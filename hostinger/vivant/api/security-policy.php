<?php
declare(strict_types=1);

// Fonctions sans I/O : politique vérifiée indépendamment des fournisseurs.
function proxyClientIp(array $server, array $trusted): string {
    $peer=(string)($server['REMOTE_ADDR']??'');
    if(!filter_var($peer,FILTER_VALIDATE_IP))return 'unknown';
    $header=(string)($server['HTTP_X_FORWARDED_FOR']??'');
    if(in_array($peer,$trusted,true) && $header!=='' && strlen($header)<=1024){
        $chain=array_map('trim',explode(',',$header));$valid=count($chain)<=20;
        foreach($chain as $ip)if(!filter_var($ip,FILTER_VALIDATE_IP))$valid=false;
        if($valid){$chain[]=$peer;while(count($chain)>1 && in_array(end($chain),$trusted,true))array_pop($chain);$peer=(string)end($chain);}
    }
    return inet_ntop(inet_pton($peer));
}

function productFromPrice(string $price, array $prices): ?string {
    $found=[];
    foreach(['individual','family','mirror'] as $product)
        if($price!=='' && ($prices[$product]??null)===$price)$found[]=$product;
    return count($found)===1?$found[0]:null;
}

function accessPolicy(array $subscriptions, array $purchases, array $config, int $now): array {
    $plans=[];$products=[];
    foreach($subscriptions as $s){
        $end=isset($s['current_period_end'])?strtotime($s['current_period_end'].' UTC'):false;
        if(in_array($s['plan']??'', ['individual','family'],true)
            && in_array($s['status']??'', ['active','trialing'],true) && $end!==false && $end>$now){
            $plans[]=$s['plan'];$products[]=$s['plan'];
        }
    }
    foreach($purchases as $p)if(($p['status']??'')==='paid' && ($p['product']??'')==='mirror')$products[]='mirror';
    // Les droits commerciaux doivent être renseignés APRÈS validation. Aucun
    // droit générique « abonné » ne débloque un produit différent.
    $features=[];$allowed=['cloud_carnet','cloud_tree','mirror_deep'];
    foreach(array_unique($products) as $p)
        foreach((array)($config['product_features'][$p]??[]) as $f)if(in_array($f,$allowed,true))$features[]=$f;
    $demo=($config['mode']??'')==='test' && ($config['demo_features_enabled']??false)===true;
    if($demo)$features=array_merge($features,['cloud_carnet','cloud_tree']);
    return ['plans'=>array_values(array_unique($plans)), 'products'=>array_values(array_unique($products)),
        'features'=>array_values(array_unique($features)), 'mirror_paid'=>in_array('mirror',$products,true), 'demo'=>$demo];
}

function validBackup(mixed $state): bool {
    if(!is_object($state) || ($state->format??null)!=='origin-vivant-cloud-2' || !property_exists($state,'tree'))return false;
    $c=$state->carnet??null;
    if(!is_object($c) || !is_object($c->draft??null))return false;
    foreach(['mirrors','memories','checkins'] as $name)
        if(!is_array($c->$name??null) || count($c->$name)>300)return false;
    $t=$state->tree;
    return $t===null || (is_object($t) && ($t->demo??null)===false && is_array($t->people??null) && count($t->people)<=70);
}

function stripeEnvironmentMatches(array $object, array $config): bool {
    return isset($object['livemode']) && is_bool($object['livemode'])
        && $object['livemode']===(($config['mode']??'staging')==='production');
}

function checkoutMatchesOrder(array $session, array $items, array $order, array $config): bool {
    $lines=$items['data']??[];$line=count($lines)===1?$lines[0]:[];$price=$line['price']??[];
    return stripeEnvironmentMatches($session,$config) && ($session['id']??'')===$order['stripe_session_id']
        && ($session['client_reference_id']??'')===$order['order_id']
        && ($session['metadata']['origin_order_id']??'')===$order['order_id']
        && ($session['customer']??'')===$order['stripe_customer_id']
        && ($session['mode']??'')===($order['product']==='mirror'?'payment':'subscription')
        && ($session['status']??'')==='complete' && ($session['payment_status']??'')==='paid'
        && ($session['currency']??'')===$order['currency']
        && is_int($session['amount_total']??null) && $session['amount_total']===(int)$order['amount']
        && ($items['has_more']??true)===false && ($line['quantity']??null)===1
        && ($price['id']??'')===$order['price_id'] && ($price['currency']??'')===$order['currency']
        && ($price['unit_amount']??null)===(int)$order['amount']
        && ($line['amount_total']??null)===(int)$order['amount'];
}
