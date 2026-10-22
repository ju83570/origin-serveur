<?php
declare(strict_types=1);
// Lanceur CLI strictement dans le conteneur de test. Jamais monté sous /app.
require '/app/vivant/api/bootstrap.php';
require '/app/vivant/api/backups.php';
require '/app/vivant/api/stripe-events.php';
require '/app/vivant/api/checkout.php';
if(PHP_SAPI!=='cli' || conf('mode')!=='test' || !str_starts_with((string)conf('site_url'),'http://127.0.0.1:'))exit(2);
$raw=stream_get_contents(STDIN);
$fixture=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
$fixtureObject=json_decode($raw,false,512,JSON_THROW_ON_ERROR);
$cfg['demo_features_enabled']=false;
$cfg['product_features']=['individual'=>['cloud_carnet'],'family'=>['cloud_carnet','cloud_tree'],'mirror'=>['mirror_deep']];
$uid=(int)($fixture['uid']??0);
if($uid){$u=query('SELECT email FROM users WHERE id=?',[$uid])->fetch();if(!$u || !str_ends_with($u['email'],'@example.invalid'))exit(3);}
try{
    if($fixture['kind']==='checkout'){
        $cfg['stripe_secret']='sk_test_unit_fixture';$cfg['test_payments_enabled']=true;$cfg['mirror_paid_ready']=true;
        $calls=[];
        $transport=function(string $method,string $route,array $params=[],?string $key=null)use($fixture,&$calls):array{
            $calls[]=['method'=>$method,'route'=>$route,'params'=>$params,'idempotency'=>$key];
            if(($fixture['timeout']??false) && $route==='checkout/sessions')throw new RuntimeException('Simulated ambiguous timeout');
            if(!array_key_exists($route,$fixture['responses']??[]))throw new RuntimeException('Unexpected fixture request');
            return $fixture['responses'][$route];
        };
        $u=query('SELECT * FROM users WHERE id=?',[$uid])->fetch();
        $result=createCheckout($u,(string)($fixture['plan']??'mirror'),$transport);
        respond([...$result,'fixture_calls'=>$calls]);
    }
    if($fixture['kind']==='event'){
        $read=function(string $route)use($fixture):array {
            if(!array_key_exists($route,$fixture['responses']??[]))throw new RuntimeException('Unexpected fixture request');
            return $fixture['responses'][$route];
        };
        respond(processStripeEvent($fixture['event'],$read));
    }
    if($fixture['kind']==='rights')respond(entitlement($uid));
    if($fixture['kind']==='load')respond(loadBackup($uid,$fixture['revision']??null));
    if($fixture['kind']==='save')respond(saveBackup($uid,$fixtureObject->state,$fixture['base_revision']??null));
    exit(4);
}catch(Throwable $e){rollbackOpenTransaction();respond(['ok'=>false,'fixture_error'=>get_class($e)],503);}
