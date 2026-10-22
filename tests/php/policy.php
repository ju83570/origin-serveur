<?php
declare(strict_types=1);
require '/app/vivant/api/payment-policy.php';
$count = 0;
function check(bool $condition, string $name): void {
    global $count;
    if (!$condition) throw new RuntimeException('Échec : '.$name);
    $count++;
}
check(!paymentPolicy([])['enabled'], 'défaut fermé');
// Chaînes réservées aux TESTS unitaires : aucune requête Stripe n'est effectuée.
$test=['mode'=>'test','stripe_secret'=>'sk_test_unit_fixture','test_payments_enabled'=>true];
check(paymentPolicy($test)['enabled'], 'checkout test disponible sans passer en production');
check(stripeKeyAllowed($test), 'clé test permise en test');
check(!paymentPolicy([...$test,'stripe_secret'=>'sk_live_unit_fixture'])['enabled'], 'clé live rejetée en test');
check(!stripeKeyAllowed([...$test,'stripe_secret'=>'sk_live_unit_fixture']), 'transport live rejeté en test');
check(!paymentPolicy([...$test,'mode'=>'staging'])['enabled'], 'staging sans checkout');
check(!paymentPolicy([...$test,'test_payments_enabled'=>false])['enabled'], 'test désactivable');
check(!stripeKeyAllowed(['mode'=>'production','stripe_secret'=>'sk_live_unit_fixture']), 'production non approuvée rejetée');
check(!paymentPolicy(['mode'=>'production','stripe_secret'=>'sk_live_unit_fixture','legal_approved'=>true,'payments_enabled'=>true])['enabled'], 'drapeaux anciens insuffisants pour activer live');
require '/app/vivant/api/bootstrap.php';
$clear='{"carnet":{"note":"personnel"},"tree":{"people":[]}}';
$sealed=encryptState($clear);
check($sealed!==$clear && !str_contains($sealed,'personnel'), 'chiffrement effectif');
check(decryptState($sealed)===$clear, 'déchiffrement');
check(encryptState($clear)!==$sealed, 'nonce aléatoire');
$bytes=base64_decode($sealed);$bytes[strlen($bytes)-1]=chr(ord($bytes[strlen($bytes)-1])^1);
check(decryptState(base64_encode($bytes))===null, 'altération rejetée');
echo "$count vérifications PHP réussies.\n";
