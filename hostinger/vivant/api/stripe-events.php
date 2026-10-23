<?php
declare(strict_types=1);

function synchronizeSubscription(array $sub,array $order,bool $deleted=false):void {
    global $cfg;
    if(!stripeEnvironmentMatches($sub,$cfg) || ($sub['customer']??null)!==$order['stripe_customer_id'])throw new RuntimeException('Subscription binding mismatch');
    $sid=(string)($sub['id']??'');if(!preg_match('/^sub_[A-Za-z0-9_]+$/',$sid))throw new RuntimeException('Invalid subscription');
    if($order['stripe_subscription_id']!==null && $order['stripe_subscription_id']!==$sid)throw new RuntimeException('Subscription order mismatch');
    $previous=query('SELECT * FROM subscriptions WHERE stripe_subscription_id=? FOR UPDATE',[$sid])->fetch();
    if($previous && ((int)$previous['user_id']!==(int)$order['user_id'] || $previous['order_id']!==$order['order_id']))throw new RuntimeException('Subscription owner mismatch');
    $items=$sub['items']['data']??[];$line=count($items)===1?$items[0]:[];
    $valid=($sub['items']['has_more']??true)===false && ($line['quantity']??null)===1
        && ($line['price']['id']??null)===$order['price_id'];
    $status=(string)($sub['status']??'');
    if(!$valid || !in_array($status,['active','trialing','past_due','unpaid','incomplete','incomplete_expired','paused','canceled'],true))$status='unverified';
    if(!$order['verified_at'] && in_array($status,['active','trialing'],true))$status='pending_checkout';
    if($deleted || ($previous['status']??'')==='canceled')$status='canceled';
    $period=$line['current_period_end']??$sub['current_period_end']??null;
    $end=is_int($period) && $period>0?gmdate('Y-m-d H:i:s',$period):null;
    query('INSERT INTO subscriptions(user_id,order_id,stripe_subscription_id,plan,status,current_period_end,updated_at) VALUES(?,?,?,?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE status=VALUES(status),current_period_end=VALUES(current_period_end),updated_at=UTC_TIMESTAMP()',[$order['user_id'],$order['order_id'],$sid,$order['product'],$status,$end]);
    query('UPDATE orders SET stripe_subscription_id=? WHERE order_id=?',[$sid,$order['order_id']]);
}

function validateCharge(array $charge,array $order,bool $recurring=false):void {
    global $cfg;
    if(!stripeEnvironmentMatches($charge,$cfg) || ($charge['customer']??null)!==$order['stripe_customer_id']
        || (!$recurring && ($charge['payment_intent']??null)!==$order['stripe_payment_intent_id'])
        || ($charge['currency']??null)!==$order['currency'] || !is_int($charge['amount']??null) || $charge['amount']<=0 || (!$recurring && $charge['amount']!==(int)$order['amount'])
        || !is_int($charge['amount_refunded']??null) || $charge['amount_refunded']<0 || $charge['amount_refunded']>$charge['amount'])throw new RuntimeException('Charge binding mismatch');
}
function recordDispute(array $dispute,array $order,string $chargeId):void {
    global $cfg;$did=(string)($dispute['id']??'');$status=(string)($dispute['status']??'');
    if(!stripeEnvironmentMatches($dispute,$cfg) || !preg_match('/^dp_[A-Za-z0-9_]+$/',$did) || ($dispute['charge']??null)!==$chargeId
        || !in_array($status,['needs_response','under_review','won','lost','warning_needs_response','warning_under_review','warning_closed'],true))throw new RuntimeException('Invalid dispute');
    $old=query('SELECT * FROM payment_disputes WHERE environment=? AND dispute_id=? FOR UPDATE',[conf('mode'),$did])->fetch();
    if($old && $old['attempt_id']!==$order['attempt_id'])throw new RuntimeException('Dispute owner mismatch');
    if($old && in_array($old['status'],['won','lost','warning_closed'],true))$status=$old['status'];
    query('INSERT INTO payment_disputes(environment,dispute_id,attempt_id,status,updated_at) VALUES(?,?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE status=VALUES(status),updated_at=UTC_TIMESTAMP()',[conf('mode'),$did,$order['attempt_id'],$status]);
}
function financialStatus(array $order,bool $paid):string {
    $attempt=query('SELECT refunded_amount FROM payment_attempts WHERE attempt_id=?',[$order['attempt_id']])->fetch();
    $blocked=query("SELECT dispute_id FROM payment_disputes WHERE attempt_id=? AND status NOT IN ('won','warning_closed') LIMIT 1",[$order['attempt_id']])->fetch();
    return (int)$attempt['refunded_amount']>0?'refunded':($blocked?'disputed':($paid?'paid':($order['verified_at']?'revoked':'pending')));
}

