<?php
declare(strict_types=1);

// Le lecteur Stripe est une dépendance explicite pour les tests. L'API HTTP
// de production utilise TOUJOURS stripe(), sans commutateur de simulation.
function synchronizeSubscription(array $sub, array $order, bool $deleted=false): void {
    global $cfg;
    if(!stripeEnvironmentMatches($sub,$cfg) || ($sub['customer']??null)!==$order['stripe_customer_id'])throw new RuntimeException('Subscription binding mismatch');
    $sid=(string)($sub['id']??'');if(!preg_match('/^sub_[a-zA-Z0-9_]+$/',$sid))throw new RuntimeException('Invalid subscription id');
    if($order['stripe_subscription_id']!==null && $order['stripe_subscription_id']!==$sid)throw new RuntimeException('Subscription order mismatch');
    $previous=query('SELECT * FROM subscriptions WHERE stripe_subscription_id=? FOR UPDATE',[$sid])->fetch();
    if($previous && ((int)$previous['user_id']!==(int)$order['user_id'] || $previous['order_id']!==$order['order_id']))throw new RuntimeException('Subscription owner mismatch');
    $items=$sub['items']['data']??[];
    $plan=count($items)===1 && ($sub['items']['has_more']??true)===false && ($items[0]['quantity']??null)===1
        ?productFromPrice((string)($items[0]['price']['id']??''),(array)conf('stripe_prices',[])):null;
    $status=(string)($sub['status']??'');
    if(!in_array($status,['active','trialing','past_due','unpaid','incomplete','incomplete_expired','paused','canceled'],true))$status='unverified';
    if($plan===null || $plan==='mirror'){$plan=$previous['plan']??$order['product'];$status='unverified';}
    if($order['status']!=='paid' && in_array($status,['active','trialing'],true))$status='pending_checkout';
    if($deleted || ($previous['status']??'')==='canceled')$status='canceled';
    $period=$items[0]['current_period_end']??$sub['current_period_end']??null;
    $end=is_int($period) && $period>0?gmdate('Y-m-d H:i:s',$period):null;
    query('INSERT INTO subscriptions(user_id,order_id,stripe_subscription_id,plan,status,current_period_end,updated_at) VALUES(?,?,?,?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE plan=VALUES(plan),status=VALUES(status),current_period_end=VALUES(current_period_end),updated_at=UTC_TIMESTAMP()',[(int)$order['user_id'],$order['order_id'],$sid,$plan,$status,$end]);
    query('UPDATE orders SET stripe_subscription_id=? WHERE order_id=?',[$sid,$order['order_id']]);
}

