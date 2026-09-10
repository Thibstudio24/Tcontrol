<?php
// ============================================================
//  Tcontrol — connexion PDO à la base MySQL
//  Inclus par api/*.php et admin/*.php
// ============================================================

$cfgFile = __DIR__ . '/config_db.php';
if (!file_exists($cfgFile)) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => false, 'error' => "Site non installé : ouvrez /install.php dans votre navigateur."]);
    exit;
}
require $cfgFile; // définit DB_HOST, DB_NAME, DB_USER, DB_PASS, DB_CHARSET

$dsn = 'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME
     . ';charset=' . (defined('DB_CHARSET') ? DB_CHARSET : 'utf8mb4');

try {
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES   => false,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => false, 'error' => 'Base de données injoignable. Vérifiez api/config_db.php']);
    exit;
}
