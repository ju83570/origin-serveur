<?php
declare(strict_types=1);
require __DIR__.'/bootstrap.php';
require __DIR__.'/backups.php';
require __DIR__.'/stripe-inbox.php';
require __DIR__.'/accounts.php';
require __DIR__.'/checkout.php';
$op=(string)($_GET['op']??'status');
$method=(string)($_SERVER['REQUEST_METHOD']??'GET');
try {
 if ($op==='status' && $method==='GET') {
   $u=currentUser(); respond(['ok'=>true,'mode'=>(string)conf('mode','staging'),'payments_enabled'=>paymentPolicy($cfg)['enabled'],'stripe_test_mode'=>conf('mode')==='test','csrf'=>$_SESSION['csrf'],'user'=>publicUser($u),'entitlements'=>$u?entitlement((int)$u['id']):null,'plans'=>['individual'=>['label'=>'ORIGIN Personnel','price'=>'9,90 € / mois','enabled'=>paymentPolicy($cfg)['enabled']&&(bool)(conf('stripe_prices',[])['individual']??false)],'family'=>['label'=>'ORIGIN Famille','price'=>'19,90 € / mois','enabled'=>(bool)conf('family_ready',false)&&paymentPolicy($cfg)['enabled']&&(bool)(conf('stripe_prices',[])['family']??false)],'mirror'=>['label'=>'Miroir approfondi','price'=>'19 €','enabled'=>(bool)conf('mirror_paid_ready',false)&&paymentPolicy($cfg)['enabled']&&(bool)(conf('stripe_prices',[])['mirror']??false)]]]);
 }
 if($op==='verify' && $method==='GET'){
   $token=(string)($_GET['token']??'');if(!preg_match('/^[a-f0-9]{64}$/',$token))fail('Lien invalide',400);
   $st=query('SELECT user_id FROM email_tokens WHERE token_hash=? AND expires_at>UTC_TIMESTAMP()', [hash('sha256',$token)]);$found=$st->fetch();if(!$found)fail('Lien expiré ou invalide',410);
   query('UPDATE users SET verified_at=UTC_TIMESTAMP() WHERE id=?',[$found['user_id']]);query('DELETE FROM email_tokens WHERE user_id=?',[$found['user_id']]);
   header('Location: '.rtrim((string)conf('site_url'),'/').'/?email_confirmee=1',true,303);exit;
 }
 if($op==='webhook'&&$method==='POST'){
   $raw=file_get_contents('php://input');if(strlen($raw)>250000)fail('Payload trop volumineux',413);
   $secret=(string)conf('stripe_webhook_secret');if(!$secret)fail('Webhook non configuré',503);
   $header=(string)($_SERVER['HTTP_STRIPE_SIGNATURE']??'');$parts=[];foreach(explode(',',$header) as $p){$kv=explode('=',trim($p),2);if(count($kv)===2)$parts[$kv[0]][]=$kv[1];}
   $t=$parts['t'][0]??'';if(!ctype_digit($t)||abs(time()-(int)$t)>300)fail('Signature expirée',400);
   $expected=hash_hmac('sha256',$t.'.'.$raw,$secret);$valid=false;foreach(($parts['v1']??[])as $sig)if(hash_equals($expected,$sig)){$valid=true;break;}if(!$valid)fail('Signature incorrecte',400);
   $event=json_decode($raw,true);if(!is_array($event)||empty($event['id'])||empty($event['type']))fail('Événement invalide');if(conf('mode','staging')==='production' && ($event['livemode']??null)!==true)fail('Événement Stripe de test reçu en production',400);if(conf('mode','staging')!=='production' && ($event['livemode']??null)!==false)fail('Événement Stripe réel rejeté en préproduction',400);
   try {respond(receiveStripeEvent($event));}catch(InvalidArgumentException $e){fail('Événement Stripe invalide',400);}
 }
 if($method!=='POST')fail('Méthode non autorisée',405);
 csrf();$data=input();
 if($op==='register'){
   rate('signup',ip(),5,60);$email=mb_strtolower(trim((string)($data['email']??'')));$pw=(string)($data['password']??'');
   if(!filter_var($email,FILTER_VALIDATE_EMAIL)||strlen($email)>190||strlen($pw)<12||strlen($pw)>200)fail('Adresse email ou mot de passe invalide (12 caractères minimum)');
   if(($data['consent']??null)!==true)fail('Lis et accepte la politique de confidentialité');
   try{query('INSERT INTO users(email,password_hash,privacy_version,privacy_accepted_at,created_at) VALUES(?,?,?,UTC_TIMESTAMP(),UTC_TIMESTAMP())',[$email,password_hash($pw,PASSWORD_DEFAULT),'2026-10-v1']);}catch(PDOException $e){if($e->getCode()==='23000')fail('Cette adresse est déjà utilisée',409);throw $e;}
   $id=(int)db()->lastInsertId();$u=['id'=>$id,'email'=>$email];emailVerify($u);respond(['ok'=>true,'message'=>'Un email de vérification a été envoyé.']);
 }
 if($op==='password_reset_request'){
   rate('reset_request',ip(),5,60);
   $email=mb_strtolower(trim((string)($data['email']??'')));
   if(filter_var($email,FILTER_VALIDATE_EMAIL) && strlen($email)<=190){
     $u=query('SELECT id,email FROM users WHERE email=?',[$email])->fetch();
     if($u){
       $token=bin2hex(random_bytes(32));
       query('INSERT INTO password_resets(user_id,token_hash,expires_at) VALUES(?,?,DATE_ADD(UTC_TIMESTAMP(), INTERVAL 45 MINUTE)) ON DUPLICATE KEY UPDATE token_hash=VALUES(token_hash),expires_at=VALUES(expires_at)',[$u['id'],hash('sha256',$token)]);
       $link=rtrim((string)conf('site_url'),'/').'/?reinitialiser='.$token;
       smtpSend((string)$u['email'],'Réinitialiser ton accès ORIGIN',"Un changement de mot de passe a été demandé pour cet email.\n\nChoisis ton nouveau mot de passe via ce lien :\n{$link}\n\nLe lien expire dans 45 minutes. Si ce n'était pas toi, ignore cet email.");
     }
   }
   respond(['ok'=>true,'message'=>'Si un compte correspond à cette adresse, un lien de réinitialisation a été envoyé.']);
 }
 if($op==='password_reset'){
   rate('reset_use',ip(),8,60);
   $token=(string)($data['token']??'');$pw=(string)($data['password']??'');
   if(!preg_match('/^[a-f0-9]{64}$/',$token) || strlen($pw)<12 || strlen($pw)>200)fail('Lien invalide ou mot de passe trop court (12 caractères minimum)');
   db()->beginTransaction();
   try {
     $found=query('SELECT user_id FROM password_resets WHERE token_hash=? AND expires_at>UTC_TIMESTAMP() FOR UPDATE', [hash('sha256',$token)])->fetch();
     if(!$found){db()->rollBack();fail('Lien expiré ou déjà utilisé. Demande un nouveau lien.',410,'reset_expired');}
     query('UPDATE users SET password_hash=?,session_version=session_version+1 WHERE id=?',[password_hash($pw,PASSWORD_DEFAULT),$found['user_id']]);
     query('DELETE FROM password_resets WHERE user_id=?',[$found['user_id']]);
     db()->commit();
   } catch(Throwable $e){db()->rollBack();throw $e;}
   // A password reset does not grant an authenticated session.
   respond(['ok'=>true,'message'=>'Mot de passe modifié. Tu peux maintenant te connecter.']);
 }
 if($op==='login'){
   $email=mb_strtolower(trim((string)($data['email']??'')));rate('login_ip',ip(),60,15);rate('login_account',$email,12,15);$pw=(string)($data['password']??'');$u=query('SELECT * FROM users WHERE email=?',[$email])->fetch();
   if(!$u || !password_verify($pw,$u['password_hash']))fail('Identifiants incorrects',401);
   if(!$u['verified_at'])fail('Confirme ton adresse email avant de te connecter.',403,'email_unverified');
   session_regenerate_id(true);$_SESSION['user_id']=(int)$u['id'];$_SESSION['session_version']=(int)$u['session_version'];$_SESSION['csrf']=bin2hex(random_bytes(24));respond(['ok'=>true,'csrf'=>$_SESSION['csrf'],'user'=>publicUser($u),'entitlements'=>entitlement((int)$u['id'])]);
 }
 if($op==='logout'){
   $_SESSION=[];session_regenerate_id(true);$_SESSION['csrf']=bin2hex(random_bytes(24));respond(['ok'=>true,'csrf'=>$_SESSION['csrf']]);
 }
 if($op==='resend'){
   rate('resend',ip(),4,60);$email=mb_strtolower(trim((string)($data['email']??'')));$u=query('SELECT id,email,verified_at FROM users WHERE email=?',[$email])->fetch();if($u && !$u['verified_at'])emailVerify($u);respond(['ok'=>true,'message'=>'Si cette adresse existe, un nouveau message a été envoyé.']);
 }
 if($op==='save'){
   $u=verified();rate('backup_save',(string)$u['id'],30,15);
   $body=json_decode(file_get_contents('php://input'));
   respond(saveBackup((int)$u['id'],$body->state??null,$body->base_revision??null));
 }
 if($op==='load' || $op==='export'){
   $u=verified();rate('backup_read',(string)$u['id'],90,15);
   respond(loadBackup((int)$u['id'],$data['revision']??null));
 }
 if($op==='versions'){
   $u=verified();$rows=query('SELECT revision,updated_at FROM user_state_history WHERE user_id=? ORDER BY revision DESC',[$u['id']])->fetchAll();
   respond(['ok'=>true,'versions'=>$rows]);
 }
 if($op==='checkout'){
   $u=verified();rate('checkout',(string)$u['id'],8,15);respond(createCheckout($u,(string)($data['plan']??'')));
 }
 if($op==='portal'){
   $u=verified();if(!$u['stripe_customer_id'])fail('Aucun abonnement Stripe associé');$s=stripe('POST','billing_portal/sessions',['customer'=>$u['stripe_customer_id'],'return_url'=>rtrim((string)conf('site_url'),'/').'/']);respond(['ok'=>true,'portal_url'=>$s['url']??null]);
 }
 if($op==='delete'){
   $u=verified();rate('delete_account',(string)$u['id'],5,60);
   $result=deleteOriginAccount($u,(string)($data['password']??''),(string)($data['confirm']??''));
   $_SESSION=[];session_regenerate_id(true);$_SESSION['csrf']=bin2hex(random_bytes(24));respond($result);
 }
 fail('Action inconnue',404);
} catch(PDOException $e){rollbackOpenTransaction();error_log('ORIGIN database error code '.(string)$e->getCode());fail('Service temporairement indisponible',503);} catch(RuntimeException $e){rollbackOpenTransaction();error_log('ORIGIN service unavailable '.get_class($e));fail('Service temporairement indisponible',503);} catch(Throwable $e){rollbackOpenTransaction();error_log('ORIGIN technical failure '.get_class($e));fail('Une erreur technique est survenue',500);}