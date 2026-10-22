<?php
declare(strict_types=1);
require __DIR__.'/bootstrap.php';
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
   $eventId=(string)$event['id'];db()->beginTransaction();
   try { query('INSERT INTO stripe_events(event_id,event_type,processed_at) VALUES(?,?,UTC_TIMESTAMP())',[$eventId,(string)$event['type']]); }
   catch(PDOException $e) { if($e->getCode()==='23000'){db()->rollBack();respond(['received'=>true,'duplicate'=>true]);} throw $e; }
   $type=(string)$event['type'];$obj=$event['data']['object']??[];
   if($type==='checkout.session.completed' && is_array($obj)){
     $uid=(int)($obj['client_reference_id']??0);$customer=is_string($obj['customer']??null)?$obj['customer']:null;
     if($uid>0 && query('SELECT id FROM users WHERE id=?',[$uid])->fetch()){
       if($customer)query('UPDATE users SET stripe_customer_id=? WHERE id=? AND (stripe_customer_id IS NULL OR stripe_customer_id=?)',[$customer,$uid,$customer]);
       if(($obj['mode']??'')==='payment'&&($obj['payment_status']??'')==='paid'&&($obj['metadata']['plan']??'')==='mirror'){
         query('INSERT INTO purchases(user_id,stripe_session_id,status,created_at) VALUES(?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE status=VALUES(status)',[$uid,(string)$obj['id'],'paid']);
       }
       if(($obj['mode']??'')==='subscription' && is_string($obj['subscription']??null)) {
         $sub=stripe('GET','subscriptions/'.rawurlencode($obj['subscription'])); upsertSubscription($sub,$uid);
       }
     }
   }
   if(in_array($type,['customer.subscription.created','customer.subscription.updated','customer.subscription.deleted'],true)&&is_array($obj)) {
     $customer=$obj['customer']??null;$owner=null;
     if(is_string($customer))$owner=query('SELECT id FROM users WHERE stripe_customer_id=?',[$customer])->fetch();
     if(!$owner && !empty($obj['metadata']['origin_user_id']))$owner=query('SELECT id FROM users WHERE id=?',[(int)$obj['metadata']['origin_user_id']])->fetch();
     if($owner)upsertSubscription($obj,(int)$owner['id']);
   }
   // L'événement et ses effets sont validés ensemble ; un échec libère le rejeu.
   db()->commit();respond(['received'=>true]);
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
   rate('login',ip(),12,15);$email=mb_strtolower(trim((string)($data['email']??'')));$pw=(string)($data['password']??'');$u=query('SELECT * FROM users WHERE email=?',[$email])->fetch();
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
   $u=verified();if(conf('mode','staging')==='production' && !entitlement((int)$u['id'])['plans']) fail('Un abonnement actif est nécessaire pour la sauvegarde en ligne.',402,'subscription_required');$payload=$data['state']??null;$originalState=json_decode(file_get_contents('php://input'))->state??null;$json=json_encode($originalState,JSON_UNESCAPED_UNICODE|JSON_INVALID_UTF8_SUBSTITUTE);if(!is_array($payload)||$json===false||strlen($json)>750000)fail('Fichier personnel invalide ou trop volumineux',413);
   $sealed=encryptState($json);query('INSERT INTO user_state(user_id,sealed_payload,updated_at) VALUES(?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE sealed_payload=VALUES(sealed_payload),updated_at=UTC_TIMESTAMP()',[$u['id'],$sealed]);respond(['ok'=>true,'message'=>'Sauvegarde privée réalisée']);
 }
 if($op==='load'){
   $u=verified();if(conf('mode','staging')==='production' && !entitlement((int)$u['id'])['plans']) fail('Un abonnement actif est nécessaire pour synchroniser le carnet.',402,'subscription_required');$r=query('SELECT sealed_payload,updated_at FROM user_state WHERE user_id=?',[$u['id']])->fetch();$v=$r?decryptState($r['sealed_payload']):null;if($r && $v===null)fail('Sauvegarde illisible : conserve ta copie locale et contacte le support.',503,'backup_unreadable');respond(['ok'=>true,'state'=>$v?json_decode($v):null,'updated_at'=>$r['updated_at']??null]);
 }
 if($op==='checkout'){
   $u=verified();if(!paymentPolicy($cfg)['enabled'])fail('Paiements désactivés. Le checkout de test nécessite le mode test et son activation explicite.',503);
   $plan=(string)($data['plan']??'');if(!in_array($plan,['individual','family','mirror'],true))fail('Offre inconnue');
   if($plan==='family'&&!conf('family_ready',false))fail('Offre Famille non lancée');
   if($plan==='mirror'&&!conf('mirror_paid_ready',false))fail('Offre Miroir non lancée');
   $price=(string)(conf('stripe_prices',[])[$plan]??'');if(!preg_match('/^price_[A-Za-z0-9]+$/',$price))fail('Tarif non configuré',503);
   $customer=$u['stripe_customer_id'];if(!$customer){$new=stripe('POST','customers',['email'=>$u['email'],'metadata'=>['origin_user_id'=>$u['id']]]);$customer=$new['id'];query('UPDATE users SET stripe_customer_id=? WHERE id=?',[$customer,$u['id']]);}
   $mode=$plan==='mirror'?'payment':'subscription';
   $params=['mode'=>$mode,'customer'=>$customer,'client_reference_id'=>(string)$u['id'],'line_items'=>[['price'=>$price,'quantity'=>1]],'metadata'=>['plan'=>$plan,'origin_user_id'=>(string)$u['id']],'success_url'=>rtrim((string)conf('site_url'),'/').'/?paiement=retour&session_id={CHECKOUT_SESSION_ID}','cancel_url'=>rtrim((string)conf('site_url'),'/').'/?paiement=annule','locale'=>'fr'];
   if($mode==='subscription')$params['subscription_data']=['metadata'=>['plan'=>$plan,'origin_user_id'=>(string)$u['id']]];
   $checkout=stripe('POST','checkout/sessions',$params);respond(['ok'=>true,'checkout_url'=>$checkout['url']??null]);
 }
 if($op==='portal'){
   $u=verified();if(!$u['stripe_customer_id'])fail('Aucun abonnement Stripe associé');$s=stripe('POST','billing_portal/sessions',['customer'=>$u['stripe_customer_id'],'return_url'=>rtrim((string)conf('site_url'),'/').'/']);respond(['ok'=>true,'portal_url'=>$s['url']??null]);
 }
 if($op==='delete'){
   $u=verified();$ent=entitlement((int)$u['id']);if($ent['plans'])fail('Résilie d’abord les abonnements actifs depuis le portail Stripe, puis demande la suppression.',409);
   if(($data['confirm']??'')!=='SUPPRIMER')fail('Confirmation de suppression requise');
   // FK cascades data. Stripe customer is deliberately retained for legitimate bookkeeping.
   query('DELETE FROM users WHERE id=?',[$u['id']]);$_SESSION=[];session_regenerate_id(true);$_SESSION['csrf']=bin2hex(random_bytes(24));respond(['ok'=>true,'message'=>'Compte et données personnelles de l’application supprimés']);
 }
 fail('Action inconnue',404);
} catch(PDOException $e){rollbackOpenTransaction();error_log('ORIGIN database: '.$e->getMessage());fail('Service temporairement indisponible',503);} catch(Throwable $e){rollbackOpenTransaction();error_log('ORIGIN: '.$e->getMessage());fail('Une erreur technique est survenue',500);}
function upsertSubscription(array $s,int $uid):void {
 $price=(string)($s['items']['data'][0]['price']['id']??'');$plan=(string)($s['metadata']['plan']??'');
 if(!in_array($plan,['individual','family'],true)){foreach((array)conf('stripe_prices',[]) as $k=>$p)if($p===$price)$plan=$k;}
 if(!in_array($plan,['individual','family'],true))return;
 $periodEnd=$s['items']['data'][0]['current_period_end']??$s['current_period_end']??null;$end=$periodEnd?gmdate('Y-m-d H:i:s',(int)$periodEnd):null;
 query('INSERT INTO subscriptions(user_id,stripe_subscription_id,plan,status,current_period_end,updated_at) VALUES(?,?,?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE user_id=VALUES(user_id),plan=VALUES(plan),status=VALUES(status),current_period_end=VALUES(current_period_end),updated_at=UTC_TIMESTAMP()',[$uid,(string)$s['id'],$plan,(string)$s['status'],$end]);
}
