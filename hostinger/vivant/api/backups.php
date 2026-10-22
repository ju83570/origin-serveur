<?php
declare(strict_types=1);

function readBackupRow(array $row, int $uid): mixed {
    $clear=decryptState($row['sealed_payload'],$uid);
    if($clear===null)fail('Sauvegarde illisible : conserve ta copie locale et contacte le support.',503,'backup_unreadable');
    try{
        $decoded=json_decode($clear,false,512,JSON_THROW_ON_ERROR);
        if(!is_object($decoded))fail('Sauvegarde incompatible : aucune donnée remplacée.',503,'backup_unreadable');
        return $decoded;
    }
    catch(JsonException $e){fail('Sauvegarde illisible : aucune donnée remplacée.',503,'backup_unreadable');}
}

function saveBackup(int $uid, mixed $state, mixed $base): array {
    if(!is_int($base) || $base<0)fail('Récupère d’abord la version de ta sauvegarde.',409,'revision_required');
    $json=json_encode($state,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
    if(strlen($json)>750000)fail('Sauvegarde trop volumineuse',413);
    if(!validBackup($state))fail('Format de sauvegarde incompatible : aucune donnée remplacée.',422,'invalid_backup');
    $features=entitlement($uid)['features'];
    if(!in_array('cloud_carnet',$features,true))fail('Ton offre ne comprend pas cette sauvegarde. La récupération et l’export restent disponibles.',403,'product_required');
    db()->beginTransaction();
    // Verrou du compte : protège aussi la première création et la suppression.
    if(!query('SELECT id FROM users WHERE id=? FOR UPDATE',[$uid])->fetch())throw new RuntimeException('Account unavailable');
    $old=query('SELECT * FROM user_state WHERE user_id=? FOR UPDATE',[$uid])->fetch();
    $revision=$old?(int)$old['revision']:0;
    if($base!==$revision){db()->rollBack();respond(['ok'=>false,'code'=>'revision_conflict','error'=>'Une version plus récente existe. Exporte ta copie locale puis récupère la sauvegarde avant de poursuivre.','current_revision'=>$revision],409);}
    $previous=$old?readBackupRow($old,$uid):null;
    if(!in_array('cloud_tree',$features,true)){
        $previousTree=is_object($previous)?($previous->tree??null):null;
        if($state->tree!==null && json_encode($state->tree)!==json_encode($previousTree)){
            db()->rollBack();fail('Ton offre ne comprend pas la sauvegarde de l’arbre. Exporte-le sur ton appareil.',403,'tree_product_required');
        }
        // Une résiliation/rétrogradation ne doit jamais effacer l’arbre existant.
        $state->tree=$previousTree;$json=json_encode($state,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
    }
    $sealed=encryptState($json,$uid);
    if($old)query('INSERT INTO user_state_history(user_id,revision,sealed_payload,updated_at) VALUES(?,?,?,?)',[$uid,$revision,$old['sealed_payload'],$old['updated_at']]);
    query('INSERT INTO user_state(user_id,sealed_payload,revision,updated_at) VALUES(?,?,?,UTC_TIMESTAMP()) ON DUPLICATE KEY UPDATE sealed_payload=VALUES(sealed_payload),revision=VALUES(revision),updated_at=UTC_TIMESTAMP()',[$uid,$sealed,$revision+1]);
    query('DELETE FROM user_state_history WHERE user_id=? AND revision<?',[$uid,max(0,$revision-9)]);
    db()->commit();
    return ['ok'=>true,'revision'=>$revision+1,'message'=>'Sauvegarde privée réalisée ; les versions précédentes restent récupérables.'];
}

function loadBackup(int $uid, mixed $revision=null): array {
    if($revision!==null && (!is_int($revision) || $revision<1))fail('Version invalide');
    $current=query('SELECT * FROM user_state WHERE user_id=?',[$uid])->fetch();
    $row=$current;
    if($revision!==null && (!$current || (int)$current['revision']!==$revision))
        $row=query('SELECT * FROM user_state_history WHERE user_id=? AND revision=?',[$uid,$revision])->fetch();
    if($revision!==null && !$row)fail('Version introuvable',404);
    return ['ok'=>true,'state'=>$row?readBackupRow($row,$uid):null,'revision'=>$row?(int)$row['revision']:0,
        'current_revision'=>$current?(int)$current['revision']:0,'updated_at'=>$row['updated_at']??null];
}
