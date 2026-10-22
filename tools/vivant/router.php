<?php
// Routeur du serveur PHP de TEST : Apache appliquera les .htaccess sur Hostinger.
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if ($path === '/vivant/api/' || $path === '/vivant/api') {
    require '/app/vivant/api/index.php';
    return true;
}
if (str_contains($path, '..') || preg_match('~(?:^|/)\.|\.(?:php|sql|log|bak|txt|EXEMPLE)$~i', $path)) {
    http_response_code(404);
    return true;
}
return false;
