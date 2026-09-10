<?php
// ============================================================
//  Tcontrol — fonctions communes API + admin
// ============================================================
declare(strict_types=1);

function json_response(array $data, int $code = 200): void {
    http_response_code($code);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function json_error(string $msg, int $code = 400): void {
    json_response(['ok' => false, 'error' => $msg], $code);
}

function read_body(): array {
    $raw = file_get_contents('php://input');
    $data = json_decode($raw ?: '', true);
    return is_array($data) ? $data : [];
}

// ---------------------------------------------------------------- config
function cfg_get(PDO $pdo, string $key, string $default = ''): string {
    $st = $pdo->prepare('SELECT v FROM config WHERE k = ?');
    $st->execute([$key]);
    $v = $st->fetchColumn();
    return $v === false ? $default : (string)$v;
}

function cfg_set(PDO $pdo, string $key, string $value): void {
    $st = $pdo->prepare('INSERT INTO config (k, v) VALUES (?, ?)
                         ON DUPLICATE KEY UPDATE v = VALUES(v)');
    $st->execute([$key, $value]);
}

function require_api_key(PDO $pdo, array $body): void {
    $key = $body['key'] ?? '';
    $expected = cfg_get($pdo, 'api_key', '');
    if (!is_string($key) || $expected === '' || !hash_equals($expected, $key)) {
        json_error('Clé API invalide.', 403);
    }
}

// ---------------------------------------------------------------- métier
/** Jour logique : avant l'heure de reset, on est encore sur la veille. */
function logical_day(int $resetHour): string {
    $now = new DateTimeImmutable('now');
    if ((int)$now->format('G') < $resetHour) {
        $now = $now->modify('-1 day');
    }
    return $now->format('Y-m-d');
}

function sanitize_name(string $s, int $max = 128): string {
    $s = trim((string)preg_replace('/[^\p{L}\p{N}_.\-\\\\ ()]/iu', '', $s));
    if ($s === '') { $s = 'inconnu'; }
    return mb_substr($s, 0, $max);
}

/** Nettoyage automatique : conserve 7 jours d'historique (1 chance / 10 par appel). */
function cleanup_old(PDO $pdo): void {
    if (random_int(1, 10) === 1) {
        $pdo->exec('DELETE FROM `usage` WHERE day < CURDATE() - INTERVAL 7 DAY');
    }
}

function fmt_hm(int $seconds): string {
    $seconds = max(0, $seconds);
    $h = intdiv($seconds, 3600);
    $m = intdiv($seconds % 3600, 60);
    if ($h > 0) { return $h . ' h ' . str_pad((string)$m, 2, '0', STR_PAD_LEFT); }
    if ($m > 0) { return $m . ' min'; }
    return $seconds . ' s';
}

// ---------------------------------------------------------------- sécurité web
function check_admin_credentials(PDO $pdo, string $user, string $pass): bool {
    $st = $pdo->prepare('SELECT pass_hash FROM admins WHERE username = ?');
    $st->execute([$user]);
    $hash = $st->fetchColumn();
    return is_string($hash) && password_verify($pass, $hash);
}
