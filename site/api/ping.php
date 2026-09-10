<?php
// ============================================================
//  Tcontrol — endpoint de synchronisation (appelé toutes les 60 s)
//  POST JSON : {key, user, machine, delta, day, running[], blocked}
//  Réponse  : {ok, day, limit, used, remaining, blocked, reset_hour,
//              alias, processes[]}
// ============================================================

require __DIR__ . '/db.php';
require __DIR__ . '/common.php';

$body = read_body();
require_api_key($pdo, $body);

$user    = sanitize_name((string)($body['user'] ?? ''));
$machine = sanitize_name((string)($body['machine'] ?? 'PC'));
$delta   = max(0, min((int)($body['delta'] ?? 0), 900)); // anti-abus : <= 15 min / ping

$resetHour = (int)cfg_get($pdo, 'reset_hour', '0');
$limit     = (int)cfg_get($pdo, 'daily_limit', '7200');
$today     = logical_day($resetHour);

// Jour auquel attribuer le delta : celui du client s'il est récent, sinon aujourd'hui
$dayForDelta = $today;
if (!empty($body['day']) && is_string($body['day'])
        && preg_match('/^\d{4}-\d{2}-\d{2}$/', $body['day'])) {
    $min = (new DateTimeImmutable('now'))->modify('-9 days')->format('Y-m-d');
    if ($body['day'] >= $min && $body['day'] <= $today) {
        $dayForDelta = $body['day'];
    }
}

// --- utilisateur (création auto au premier ping) ---------------------------
$pdo->prepare('INSERT INTO users (username) VALUES (?)
               ON DUPLICATE KEY UPDATE username = username')->execute([$user]);
$st = $pdo->prepare('SELECT id, alias FROM users WHERE username = ?');
$st->execute([$user]);
$row = $st->fetch();
$uid   = (int)$row['id'];
$alias = (string)($row['alias'] ?? '');

// --- enregistrement du temps + présence (même à delta = 0) -----------------
$pdo->prepare('INSERT INTO `usage` (user_id, day, machine, seconds, last_seen)
               VALUES (?, ?, ?, ?, NOW())
               ON DUPLICATE KEY UPDATE
                   seconds = seconds + VALUES(seconds),
                   last_seen = NOW()')
    ->execute([$uid, $dayForDelta, $machine, $delta]);

// --- total du jour (toutes machines confondues) -----------------------------
$st = $pdo->prepare('SELECT COALESCE(SUM(seconds),0) FROM `usage`
                     WHERE user_id = ? AND day = ?');
$st->execute([$uid, $today]);
$used = (int)$st->fetchColumn();

$blocked = $limit > 0 && $used >= $limit;
if ($blocked) {
    $pdo->prepare('UPDATE `usage` SET blocked = 1 WHERE user_id = ? AND day = ?')
        ->execute([$uid, $today]);
}

cleanup_old($pdo); // rétention 7 jours

$procs = $pdo->query('SELECT process_name FROM blocked_processes
                      ORDER BY process_name')->fetchAll(PDO::FETCH_COLUMN);

json_response([
    'ok'          => true,
    'day'         => $today,
    'limit'       => $limit,
    'used'        => $used,
    'remaining'   => max(0, $limit - $used),
    'blocked'     => $blocked,
    'reset_hour'  => $resetHour,
    'alias'       => $alias,
    'processes'   => array_values($procs),
    'server_time' => date('c'),
]);
