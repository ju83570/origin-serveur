<?php
declare(strict_types=1);
// Load configuration OUTSIDE document root. Never store secrets in /public_html.
ini_set('display_errors', '0');
error_reporting(E_ALL);
require_once __DIR__.'/payment-policy.php';
require_once __DIR__.'/security-policy.php';
require_once __DIR__.'/registry.php';
$configFile = getenv('ORIGIN_VIVANT_CONFIG') ?: dirname((string)($_SERVER['DOCUMENT_ROOT'] ?? dirname(__DIR__,3))) . '/origin-vivant-config.php';
if (!is_file($configFile)) {
    http_response_code(503);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['error'=>'Configuration non installée','code'=>'not_configured']);
    exit;
}
$cfg = require $configFile;
$originDatabase = null;
if (!is_array($cfg)) { http_response_code(503); exit; }
if (PHP_SAPI !== 'cli' && !empty($cfg['https_required']) && (empty($_SERVER['HTTPS']) || $_SERVER['HTTPS'] === 'off') && (!in_array((string)($_SERVER['REMOTE_ADDR'] ?? ''), (array)($cfg['trusted_proxy_ips'] ?? []), true) || (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') !== 'https'))) {
    http_response_code(403); header('Content-Type: application/json'); echo '{"error":"HTTPS requis"}'; exit;
}
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: same-origin');
header('Cache-Control: no-store');
header('Content-Type: application/json; charset=utf-8');
header("Content-Security-Policy: default-src 'none'; frame-ancestors 'none'");
function conf(string $key, mixed $default=null):mixed { global $cfg;return $cfg[$key] ?? $default; }
function respond(array $data, int $code=200):never { http_response_code($code); echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_INVALID_UTF8_SUBSTITUTE); exit; }
function fail(string $message, int $status=400, string $code='error'):never { respond(['ok'=>false,'error'=>$message,'code'=>$code],$status); }
function db():PDO { global $originDatabase; if ($originDatabase instanceof PDO) return $originDatabase; $originDatabase=new PDO((string)conf('db_dsn'),(string)conf('db_user'),(string)conf('db_password'),[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,PDO::ATTR_EMULATE_PREPARES=>false]); return $originDatabase; }
function rollbackOpenTransaction():void { global $originDatabase; if($originDatabase instanceof PDO && $originDatabase->inTransaction())$originDatabase->rollBack(); }
function query(string $sql, array $params=[]):PDOStatement { $st=db()->prepare($sql);$st->execute($params);return $st; }
function input():array { $raw=file_get_contents('php://input'); if (strlen($raw)>1048576) fail('Contenu trop volumineux',413); $v=json_decode($raw?:'{}',true); if (!is_array($v)) fail('JSON invalide');return $v; }
function rate(string $bucket, string $key, int $limit, int $minutes):void {
    $hash=hash_hmac('sha256',$bucket.'|'.$key,purposeKey('rate-limit'));$window=intdiv(time(),$minutes*60)*($minutes*60);
    query('INSERT INTO rate_limit_counters(bucket,fingerprint,window_start,attempts) VALUES(?,?,?,1) ON DUPLICATE KEY UPDATE attempts=attempts+1',[$bucket,$hash,$window]);
    $n=(int)query('SELECT attempts FROM rate_limit_counters WHERE bucket=? AND fingerprint=? AND window_start=?',[$bucket,$hash,$window])->fetch()['attempts'];
    if(random_int(1,100)===1)query('DELETE FROM rate_limit_counters WHERE window_start<?',[time()-172800]);
    if($n>$limit){header('Retry-After: '.max(1,$window+$minutes*60-time()));fail('Trop de tentatives. Réessaie plus tard.',429,'rate_limited');}
}
function ip():string {return proxyClientIp($_SERVER,(array)conf('trusted_proxy_ips',[]));}
function makeSession():void { if(session_status()===PHP_SESSION_ACTIVE)return;session_name('origin_vivant_sid');session_set_cookie_params(['lifetime'=>0,'path'=>'/vivant','secure'=>true,'httponly'=>true,'samesite'=>'Lax']);ini_set('session.use_strict_mode','1');session_start(); if (!isset($_SESSION['csrf'])) $_SESSION['csrf']=bin2hex(random_bytes(24)); }
function csrf():void {makeSession();$v=(string)($_SERVER['HTTP_X_CSRF_TOKEN']??'');if ($v==='' || !hash_equals((string)$_SESSION['csrf'],$v)) fail('Protection CSRF requise',403,'csrf');}
function currentUser():?array {makeSession();$id=(int)($_SESSION['user_id']??0);if ($id<=0)return null;$user=query('SELECT id,email,verified_at,stripe_customer_id,created_at,session_version FROM users WHERE id=?',[$id])->fetch();if ($user && (int)($_SESSION['session_version'] ?? 0) !== (int)$user['session_version']) { unset($_SESSION['user_id']); return null; }return $user ?: null;}
function user():array {$u=currentUser();if(!$u)fail('Connecte-toi pour continuer.',401,'login_required');return $u;}
function verified():array {$u=user();if(!$u['verified_at'])fail('Confirme ton adresse email.',403,'email_unverified');return $u;}
function publicUser(?array $u):?array {if(!$u)return null;return ['id'=>(int)$u['id'],'email'=>$u['email'],'verified'=>(bool)$u['verified_at']];}
function keyBytes(?string $id=null):string {
    $k=$id===null?(string)conf('app_key'):(string)(conf('encryption_keys',[])[$id]??($id==='legacy'?conf('app_key'):''));
    $b=base64_decode($k,true);
    if($b===false || strlen($b)!==32 || base64_encode($b)!==$k)throw new RuntimeException('Encryption configuration invalid');
    return $b;
}
function purposeKey(string $purpose,?string $id=null):string {
    return hash_hkdf('sha256',keyBytes($id),32,'origin-vivant/'.$purpose.'/v2','origin-vivant-hkdf-v2');
}
function payloadAad(string $id,string $purpose,string $subject):string {
    return json_encode(['v'=>2,'kid'=>$id,'environment'=>(string)conf('mode'),'purpose'=>$purpose,'subject'=>$subject],JSON_THROW_ON_ERROR);
}
function sealPayload(string $clear,string $purpose,string $subject):string {
    $id=(string)conf('encryption_key_id','legacy');
    if(!preg_match('/^[a-zA-Z0-9_-]{1,40}$/',$id))throw new RuntimeException('Encryption key id invalid');
    $nonce=random_bytes(SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES);
    return 'ov2:'.$id.':'.base64_encode($nonce.sodium_crypto_aead_xchacha20poly1305_ietf_encrypt($clear,payloadAad($id,$purpose,$subject),$nonce,purposeKey($purpose,$id)));
}
function openPayload(string $blob,string $purpose,string $subject):?string {
    $p=explode(':',$blob);if(count($p)!==3 || $p[0]!=='ov2')return null;
    $v=base64_decode($p[2],true);
    if($v===false || strlen($v)<SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES+SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_ABYTES)return null;
    try{
        $nonce=substr($v,0,SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES);
        $clear=sodium_crypto_aead_xchacha20poly1305_ietf_decrypt(substr($v,SODIUM_CRYPTO_AEAD_XCHACHA20POLY1305_IETF_NPUBBYTES),payloadAad($p[1],$purpose,$subject),$nonce,purposeKey($purpose,$p[1]));
        return $clear===false?null:$clear;
    }catch(Throwable $e){return null;}
}
function encryptState(string $json,int $uid=0):string {return sealPayload($json,'family-backup','user:'.$uid);}
function decryptState(string $blob,int $uid=0):?string {
    if(str_starts_with($blob,'ov2:'))return openPayload($blob,'family-backup','user:'.$uid);
    // Lecture des formats historiques uniquement ; aucune nouvelle écriture.
    $parts=explode(':',$blob);$versioned=count($parts)===3 && $parts[0]==='ov1';
    if(count($parts)!==1 && !$versioned)return null;
    $id=$versioned?$parts[1]:null;$encoded=$versioned?$parts[2]:$blob;
    $v=base64_decode($encoded,true);
    if($v===false || strlen($v)<SODIUM_CRYPTO_SECRETBOX_NONCEBYTES+SODIUM_CRYPTO_SECRETBOX_MACBYTES)return null;
    try{$key=keyBytes($id);}catch(Throwable $e){return null;}
    $nonce=substr($v,0,SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
    $clear=sodium_crypto_secretbox_open(substr($v,SODIUM_CRYPTO_SECRETBOX_NONCEBYTES),$nonce,$key);
    if($clear===false)return null;if(!$versioned)return $clear;
    $decoded=json_decode($clear,true);
    return is_array($decoded) && ($decoded['owner']??null)===$uid && is_string($decoded['json']??null)?$decoded['json']:null;
}
function smtpSend(string $to,string $subject,string $body):void { // SMTP TLS required for verification mail; do not send secrets through PHP mail().
 $host=(string)conf('smtp_host');$port=(int)conf('smtp_port',587);$from=(string)conf('smtp_from');$user=(string)conf('smtp_user');$pass=(string)conf('smtp_password');
 if(!$host || !$from || !$user || !$pass) fail('Envoi email non configuré',503);
 $socket=@stream_socket_client("tcp://{$host}:{$port}",$errNo,$errStr,12,STREAM_CLIENT_CONNECT);if(!$socket)fail('Service email indisponible',503);
 stream_set_timeout($socket,12);
 $read=function()use($socket):string{$out='';for($i=0;$i<30;$i++){$l=fgets($socket,2048);if($l===false)throw new RuntimeException('SMTP read');$out.=$l;if(strlen($l)<4||$l[3]===' ')break;}return $out;};
 $send=function(string $line,array $codes)use($socket,$read):void{fwrite($socket,$line."\r\n");$resp=$read();if(!in_array((int)substr($resp,0,3),$codes,true))throw new RuntimeException('SMTP error');};
 try{$greet=$read();if((int)substr($greet,0,3)!==220)throw new RuntimeException('SMTP greet');$send('EHLO origin-famille.fr',[250]);$send('STARTTLS',[220]);if(!stream_socket_enable_crypto($socket,true,STREAM_CRYPTO_METHOD_TLS_CLIENT))throw new RuntimeException('SMTP TLS');$send('EHLO origin-famille.fr',[250]);$send('AUTH LOGIN',[334]);$send(base64_encode($user),[334]);$send(base64_encode($pass),[235]);$send('MAIL FROM:<'.$from.'>',[250]);$send('RCPT TO:<'.$to.'>',[250,251]);$send('DATA',[354]);$headers='From: ORIGIN <'.$from.'>' . "\r\n" . 'To: <'.$to.'>' . "\r\n" . 'Subject: =?UTF-8?B?'.base64_encode($subject).'?=' . "\r\n" . "MIME-Version: 1.0\r\nContent-Type: text/plain; charset=UTF-8\r\n";
 $msg=$headers."\r\n".$body;$msg=preg_replace('/^\./m','..',$msg);fwrite($socket,str_replace("\n","\r\n",str_replace("\r\n","\n",$msg))."\r\n.\r\n");$done=$read();if((int)substr($done,0,3)!==250)throw new RuntimeException('SMTP data');$send('QUIT',[221]);}catch(Throwable $e){error_log('ORIGIN SMTP failure '.$e->getMessage());fail('Impossible d’envoyer cet email maintenant.',503);}finally{fclose($socket);}
}
function emailVerify(array $u):void {$token=bin2hex(random_bytes(32));query('DELETE FROM email_tokens WHERE user_id=?',[$u['id']]);query('INSERT INTO email_tokens(user_id,token_hash,expires_at) VALUES(?,?,DATE_ADD(UTC_TIMESTAMP(), INTERVAL 1 DAY))',[$u['id'],hash('sha256',$token)]);$link=rtrim((string)conf('site_url'),'/' ).'/api/?op=verify&token='.$token;smtpSend((string)$u['email'],'Confirme ton adresse ORIGIN',"Bienvenue sur ORIGIN VIVANT !\n\nConfirme ton adresse en ouvrant ce lien :\n{$link}\n\nCe lien expire dans 24 heures. Si tu n'es pas à l'origine de cette demande, ignore ce message.");}
function stripe(string $method,string $route,array $params=[],?string $idempotency=null):array {
    global $cfg;
    if(db()->inTransaction())throw new LogicException('Stripe network transaction forbidden');
    if(!stripeKeyAllowed($cfg))throw new RuntimeException('Stripe environment not configured');
    $headers=['Authorization: Bearer '.(string)conf('stripe_secret'),'Stripe-Version: 2025-08-27.basil'];
    if($idempotency!==null)$headers[]='Idempotency-Key: '.$idempotency;
    $url='https://api.stripe.com/v1/'.$route;
    if($method==='GET' && $params)$url.='?'.http_build_query($params);
    $ch=curl_init($url);curl_setopt_array($ch,[CURLOPT_RETURNTRANSFER=>true,CURLOPT_TIMEOUT=>20,CURLOPT_CUSTOMREQUEST=>$method,CURLOPT_HTTPHEADER=>$headers,CURLOPT_SSL_VERIFYPEER=>true]);
    if($method==='POST')curl_setopt($ch,CURLOPT_POSTFIELDS,http_build_query($params));
    $result=curl_exec($ch);$status=curl_getinfo($ch,CURLINFO_HTTP_CODE);curl_close($ch);$obj=json_decode((string)$result,true);
    if(!is_array($obj)||$status<200||$status>=300)throw new RuntimeException('Stripe transport failure HTTP '.(int)$status);
    return $obj;
}
function entitlement(int $id):array {return registryEntitlement($id);}
