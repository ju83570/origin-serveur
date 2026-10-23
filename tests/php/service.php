<?php
declare(strict_types=1);
// Lanceur CLI strictement dans le conteneur de test. Jamais monté sous /app.
require '/app/vivant/api/bootstrap.php';
require '/app/vivant/api/backups.php';
require '/app/vivant/api/stripe-inbox.php';
require '/app/vivant/api/accounts.php';
require '/app/vivant/api/checkout.php';
if(PHP_SAPI!=='cli' || conf('mode')!=='test' || !str_starts_with((string)conf('site_url'),'http://127.0.0.1:'))exit(2);
$raw=stream_get_contents(STDIN);
$fixture=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
$fixtureObject=json_decode($raw,false,512,JSON_THROW_ON_ERROR);
$cfg['demo_features_enabled']=false;
$cfg['product_features']=['individual'=>['cloud_carnet'],'family'=>['cloud_carnet','cloud_tree'],'mirror'=>['mirror_deep']];
if(isset($fixture['environment'])){if(!in_array($fixture['environment'],['test','production'],true))exit(5);$cfg['mode']=$fixture['environment'];}
$uid=(int)($fixture['uid']??0);
if($uid){$u=query('SELECT email FROM users WHERE id=?',[$uid])->fetch();if(!$u || !str_ends_with($u['email'],'@example.invalid'))exit(3);}
try{
    if($fixture['kind']==='checkout'){
        $cfg['stripe_secret']='sk_test_unit_fixture';$cfg['test_payments_enabled']=true;$cfg['mirror_paid_ready']=true;
        $calls=[];
        $transport=function(string $method,string $route,array $params=[],?string $key=null)use($fixture,&$calls):array{
            if(db()->inTransaction())throw new LogicException('Network inside transaction');
            $calls[]=['method'=>$method,'route'=>$route,'params'=>$params,'idempotency'=>$key];
            if(isset($fixture['scope']))query('INSERT INTO test_provider_calls(scope,method,route,idempotency_key) VALUES(?,?,?,?)',[$fixture['scope'],$method,$route,$key]);
            if($method==='POST' && !empty($fixture['delay_ms']))usleep(min(1000,(int)$fixture['delay_ms'])*1000);
            if(($fixture['timeout']??false) && $route==='checkout/sessions')throw new RuntimeException('Simulated ambiguous timeout');
            if(!array_key_exists($route,$fixture['responses']??[]))throw new RuntimeException('Unexpected fixture request');
            $reply=$fixture['responses'][$route];
            if($route==='checkout/sessions')$reply=array_replace(['livemode'=>false,'customer'=>$params['customer'],'client_reference_id'=>$params['client_reference_id'],'metadata'=>$params['metadata']],$reply);
            elseif(str_starts_with($route,'checkout/sessions/')){
                $o=canonicalOrder('session',substr($route,strlen('checkout/sessions/')));
                if($o)$reply=array_replace(['livemode'=>false,'customer'=>$o['stripe_customer_id'],'client_reference_id'=>$o['order_id']],$reply);
            }
            return $reply;
        };
        $u=query('SELECT * FROM users WHERE id=?',[$uid])->fetch();
        $result=createCheckout($u,(string)($fixture['plan']??'mirror'),$transport);
        respond([...$result,'fixture_calls'=>$calls]);
    }
    if(in_array($fixture['kind'],['event','receive','work'],true)){
        $read=function(string $route)use($fixture):array {
            if(db()->inTransaction())throw new LogicException('Network inside transaction');
            if(isset($fixture['scope']))query('INSERT INTO test_provider_calls(scope,method,route,idempotency_key) VALUES(?,?,?,NULL)',[$fixture['scope'],'GET',$route]);
            if(!array_key_exists($route,$fixture['responses']??[]))throw new RuntimeException('Unexpected fixture request');
            if(!empty($fixture['delay_ms']))usleep(min(1000,(int)$fixture['delay_ms'])*1000);
            if(!empty($fixture['steal_lease']))query("UPDATE stripe_inbox SET lease_token=?,lease_until=DATE_ADD(UTC_TIMESTAMP(),INTERVAL 300 SECOND) WHERE environment='test' AND event_id=?",[str_repeat('e',64),$fixture['event']['id']]);
            return $fixture['responses'][$route];
        };
        if($fixture['kind']==='receive')respond(receiveStripeEvent($fixture['event']));
        if($fixture['kind']==='event'){
            $receipt=receiveStripeEvent($fixture['event']);
            $state=query('SELECT status FROM stripe_inbox WHERE environment=? AND event_id=?',[conf('mode'),$fixture['event']['id']])->fetch()['status'];
            if(in_array($state,['processed','ignored'],true))respond(['received'=>true,'duplicate'=>true]);
            // Avancer explicitement l'horloge de reprise du TEST, jamais de flag HTTP.
            query("UPDATE stripe_inbox SET next_attempt_at=UTC_TIMESTAMP() WHERE environment='test' AND event_id=? AND status='retry'",[$fixture['event']['id']]);
        }
        respond(workStripeEvent($read,$fixture['event']['id']));
    }
    if($fixture['kind']==='claim')respond(['claim'=>claimStripeEvent($fixture['event']['id'])!==null]);
    if($fixture['kind']==='job_auth')respond(['allowed'=>bookletJobAuthorized($uid,$fixture['item'],$fixture['offer'])]);
    if($fixture['kind']==='delete'){
        $u=query('SELECT * FROM users WHERE id=?',[$uid])->fetch();
        $transport=function(string $method,string $route,array $params)use($fixture):array {if(db()->inTransaction())throw new LogicException('Network inside transaction');return $fixture['billing']??['has_more'=>false,'data'=>[]];};
        respond(deleteOriginAccount($u,(string)($fixture['password']??''),'SUPPRIMER',$transport));
    }
    if($fixture['kind']==='rights')respond(entitlement($uid));
    if($fixture['kind']==='load')respond(loadBackup($uid,$fixture['revision']??null));
    if($fixture['kind']==='save')respond(saveBackup($uid,$fixtureObject->state,$fixture['base_revision']??null));
    exit(4);
}catch(Throwable $e){rollbackOpenTransaction();respond(['ok'=>false,'fixture_error'=>get_class($e)],503);}
