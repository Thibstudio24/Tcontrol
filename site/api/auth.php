<?php
// ============================================================
//  Tcontrol — vérification des identifiants admin (depuis l'app)
//  POST JSON : {key, username, password} -> {ok:true}
// ============================================================

require __DIR__ . '/db.php';
require __DIR__ . '/common.php';

$body = read_body();
require_api_key($pdo, $body);

$user = trim((string)($body['username'] ?? ''));
$pass = (string)($body['password'] ?? '');

if ($user === '' || $pass === '' || !check_admin_credentials($pdo, $user, $pass)) {
    usleep(500000); // ralentit les tentatives par force brute
    json_error('Identifiants incorrects.', 401);
}

json_response(['ok' => true]);
