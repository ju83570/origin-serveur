<?php
declare(strict_types=1);

function createCheckout(array $u,string $plan,?callable $transport=null): array {
    global $cfg;
    $transport ??= 'stripe';
    if(!paymentPolicy($cfg)['enabled'])fail('Paiements désactivés : Stripe test doit être activé explicitement.',503);
    if(!in_array($plan,['individual','family','mirror'],true))fail('Offre inconnue');
    if($plan==='family' && !conf('family_ready',false))fail('Offre Famille non lancée');
    if($plan==='mirror' && !conf('mirror_paid_ready',false))fail('Offre Miroir non lancée');
    $priceId=(string)(conf('stripe_prices',[])[$plan]??'');
    if(!preg_match('/^price_[A-Za-z0-9]+$/',$priceId) || productFromPrice($priceId,(array)conf('stripe_prices',[]))!==$plan)fail('Tarif non configuré ou ambigu',503);
    $price=$transport('GET','prices/'.rawurlencode($priceId));
    if(!stripeEnvironmentMatches($price,$cfg) || ($price['active']??false)!==true || !is_int($price['unit_amount']??null) || $price['unit_amount']<=0 || ($price['currency']??'')!=='eur'
        || ($price['type']??'')!==($plan==='mirror'?'one_time':'recurring'))throw new RuntimeException('Unapproved Stripe price');
    // Un identifiant client stable et une clé d'idempotence empêchent les
    // créations doubles même après une réponse Stripe perdue.
    $customer=$u['stripe_customer_id'];
    if(!$customer){
        $new=$transport('POST','customers',['email'=>$u['email'],'metadata'=>['origin_user_id'=>(string)$u['id']]],'origin-customer-'.conf('mode').'-'.$u['id']);
        $customer=$new['id'];
        query('UPDATE users SET stripe_customer_id=? WHERE id=? AND stripe_customer_id IS NULL',[$customer,$u['id']]);
        $customer=query('SELECT stripe_customer_id FROM users WHERE id=?',[$u['id']])->fetch()['stripe_customer_id'];
    }
    db()->beginTransaction();
    query('SELECT id FROM users WHERE id=? FOR UPDATE',[$u['id']]);
    if($plan!=='mirror' && query("SELECT id FROM subscriptions WHERE user_id=? AND status NOT IN ('canceled','incomplete_expired') LIMIT 1",[$u['id']])->fetch()){
        db()->rollBack();fail('Utilise le portail pour gérer ton abonnement existant.',409);
    }
    $order=query("SELECT * FROM orders WHERE user_id=? AND product=? AND environment=? AND status='pending' AND expires_at>UTC_TIMESTAMP() ORDER BY created_at LIMIT 1 FOR UPDATE",[$u['id'],$plan,conf('mode')])->fetch();
    if(!$order){
        $bytes=random_bytes(16);$bytes[6]=chr((ord($bytes[6])&15)|64);$bytes[8]=chr((ord($bytes[8])&63)|128);$hex=bin2hex($bytes);
        $oid=substr($hex,0,8).'-'.substr($hex,8,4).'-'.substr($hex,12,4).'-'.substr($hex,16,4).'-'.substr($hex,20);
        query('INSERT INTO orders(order_id,user_id,product,environment,price_id,amount,currency,stripe_customer_id,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?,UTC_TIMESTAMP(),DATE_ADD(UTC_TIMESTAMP(),INTERVAL 24 HOUR))',[$oid,$u['id'],$plan,conf('mode'),$priceId,$price['unit_amount'],$price['currency'],$customer]);
        $order=query('SELECT * FROM orders WHERE order_id=?',[$oid])->fetch();
    }
    db()->commit();
    if($order['stripe_session_id'])$session=$transport('GET','checkout/sessions/'.rawurlencode($order['stripe_session_id']));
    else {
        $expires=strtotime($order['expires_at'].' UTC');
        if($expires<time()+1800)fail('Un paiement précédent est encore en cours de vérification. Attends son expiration.',409,'checkout_pending');
        $meta=['origin_order_id'=>$order['order_id'],'plan'=>$plan,'origin_user_id'=>(string)$u['id']];
        $params=['mode'=>$plan==='mirror'?'payment':'subscription','customer'=>$customer,'client_reference_id'=>$order['order_id'],'expires_at'=>$expires,
            'line_items'=>[['price'=>$order['price_id'],'quantity'=>1]],'metadata'=>$meta,
            'success_url'=>rtrim((string)conf('site_url'),'/').'/?paiement=retour&session_id={CHECKOUT_SESSION_ID}',
            'cancel_url'=>rtrim((string)conf('site_url'),'/').'/?paiement=annule','locale'=>'fr'];
        if($plan!=='mirror')$params['subscription_data']=['metadata'=>$meta];
        $session=$transport('POST','checkout/sessions',$params,'origin-checkout-'.$order['order_id']);
        query('UPDATE orders SET stripe_session_id=? WHERE order_id=? AND stripe_session_id IS NULL',[$session['id'],$order['order_id']]);
    }
    if(($session['status']??'')!=='open' || !is_string($session['url']??null) || !str_starts_with($session['url'],'https://checkout.stripe.com/'))fail('Ce paiement est déjà terminé ou expiré. Actualise ton espace.',409);
    return ['ok'=>true,'order_id'=>$order['order_id'],'checkout_url'=>$session['url']];
}
