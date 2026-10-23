<?php
declare(strict_types=1);
// Installer HORS document root et lancer par cron/CLI, jamais par HTTP.
if(PHP_SAPI!=='cli')exit(2);
require dirname(__DIR__,2).'/hostinger/vivant/api/bootstrap.php';
require dirname(__DIR__,2).'/hostinger/vivant/api/stripe-inbox.php';
if(($argv[1]??'')==='--status'){
    echo json_encode(query('SELECT status,COUNT(*) AS count FROM stripe_inbox WHERE environment=? GROUP BY status',[conf('mode')])->fetchAll()).PHP_EOL;exit;
}
if(($argv[1]??'')==='--retry'){
    $id=(string)($argv[2]??'');if(!preg_match('/^evt_[A-Za-z0-9_]{1,140}$/',$id))exit(2);
    $updated=query("UPDATE stripe_inbox SET status='retry',attempts=0,next_attempt_at=UTC_TIMESTAMP(),last_error=NULL WHERE environment=? AND event_id=? AND status IN ('retry','blocked') AND lease_token IS NULL",[conf('mode'),$id]);
    echo json_encode(['rescheduled'=>$updated->rowCount()]).PHP_EOL;exit;
}
$limit=20;
for($n=0;$n<$limit;$n++){
    $result=workStripeEvent(fn(string $route):array=>stripe('GET',$route));
    if(!$result['worked'])break;
    echo json_encode($result,JSON_UNESCAPED_SLASHES).PHP_EOL;
}
