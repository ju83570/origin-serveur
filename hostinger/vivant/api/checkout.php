<?php
declare(strict_types=1);

function checkoutBusy(): never {header('Retry-After: 1');fail('Ton paiement est déjà en préparation. Réessaie dans un instant.',409,'checkout_busy');}

function ensureStripeCustomer(int $uid,callable $transport): string {
    $env=(string)conf('mode');$token=bin2hex(random_bytes(32));
    db()->beginTransaction();
    $u=query('SELECT * FROM users WHERE id=? FOR UPDATE',[$uid])->fetch();
    if(!$u){db()->rollBack();fail('Compte indisponible',401);}
    $idem='origin-customer-'.$env.'-'.$uid;
    query('INSERT INTO customer_bindings(user_id,environment,stripe_customer_id,idempotency_key) VALUES(?,?,?,?) ON DUPLICATE KEY UPDATE user_id=VALUES(user_id)',[$uid,$env,$u['stripe_customer_id'],$idem]);
    $binding=query('SELECT * FROM customer_bindings WHERE user_id=? AND environment=? FOR UPDATE',[$uid,$env])->fetch();
    if($binding['stripe_customer_id']){db()->commit();return $binding['stripe_customer_id'];}
    $claim=query('UPDATE customer_bindings SET lease_token=?,lease_until=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 90 SECOND) WHERE user_id=? AND environment=? AND (lease_until IS NULL OR lease_until<UTC_TIMESTAMP())',[$token,$uid,$env]);
    if($claim->rowCount()!==1){db()->rollBack();checkoutBusy();}
    db()->commit();
    try{
        $new=$transport('POST','customers',['email'=>$u['email'],'metadata'=>['origin_user_id'=>(string)$uid]],$binding['idempotency_key']);
        $id=(string)($new['id']??'');if(!preg_match('/^cus_[A-Za-z0-9_]+$/',$id))throw new RuntimeException('Invalid Stripe customer');
        db()->beginTransaction();query('SELECT id FROM users WHERE id=? FOR UPDATE',[$uid]);
        $updated=query('UPDATE customer_bindings SET stripe_customer_id=?,lease_token=NULL,lease_until=NULL WHERE user_id=? AND environment=? AND lease_token=? AND lease_until>UTC_TIMESTAMP()',[$id,$uid,$env,$token]);
        if($updated->rowCount()!==1)throw new RuntimeException('Customer lease expired');
        query('UPDATE users SET stripe_customer_id=? WHERE id=? AND stripe_customer_id IS NULL',[$id,$uid]);db()->commit();return $id;
    }catch(Throwable $e){rollbackOpenTransaction();query('UPDATE customer_bindings SET lease_token=NULL,lease_until=NULL WHERE user_id=? AND environment=? AND lease_token=?',[$uid,$env,$token]);throw $e;}
}

