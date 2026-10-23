<?php
declare(strict_types=1);

function originUuid(): string {
    $b=random_bytes(16);$b[6]=chr((ord($b[6])&15)|64);$b[8]=chr((ord($b[8])&63)|128);$h=bin2hex($b);
    return substr($h,0,8).'-'.substr($h,8,4).'-'.substr($h,12,4).'-'.substr($h,16,4).'-'.substr($h,20);
}

function canonicalOrder(string $field,string $value,bool $lock=false): ?array {
    $column=['session'=>'a.stripe_session_id','intent'=>'a.stripe_payment_intent_id','order'=>'o.order_id','subscription'=>'o.stripe_subscription_id'][$field]??null;
    if($column===null)throw new LogicException('Unknown registry key');
    $sql='SELECT o.*,i.order_item_id,i.sku AS product,i.price_id,i.unit_amount AS amount,i.currency,i.revision,a.attempt_id,a.stripe_customer_id,a.stripe_session_id,a.stripe_payment_intent_id,a.verified_at,a.refunded_amount FROM orders o JOIN order_items i ON i.order_id=o.order_id AND i.environment=o.environment AND i.position=1 AND i.revision=1 JOIN payment_attempts a ON a.order_id=o.order_id AND a.environment=o.environment WHERE o.environment=? AND '.$column.'=?';
    $row=query($sql.($lock?' FOR UPDATE':''),[conf('mode'),$value])->fetch();return $row?:null;
}

function registerOrderItem(array $order): string {
    $id=originUuid();
    query('INSERT INTO order_items(order_item_id,order_id,environment,sku,price_id,unit_amount,quantity,currency) VALUES(?,?,?,?,?,?,1,?)',[$id,$order['order_id'],$order['environment'],$order['product'],$order['price_id'],$order['amount'],$order['currency']]);
    query('INSERT INTO payment_attempts(attempt_id,order_id,environment,idempotency_key,stripe_customer_id,created_at) VALUES(?,?,?,?,?,UTC_TIMESTAMP())',[originUuid(),$order['order_id'],$order['environment'],'origin-checkout-'.$order['order_id'],$order['stripe_customer_id']]);
    return $id;
}

function synchronizeEntitlements(array $order): void {
    if(!$order['user_id'])return;
    $uid=(int)$order['user_id'];$item=$order['order_item_id'];$env=$order['environment'];
    query("UPDATE entitlements SET status='revoked',updated_at=UTC_TIMESTAMP() WHERE order_item_id=? AND environment=?",[$item,$env]);
    if($order['status']!=='paid' || !$order['verified_at'] || (int)$order['refunded_amount']>0)return;
    $end=null;
    if(in_array($order['product'],['individual','family'],true)){
        $sub=query('SELECT * FROM subscriptions WHERE order_id=? AND user_id=?',[$order['order_id'],$uid])->fetch();
        if(!$sub || $sub['plan']!==$order['product'] || !in_array($sub['status'],['active','trialing'],true) || !$sub['current_period_end'] || strtotime($sub['current_period_end'].' UTC')<=time())return;
        $end=$sub['current_period_end'];
    }
    $features=(array)(conf('product_features',[])[$order['product']]??[]);
    $features=array_values(array_intersect($features,['cloud_carnet','cloud_tree','mirror_deep']));
    $features[]='product:'.$order['product'];
    foreach($features as $f)query("INSERT INTO entitlements(user_id,order_item_id,environment,capability,status,valid_until,updated_at) VALUES(?,?,?,?,'active',?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE status='active',valid_until=VALUES(valid_until),updated_at=UTC_TIMESTAMP()",[$uid,$item,$env,$f,$end]);
}

function registryEntitlement(int $uid): array {
    $rows=query("SELECT e.capability,i.sku FROM entitlements e JOIN order_items i ON i.order_item_id=e.order_item_id AND i.environment=e.environment JOIN orders o ON o.order_id=i.order_id AND o.environment=i.environment AND o.user_id=e.user_id WHERE e.user_id=? AND e.environment=? AND e.status='active' AND (e.valid_until IS NULL OR e.valid_until>UTC_TIMESTAMP()) AND o.status='paid'",[$uid,conf('mode')])->fetchAll();
    $features=[];$products=[];
    foreach($rows as $r){if($r['capability']==='product:'.$r['sku'])$products[]=$r['sku'];elseif(in_array($r['capability'],(array)(conf('product_features',[])[$r['sku']]??[]),true))$features[]=$r['capability'];}
    $demo=conf('mode')==='test' && conf('demo_features_enabled')===true;
    if($demo)$features=array_merge($features,['cloud_carnet','cloud_tree']);
    return ['plans'=>array_values(array_intersect(array_unique($products),['individual','family'])),'products'=>array_values(array_unique($products)),
        'features'=>array_values(array_unique($features)),'mirror_paid'=>in_array('mirror',$products,true),'demo'=>$demo];
}

function bookletJobAuthorized(int $uid,string $item,string $offer): bool {
    // Réservé au futur contrat interne. Aucun endpoint ni génération ajouté.
    if(!in_array($offer,['solo','couple','famille','prestige','naissance','vocation','bundle'],true))return false;
    return (bool)query("SELECT e.entitlement_id FROM entitlements e JOIN order_items i ON i.order_item_id=e.order_item_id AND i.environment=e.environment JOIN orders o ON o.order_id=i.order_id AND o.environment=i.environment AND o.user_id=e.user_id WHERE e.user_id=? AND e.order_item_id=? AND e.environment=? AND e.capability=? AND i.sku=? AND e.status='active' AND o.status='paid' AND (e.valid_until IS NULL OR e.valid_until>UTC_TIMESTAMP())",[$uid,$item,conf('mode'),'booklet:'.$offer,$offer])->fetch();
}