function checkoutOrder(array $obj,bool $lock=false):?array {
    $order=canonicalOrder('session',(string)($obj['id']??''),$lock);
    if(!$order){
        $order=canonicalOrder('order',(string)($obj['metadata']['origin_order_id']??''),$lock);
        if($order && $order['stripe_session_id']!==null && $order['stripe_session_id']!==($obj['id']??null))throw new RuntimeException('Session order mismatch');
    }
    return $order;
}

function chargeOrder(array $charge,callable $read,bool $lock=false):?array {
    $order=canonicalOrder('intent',(string)($charge['payment_intent']??''),$lock);
    if($order)return $order;
    $invoiceId=$charge['invoice']??null;if(!is_string($invoiceId))return null;
    $invoice=$read('invoices/'.rawurlencode($invoiceId));
    $sid=$invoice['subscription']??$invoice['parent']['subscription_details']['subscription']??null;
    if(!is_string($sid))return null;
    $order=canonicalOrder('subscription',$sid,$lock);
    if(!$order){
        $sub=$read('subscriptions/'.rawurlencode($sid));
        $order=canonicalOrder('order',(string)($sub['metadata']['origin_order_id']??''),$lock);
    }
    return $order;
}

// Toutes les lectures fournisseur s'effectuent AVANT la transaction des effets.
function fetchStripeResources(array $event,callable $read):array {
    if(db()->inTransaction())throw new LogicException('Network inside transaction');
    $cache=[];$get=function(string $route)use(&$cache,$read):array{
        if(db()->inTransaction())throw new LogicException('Network inside transaction');
        if(!array_key_exists($route,$cache))$cache[$route]=$read($route);return $cache[$route];
    };
    $type=$event['type'];$obj=$event['data']['object'];
    if(str_starts_with($type,'checkout.session.')){
        $order=checkoutOrder($obj);if(!$order || !$order['user_id'] || in_array($order['status'],['refunded','disputed','revoked'],true))return $cache;
        $sid=$order['stripe_session_id']??(string)($obj['id']??'');
        $session=$get('checkout/sessions/'.rawurlencode($sid));
        if(($session['payment_status']??'')==='paid'){
            $get('checkout/sessions/'.rawurlencode($sid).'/line_items');
            if(is_string($session['subscription']??null))$get('subscriptions/'.rawurlencode($session['subscription']));
            if(is_string($session['payment_intent']??null)){
                $intent=$get('payment_intents/'.rawurlencode($session['payment_intent']));
                $chargeId=$intent['latest_charge']??null;
                if(is_string($chargeId)){
                    $charge=$get('charges/'.rawurlencode($chargeId));
                    if(($charge['disputed']??false)===true)$get('disputes?charge='.rawurlencode($chargeId).'&limit=100');
                }
            }
        }
    }elseif(str_starts_with($type,'customer.subscription.') || in_array($type,['invoice.paid','invoice.payment_failed'],true)){
        $sid=str_starts_with($type,'invoice.')?($obj['subscription']??$obj['parent']['subscription_details']['subscription']??null):($obj['id']??null);
        if(is_string($sid) && $type!=='customer.subscription.deleted')$get('subscriptions/'.rawurlencode($sid));
    }elseif($type==='charge.refunded' || str_starts_with($type,'charge.dispute.')){
        if(str_starts_with($type,'charge.dispute.')){
            $dispute=$get('disputes/'.rawurlencode((string)($obj['id']??'')));
            if(is_string($dispute['charge']??null))$charge=$get('charges/'.rawurlencode($dispute['charge']));
        }elseif(is_string($obj['id']??null))$charge=$get('charges/'.rawurlencode($obj['id']));
        if(isset($charge)){
            $order=chargeOrder($charge,$get);
            if($order && $order['stripe_subscription_id'])$get('subscriptions/'.rawurlencode($order['stripe_subscription_id']));
        }
    }
    return $cache;
}

