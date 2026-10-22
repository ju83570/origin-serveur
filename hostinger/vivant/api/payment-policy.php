<?php
declare(strict_types=1);

// Fonctions pures : testables sans Stripe, compte client ou identifiants réels.
function paymentPolicy(array $config): array {
    $mode = (string)($config['mode'] ?? 'staging');
    $secret = (string)($config['stripe_secret'] ?? '');
    $test = $mode === 'test';
    $enabled = $test
        ? ($config['test_payments_enabled'] ?? false) === true && str_starts_with($secret, 'sk_test_')
        : $mode === 'production'
          && ($config['live_payments_approved'] ?? false) === true
          && ($config['legal_approved'] ?? false) === true
          && ($config['payments_enabled'] ?? false) === true
          && str_starts_with($secret, 'sk_live_');
    return ['enabled'=>$enabled, 'test'=>$test, 'mode'=>$mode];
}

function stripeKeyAllowed(array $config): bool {
    $mode = (string)($config['mode'] ?? 'staging');
    $secret = (string)($config['stripe_secret'] ?? '');
    if (in_array($mode, ['staging', 'test'], true)) return str_starts_with($secret, 'sk_test_');
    return $mode === 'production'
        && ($config['live_payments_approved'] ?? false) === true
        && str_starts_with($secret, 'sk_live_');
}
