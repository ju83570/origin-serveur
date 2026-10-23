<?php
declare(strict_types=1);
require_once __DIR__.'/stripe-events.php';

function minimizeStripeEvent(array $event):array {
    global $cfg;
    if(!stripeEnvironmentMatches($event,$cfg) || !is_string($event['id']??null) || !preg_match('/^evt_[A-Za-z0-9_]{1,140}$/',$event['id'])
        || !is_string($event['type']??null) || strlen($event['type'])>100 || !is_int($event['created']??null) || !is_array($event['data']['object']??null))throw new InvalidArgumentException('Invalid Stripe envelope');
    $src=$event['data']['object'];$obj=[];
    foreach(['id','customer','subscription','payment_intent','charge','status'] as $key){
        $value=$src[$key]??null;if(is_array($value))$value=$value['id']??null;
        if(is_string($value) && strlen($value)<=150 && preg_match('/^[A-Za-z0-9_]+$/',$value))$obj[$key]=$value;
    }
    if(is_bool($src['livemode']??null))$obj['livemode']=$src['livemode'];
    foreach(['current_period_end','amount_refunded'] as $key)if(is_int($src[$key]??null))$obj[$key]=$src[$key];
    if(is_string($src['metadata']['origin_order_id']??null) && preg_match('/^[a-f0-9-]{36}$/',$src['metadata']['origin_order_id']))$obj['metadata']=['origin_order_id'=>$src['metadata']['origin_order_id']];
    if(is_string($src['parent']['subscription_details']['subscription']??null))$obj['parent']=['subscription_details'=>['subscription'=>$src['parent']['subscription_details']['subscription']]];
    if(is_array($src['items']['data']??null)){
        $obj['items']=['has_more'=>$src['items']['has_more']??true,'data'=>[]];
        foreach(array_slice($src['items']['data'],0,2) as $item)$obj['items']['data'][]=['quantity'=>$item['quantity']??null,'price'=>['id'=>$item['price']['id']??null],'current_period_end'=>$item['current_period_end']??null];
    }
    return ['id'=>$event['id'],'type'=>$event['type'],'created'=>$event['created'],'livemode'=>$event['livemode'],'data'=>['object'=>$obj]];
}

function receiveStripeEvent(array $event):array {
    $event=minimizeStripeEvent($event);$env=(string)conf('mode');
    $json=json_encode($event,JSON_THROW_ON_ERROR|JSON_UNESCAPED_SLASHES);$digest=hash('sha256',$json);
    $sealed=sealPayload($json,'stripe-inbox',$env.'|'.$event['id']);
    $insert=query('INSERT INTO stripe_inbox(environment,event_id,event_type,event_created,payload_hash,sealed_payload,next_attempt_at,received_at) VALUES(?,?,?,?,?,?,UTC_TIMESTAMP(),UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE event_id=VALUES(event_id)',[$env,$event['id'],$event['type'],$event['created'],$digest,$sealed]);
    $row=query('SELECT payload_hash,event_type,status FROM stripe_inbox WHERE environment=? AND event_id=?',[$env,$event['id']])->fetch();
    if(!hash_equals($row['payload_hash'],$digest) || $row['event_type']!==$event['type'])throw new InvalidArgumentException('Stripe event identity mismatch');
    return ['received'=>true,'queued'=>true,'duplicate'=>$insert->rowCount()!==1];
}

function claimStripeEvent(?string $eventId=null):?array {
    $token=bin2hex(random_bytes(32));$params=[$token,conf('mode')];
    $where=$eventId===null?'':' AND event_id=?';if($eventId!==null)$params[]=$eventId;
    // UPDATE conditionnel portable, sans supposer MySQL 8 / SKIP LOCKED.
    $claim=query("UPDATE stripe_inbox SET status='processing',lease_token=?,lease_until=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 300 SECOND),attempts=attempts+1 WHERE environment=? AND ((status IN ('received','retry') AND next_attempt_at<=UTC_TIMESTAMP()) OR (status='processing' AND lease_until<UTC_TIMESTAMP()))".$where.' ORDER BY received_at,event_id LIMIT 1',$params);
    if($claim->rowCount()!==1)return null;
    return query('SELECT * FROM stripe_inbox WHERE environment=? AND lease_token=?',[conf('mode'),$token])->fetch()?:null;
}

function workStripeEvent(callable $read,?string $eventId=null):array {
    $claim=claimStripeEvent($eventId);if(!$claim)return ['worked'=>false];
    $env=$claim['environment'];$id=$claim['event_id'];$token=$claim['lease_token'];
    try{
        $json=openPayload($claim['sealed_payload'],'stripe-inbox',$env.'|'.$id);
        if($json===null || !hash_equals($claim['payload_hash'],hash('sha256',$json)))throw new RuntimeException('Inbox unreadable');
        $event=json_decode($json,true,512,JSON_THROW_ON_ERROR);
        $network=function(string $route)use($read,$env,$id,$token):array {
            if(db()->inTransaction())throw new LogicException('Network inside transaction');
            $renew=query("UPDATE stripe_inbox SET lease_until=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 300 SECOND) WHERE environment=? AND event_id=? AND status='processing' AND lease_token=? AND lease_until>UTC_TIMESTAMP()",[$env,$id,$token]);
            // rowCount peut être 0 si la même seconde ne modifie pas l'échéance.
            $held=query("SELECT event_id FROM stripe_inbox WHERE environment=? AND event_id=? AND status='processing' AND lease_token=? AND lease_until>UTC_TIMESTAMP()",[$env,$id,$token])->fetch();
            if(!$held)throw new RuntimeException('Inbox lease expired');return $read($route);
        };
        $resources=fetchStripeResources($event,$network);
        db()->beginTransaction();
        $held=query("SELECT event_id FROM stripe_inbox WHERE environment=? AND event_id=? AND status='processing' AND lease_token=? AND lease_until>UTC_TIMESTAMP() FOR UPDATE",[$env,$id,$token])->fetch();
        if(!$held)throw new RuntimeException('Inbox lease expired');
        $cached=function(string $route)use($resources):array {if(!array_key_exists($route,$resources))throw new LogicException('Unprepared Stripe resource');return $resources[$route];};
        $affected=null;$status=applyStripeEvent($event,$cached,$affected);
        if($status==='processed' && $affected!==null)query('INSERT INTO outbox(environment,dedupe_key,topic,aggregate_id,payload,created_at) VALUES(?,?,?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE dedupe_key=VALUES(dedupe_key)',[$env,hash('sha256',$id.'|rights-reconciled'),'payment.reconciled',$affected,json_encode(['order_id'=>$affected,'stripe_event_id'=>$id])]);
        query('UPDATE stripe_inbox SET status=?,lease_token=NULL,lease_until=NULL,processed_at=UTC_TIMESTAMP(),last_error=NULL WHERE environment=? AND event_id=? AND lease_token=?',[$status,$env,$id,$token]);
        db()->commit();return ['worked'=>true,'status'=>$status,'event_id'=>$id];
    }catch(Throwable $e){
        rollbackOpenTransaction();$blocked=(int)$claim['attempts']>=10;
        query('UPDATE stripe_inbox SET status=?,lease_token=NULL,lease_until=NULL,next_attempt_at=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 60 SECOND),last_error=? WHERE environment=? AND event_id=? AND lease_token=?',[$blocked?'blocked':'retry',get_class($e),$env,$id,$token]);
        return ['worked'=>true,'ok'=>false,'retry'=>!$blocked,'event_id'=>$id,'error_class'=>get_class($e)];
    }
}