function applyStripeEvent(array $event,callable $read,?string &$affected=null):string {
    global $cfg;$type=$event['type'];$obj=$event['data']['object'];
    if(in_array($type,['checkout.session.completed','checkout.session.async_payment_succeeded','checkout.session.async_payment_failed','checkout.session.expired'],true)){
        $order=checkoutOrder($obj,true);if(!$order || !$order['user_id'])return 'ignored';$affected=$order['order_id'];
        if(in_array($order['status'],['refunded','disputed','revoked'],true))return 'processed';
        $sid=$order['stripe_session_id']??(string)$obj['id'];
        $session=$read('checkout/sessions/'.rawurlencode($sid));
        $owner=query('SELECT stripe_customer_id FROM users WHERE id=?',[$order['user_id']])->fetch();
        if(!$owner || $owner['stripe_customer_id']!==$order['stripe_customer_id'] || !stripeEnvironmentMatches($session,$cfg)
            || ($session['id']??null)!==$sid || ($session['customer']??null)!==$order['stripe_customer_id']
            || ($session['client_reference_id']??null)!==$order['order_id'] || ($session['metadata']['origin_order_id']??null)!==$order['order_id'])throw new RuntimeException('Checkout identity mismatch');
        $order['stripe_session_id']=$sid;
        query('UPDATE payment_attempts SET stripe_session_id=? WHERE attempt_id=? AND (stripe_session_id IS NULL OR stripe_session_id=?)',[$sid,$order['attempt_id'],$sid]);
        query('UPDATE orders SET stripe_session_id=? WHERE order_id=? AND stripe_session_id IS NULL',[$sid,$order['order_id']]);
        if(($session['payment_status']??'')!=='paid'){
            if(!$order['verified_at']){
                $status=($session['status']??'')==='expired'?'expired':($type==='checkout.session.async_payment_failed'?'failed':'pending');
                query('UPDATE payment_attempts SET status=? WHERE attempt_id=?',[$status,$order['attempt_id']]);
                query('UPDATE orders SET status=? WHERE order_id=?',[$status,$order['order_id']]);
            }
            return 'processed';
        }
        $items=$read('checkout/sessions/'.rawurlencode($sid).'/line_items');
        if(!checkoutMatchesOrder($session,$items,$order,$cfg))throw new RuntimeException('Checkout offer or amount mismatch');
        $pi=$session['payment_intent']??null;
        if($pi!==null && (!is_string($pi) || !preg_match('/^pi_[A-Za-z0-9_]+$/',$pi)))throw new RuntimeException('Invalid intent');
        if($order['product']==='mirror' && !is_string($pi))throw new RuntimeException('Missing payment proof');
        if(is_string($pi)){
            $intent=$read('payment_intents/'.rawurlencode($pi));
            if(!stripeEnvironmentMatches($intent,$cfg) || ($intent['id']??null)!==$pi || ($intent['status']??null)!=='succeeded' || ($intent['customer']??null)!==$order['stripe_customer_id'] || ($intent['currency']??null)!==$order['currency'] || ($intent['amount']??null)!==(int)$order['amount'])throw new RuntimeException('Payment intent mismatch');
            $chargeId=$intent['latest_charge']??null;if(!is_string($chargeId))throw new RuntimeException('Missing charge');
            $charge=$read('charges/'.rawurlencode($chargeId));$order['stripe_payment_intent_id']=$pi;validateCharge($charge,$order);
            if(($charge['paid']??false)!==true)throw new RuntimeException('Charge not paid');
            query('UPDATE payment_attempts SET refunded_amount=GREATEST(refunded_amount,?) WHERE attempt_id=?',[$charge['amount_refunded'],$order['attempt_id']]);
            if(($charge['disputed']??false)===true){
                $list=$read('disputes?charge='.rawurlencode($chargeId).'&limit=100');
                if(($list['has_more']??true)!==false || empty($list['data']))throw new RuntimeException('Incomplete dispute state');
                foreach($list['data'] as $d)recordDispute($d,$order,$chargeId);
            }
        }
        query("UPDATE payment_attempts SET status='verified',verified_at=COALESCE(verified_at,UTC_TIMESTAMP()),stripe_payment_intent_id=? WHERE attempt_id=?",[$pi,$order['attempt_id']]);
        query("UPDATE orders SET status='paid',stripe_payment_intent_id=? WHERE order_id=?",[$pi,$order['order_id']]);
        $order=canonicalOrder('order',$order['order_id'],true);
        if($order['product']!=='mirror'){
            $sub=$session['subscription']??null;if(!is_string($sub))throw new RuntimeException('Missing subscription');
            synchronizeSubscription($read('subscriptions/'.rawurlencode($sub)),$order);
        }
        $state=financialStatus($order,true);
        query('UPDATE orders SET status=? WHERE order_id=?',[$state,$order['order_id']]);
        query('UPDATE payment_attempts SET status=? WHERE attempt_id=?',[$state==='paid'?'verified':$state,$order['attempt_id']]);
        synchronizeEntitlements(canonicalOrder('order',$order['order_id'],true));return 'processed';
    }
    if(in_array($type,['customer.subscription.created','customer.subscription.updated','customer.subscription.deleted','invoice.paid','invoice.payment_failed'],true)){
        $sid=str_starts_with($type,'invoice.')?($obj['subscription']??$obj['parent']['subscription_details']['subscription']??null):($obj['id']??null);
        if(!is_string($sid))return 'ignored';
        $sub=$type==='customer.subscription.deleted'?$obj:$read('subscriptions/'.rawurlencode($sid));
        $order=canonicalOrder('subscription',$sid,true)??canonicalOrder('order',(string)($sub['metadata']['origin_order_id']??''),true);
        if(!$order || !$order['user_id'])return 'ignored';$affected=$order['order_id'];
        synchronizeSubscription($sub,$order,$type==='customer.subscription.deleted');synchronizeEntitlements($order);return 'processed';
    }
    if($type==='charge.refunded' || in_array($type,['charge.dispute.created','charge.dispute.updated','charge.dispute.closed','charge.dispute.funds_withdrawn','charge.dispute.funds_reinstated'],true)){
        $dispute=null;
        if($type==='charge.refunded')$charge=$read('charges/'.rawurlencode((string)($obj['id']??'')));
        else{$dispute=$read('disputes/'.rawurlencode((string)($obj['id']??'')));$charge=$read('charges/'.rawurlencode((string)($dispute['charge']??'')));}
        $pi=$charge['payment_intent']??null;if(!is_string($pi))return 'ignored';
        $order=chargeOrder($charge,$read,true);if(!$order)return 'ignored';$affected=$order['order_id'];
        validateCharge($charge,$order,in_array($order['product'],['individual','family'],true));
        if($order['user_id'] && $order['stripe_subscription_id'])synchronizeSubscription($read('subscriptions/'.rawurlencode($order['stripe_subscription_id'])),$order);
        query('UPDATE payment_attempts SET refunded_amount=GREATEST(refunded_amount,?) WHERE attempt_id=?',[$charge['amount_refunded'],$order['attempt_id']]);
        if($dispute!==null){
            if(($dispute['id']??null)!==($obj['id']??null))throw new RuntimeException('Dispute identity mismatch');
            recordDispute($dispute,$order,(string)$charge['id']);
        }
        $source=$dispute['id']??$charge['id'];$adjustmentStatus=$dispute['status']??'refunded';
        query("INSERT INTO payment_adjustments(environment,source_id,order_id,attempt_id,payment_intent_id,invoice_id,amount,refunded_amount,currency,status,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE refunded_amount=GREATEST(refunded_amount,VALUES(refunded_amount)),status=CASE WHEN status IN ('won','lost','warning_closed') THEN status ELSE VALUES(status) END,updated_at=UTC_TIMESTAMP()",[conf('mode'),$source,$order['order_id'],$order['attempt_id'],$pi,$charge['invoice']??null,$charge['amount'],$charge['amount_refunded'],$charge['currency'],$adjustmentStatus]);
        $state=financialStatus($order,($charge['paid']??false)===true && (bool)$order['verified_at']);
        query('UPDATE orders SET status=? WHERE order_id=?',[$state,$order['order_id']]);
        query('UPDATE payment_attempts SET status=? WHERE attempt_id=?',[$state==='paid'?'verified':$state,$order['attempt_id']]);
        synchronizeEntitlements(canonicalOrder('order',$order['order_id'],true));return 'processed';
    }
    return 'ignored';
}