function applyStripeEvent(array $event, callable $read): string {
    global $cfg;
    $type=$event['type'];$obj=$event['data']['object']??null;
    if(!is_array($obj))throw new RuntimeException('Invalid event object');
    if(in_array($type,['checkout.session.completed','checkout.session.async_payment_succeeded','checkout.session.async_payment_failed','checkout.session.expired'],true)){
        $order=query('SELECT * FROM orders WHERE stripe_session_id=? FOR UPDATE',[(string)($obj['id']??'')])->fetch();
        if(!$order){
            // Un webhook peut devancer la réponse à la création du Checkout.
            // Le UUID serveur permet le rattachement ; toutes les identités et
            // le montant seront encore vérifiés sur la ressource Stripe relue.
            $oid=(string)($obj['metadata']['origin_order_id']??'');
            $order=query('SELECT * FROM orders WHERE order_id=? FOR UPDATE',[$oid])->fetch();
            if($order && $order['stripe_session_id']===null)$order['stripe_session_id']=(string)($obj['id']??'');
            elseif($order && $order['stripe_session_id']!==($obj['id']??null))throw new RuntimeException('Session order mismatch');
        }
        if(!$order || !$order['user_id'])return 'ignored'; // aucune commande présumée à partir du seul utilisateur
        if($order['environment']!==conf('mode'))throw new RuntimeException('Order environment mismatch');
        if(in_array($order['status'],['refunded','disputed','revoked'],true))return 'processed';
        $customer=query('SELECT stripe_customer_id FROM users WHERE id=?',[$order['user_id']])->fetch();
        if(!$customer || $customer['stripe_customer_id']!==$order['stripe_customer_id'])throw new RuntimeException('Customer binding mismatch');
        $session=$read('checkout/sessions/'.rawurlencode($order['stripe_session_id']));
        if(!stripeEnvironmentMatches($session,$cfg) || ($session['id']??null)!==$order['stripe_session_id']
            || ($session['customer']??null)!==$order['stripe_customer_id']
            || ($session['client_reference_id']??null)!==$order['order_id']
            || ($session['metadata']['origin_order_id']??null)!==$order['order_id'])throw new RuntimeException('Session identity mismatch');
        query('UPDATE orders SET stripe_session_id=? WHERE order_id=? AND stripe_session_id IS NULL',[$order['stripe_session_id'],$order['order_id']]);
        if(($session['payment_status']??'')!=='paid'){
            if($order['status']!=='paid' && ($session['status']??'')==='expired')query("UPDATE orders SET status='expired' WHERE order_id=?",[$order['order_id']]);
            return 'processed'; // paiement différé : attendre l'événement de succès
        }
        $items=$read('checkout/sessions/'.rawurlencode($order['stripe_session_id']).'/line_items');
        if(!checkoutMatchesOrder($session,$items,$order,$cfg))throw new RuntimeException('Checkout offer or amount mismatch');
        $pi=$session['payment_intent']??null;
        if($pi!==null && (!is_string($pi) || !preg_match('/^pi_[A-Za-z0-9_]+$/',$pi)))throw new RuntimeException('Invalid payment intent');
        query("UPDATE orders SET status='paid',stripe_payment_intent_id=? WHERE order_id=?",[$pi,$order['order_id']]);$order['status']='paid';
        if($order['product']==='mirror')
            query("INSERT INTO purchases(user_id,order_id,product,stripe_session_id,status,created_at) VALUES(?,?,?,?,'paid',UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE status='paid'",[$order['user_id'],$order['order_id'],'mirror',$order['stripe_session_id']]);
        else {
            $sid=$session['subscription']??null;if(!is_string($sid))throw new RuntimeException('Missing subscription');
            synchronizeSubscription($read('subscriptions/'.rawurlencode($sid)),$order);
        }
        return 'processed';
    }
    if(in_array($type,['customer.subscription.created','customer.subscription.updated','customer.subscription.deleted','invoice.paid','invoice.payment_failed'],true)){
        $invoice=str_starts_with($type,'invoice.');
        $sid=$invoice?($obj['subscription']??$obj['parent']['subscription_details']['subscription']??null):($obj['id']??null);
        if(!is_string($sid))return 'ignored';
        $sub=(!$invoice && $type==='customer.subscription.deleted')?$obj:$read('subscriptions/'.rawurlencode($sid));
        $oid=(string)($sub['metadata']['origin_order_id']??'');
        $order=query('SELECT * FROM orders WHERE stripe_subscription_id=? OR order_id=? FOR UPDATE',[$sid,$oid])->fetch();
        if(!$order || !$order['user_id'])return 'ignored';
        if($order['environment']!==conf('mode'))throw new RuntimeException('Subscription environment mismatch');
        synchronizeSubscription($sub,$order,$type==='customer.subscription.deleted');return 'processed';
    }
    if(in_array($type,['charge.refunded','charge.dispute.created'],true)){
        $pi=$obj['payment_intent']??null;
        if(!is_string($pi) && is_string($obj['charge']??null))$pi=$read('charges/'.rawurlencode($obj['charge']))['payment_intent']??null;
        if(!is_string($pi))return 'ignored';
        if($type==='charge.refunded' && (int)($obj['amount_refunded']??0)<=0)return 'ignored';
        $order=query('SELECT * FROM orders WHERE stripe_payment_intent_id=? FOR UPDATE',[$pi])->fetch();
        if(!$order)return 'ignored';
        if($order['environment']!==conf('mode'))throw new RuntimeException('Refund environment mismatch');
        $status=$type==='charge.refunded'?'refunded':'disputed';
        query('UPDATE orders SET status=? WHERE order_id=?',[$status,$order['order_id']]);
        query('UPDATE purchases SET status=? WHERE order_id=?',[$status,$order['order_id']]);
        query("UPDATE subscriptions SET status='unpaid' WHERE order_id=? AND status<>'canceled'",[$order['order_id']]);
        return 'processed';
    }
    return 'ignored';
}

function processStripeEvent(array $event, callable $read): array {
    global $cfg;
    if(!stripeEnvironmentMatches($event,$cfg) || !is_string($event['id']??null) || !preg_match('/^evt_[A-Za-z0-9_]{1,140}$/',$event['id']) || !is_string($event['type']??null) || strlen($event['type'])>100)throw new RuntimeException('Invalid event envelope');
    // Inbox durable, sans données familiales ni payload client. Une erreur
    // laisse received : Stripe peut rejouer, elle n'est jamais un faux succès.
    query("INSERT INTO stripe_events(event_id,event_type,status,processed_at) VALUES(?,?,'received',UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE event_id=VALUES(event_id)",[$event['id'],$event['type']]);
    db()->beginTransaction();
    try{
        $saved=query('SELECT * FROM stripe_events WHERE event_id=? FOR UPDATE',[$event['id']])->fetch();
        if($saved['event_type']!==$event['type'])throw new RuntimeException('Event identity mismatch');
        if($saved['status']!=='received'){db()->commit();return ['received'=>true,'duplicate'=>true];}
        $status=applyStripeEvent($event,$read);
        query('UPDATE stripe_events SET status=?,processed_at=UTC_TIMESTAMP() WHERE event_id=?',[$status,$event['id']]);
        db()->commit();return ['received'=>true,'status'=>$status];
    }catch(Throwable $e){rollbackOpenTransaction();throw $e;}
}