function createCheckout(array $u,string $plan,?callable $transport=null): array {
    global $cfg;$transport ??= 'stripe';
    if(!paymentPolicy($cfg)['enabled'])fail('Paiements désactivés : Stripe test doit être activé explicitement.',503);
    if(!in_array($plan,['individual','family','mirror'],true))fail('Offre inconnue');
    if($plan==='family' && !conf('family_ready',false))fail('Offre Famille non lancée');
    if($plan==='mirror' && !conf('mirror_paid_ready',false))fail('Offre Miroir non lancée');
    $priceId=(string)(conf('stripe_prices',[])[$plan]??'');
    if(!preg_match('/^price_[A-Za-z0-9]+$/',$priceId) || productFromPrice($priceId,(array)conf('stripe_prices',[]))!==$plan)fail('Tarif non configuré ou ambigu',503);
    if(db()->inTransaction())throw new LogicException('Network transaction forbidden');
    $price=$transport('GET','prices/'.rawurlencode($priceId));
    if(db()->inTransaction())throw new LogicException('Network transaction forbidden');
    if(!stripeEnvironmentMatches($price,$cfg) || ($price['active']??false)!==true || !is_int($price['unit_amount']??null) || $price['unit_amount']<=0 || ($price['currency']??'')!=='eur'
        || ($price['type']??'')!==($plan==='mirror'?'one_time':'recurring'))throw new RuntimeException('Unapproved Stripe price');
    $customer=ensureStripeCustomer((int)$u['id'],$transport);
    db()->beginTransaction();
    if(!query('SELECT id FROM users WHERE id=? FOR UPDATE',[$u['id']])->fetch())throw new RuntimeException('Account unavailable');
    if($plan!=='mirror' && query("SELECT id FROM subscriptions WHERE user_id=? AND status NOT IN ('canceled','incomplete_expired') LIMIT 1",[$u['id']])->fetch()){
        db()->rollBack();fail('Utilise le portail pour gérer ton abonnement existant.',409);
    }
    $pending=query("SELECT o.order_id FROM orders o JOIN order_items i ON i.order_id=o.order_id AND i.environment=o.environment WHERE o.user_id=? AND i.sku=? AND o.environment=? AND o.status='pending' AND o.expires_at>UTC_TIMESTAMP() ORDER BY o.created_at LIMIT 1 FOR UPDATE",[$u['id'],$plan,conf('mode')])->fetch();
    if(!$pending){
        $oid=originUuid();
        query('INSERT INTO orders(order_id,user_id,product,environment,price_id,amount,currency,stripe_customer_id,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(),INTERVAL 24 HOUR))',[$oid,$u['id'],$plan,conf('mode'),$priceId,$price['unit_amount'],$price['currency'],$customer]);
        registerOrderItem(query('SELECT * FROM orders WHERE order_id=?',[$oid])->fetch());
    }else $oid=$pending['order_id'];
    $order=canonicalOrder('order',$oid,true);
    if(!$order || $order['price_id']!==$priceId)throw new RuntimeException('Pending catalogue mismatch');
    $token=bin2hex(random_bytes(32));
    $claim=query('UPDATE payment_attempts SET lease_token=?,lease_until=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 90 SECOND) WHERE attempt_id=? AND (lease_until IS NULL OR lease_until<UTC_TIMESTAMP())',[$token,$order['attempt_id']]);
    if($claim->rowCount()!==1){db()->rollBack();checkoutBusy();}
    $attempt=query('SELECT * FROM payment_attempts WHERE attempt_id=?',[$order['attempt_id']])->fetch();db()->commit();
    try{
        if($order['stripe_session_id'])$session=$transport('GET','checkout/sessions/'.rawurlencode($order['stripe_session_id']));
        else{
            $expires=strtotime($order['expires_at'].' UTC');
            if($expires<time()+1800)throw new RuntimeException('Checkout pending expiry');
            $meta=['origin_order_id'=>$oid,'plan'=>$plan,'origin_user_id'=>(string)$u['id']];
            $params=['mode'=>$plan==='mirror'?'payment':'subscription','customer'=>$customer,'client_reference_id'=>$oid,'expires_at'=>$expires,
                'line_items'=>[['price'=>$order['price_id'],'quantity'=>1]],'metadata'=>$meta,
                'success_url'=>rtrim((string)conf('site_url'),'/').'/?paiement=retour&session_id={CHECKOUT_SESSION_ID}',
                'cancel_url'=>rtrim((string)conf('site_url'),'/').'/?paiement=annule','locale'=>'fr'];
            if($plan!=='mirror')$params['subscription_data']=['metadata'=>$meta];
            $session=$transport('POST','checkout/sessions',$params,$attempt['idempotency_key']);
        }
        if(!stripeEnvironmentMatches($session,$cfg) || ($session['customer']??null)!==$customer || ($session['client_reference_id']??null)!==$oid || !preg_match('/^cs_[A-Za-z0-9_]+$/',(string)($session['id']??'')))throw new RuntimeException('Checkout binding mismatch');
        db()->beginTransaction();
        $saved=query('UPDATE payment_attempts SET stripe_session_id=?,lease_token=NULL,lease_until=NULL WHERE attempt_id=? AND lease_token=? AND lease_until>UTC_TIMESTAMP() AND (stripe_session_id IS NULL OR stripe_session_id=?)',[$session['id'],$order['attempt_id'],$token,$session['id']]);
        if($saved->rowCount()!==1)throw new RuntimeException('Checkout lease expired');
        // Colonnes historiques de compatibilité ; aucun droit ne les lit.
        query('UPDATE orders SET stripe_session_id=? WHERE order_id=? AND stripe_session_id IS NULL',[$session['id'],$oid]);db()->commit();
    }catch(Throwable $e){rollbackOpenTransaction();query('UPDATE payment_attempts SET lease_token=NULL,lease_until=NULL WHERE attempt_id=? AND lease_token=?',[$order['attempt_id'],$token]);throw $e;}
    if(($session['status']??'')!=='open' || !is_string($session['url']??null) || !str_starts_with($session['url'],'https://checkout.stripe.com/'))fail('Ce paiement est déjà terminé ou expiré. Actualise ton espace.',409);
    return ['ok'=>true,'order_id'=>$oid,'checkout_url'=>$session['url']];
}
