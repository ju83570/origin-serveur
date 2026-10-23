<?php
declare(strict_types=1);

function deleteOriginAccount(array $u,string $password,string $confirmation,?callable $transport=null):array {
    $transport ??= 'stripe';
    if($confirmation!=='SUPPRIMER')fail('Confirmation de suppression requise');
    $stored=query('SELECT password_hash,session_version FROM users WHERE id=?',[$u['id']])->fetch();
    if(!$stored || !password_verify($password,$stored['password_hash']))fail('Confirme ton mot de passe actuel pour supprimer ce compte.',403,'reauth_required');
    if(query("SELECT id FROM subscriptions WHERE user_id=? AND status NOT IN ('canceled','incomplete_expired') LIMIT 1",[$u['id']])->fetch())fail('Résilie d’abord les abonnements depuis le portail Stripe.',409,'billing_active');
    // Rapprochement distant AVANT tout verrou de suppression.
    if($u['stripe_customer_id']){
        $remote=$transport('GET','subscriptions',['customer'=>$u['stripe_customer_id'],'status'=>'all','limit'=>100]);
        if(($remote['has_more']??true)!==false)throw new RuntimeException('Billing reconciliation incomplete');
        foreach(($remote['data']??[]) as $sub)if(!in_array($sub['status']??'',['canceled','incomplete_expired'],true))fail('Un abonnement Stripe nécessite encore une résiliation.',409,'billing_active');
    }
    db()->beginTransaction();
    $current=query('SELECT password_hash,session_version FROM users WHERE id=? FOR UPDATE',[$u['id']])->fetch();
    if(!$current || $current['password_hash']!==$stored['password_hash'] || (int)$current['session_version']!==(int)$stored['session_version']){
        db()->rollBack();fail('Reconnecte-toi avant de supprimer ce compte.',409,'reauth_required');
    }
    $billing=query("SELECT id FROM subscriptions WHERE user_id=? AND status NOT IN ('canceled','incomplete_expired') LIMIT 1 FOR UPDATE",[$u['id']])->fetch();
    $pending=query("SELECT order_id FROM orders WHERE user_id=? AND status='pending' AND expires_at>UTC_TIMESTAMP() LIMIT 1 FOR UPDATE",[$u['id']])->fetch();
    $creating=query('SELECT user_id FROM customer_bindings WHERE user_id=? AND lease_until>UTC_TIMESTAMP() LIMIT 1 FOR UPDATE',[$u['id']])->fetch();
    if($billing || $pending || $creating){db()->rollBack();fail('Un abonnement ou paiement est encore en cours. Termine-le avant la suppression.',409,'billing_active');}
    query('DELETE FROM users WHERE id=?',[$u['id']]);db()->commit();
    return ['ok'=>true,'message'=>'Compte, données familiales et droits supprimés. Écritures financières détachées du compte et conservées sans nom ni email.'];
}
