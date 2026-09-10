<?php
// ============================================================
//  Tcontrol — API d'administration pour l'app Windows
//  Chaque requête doit contenir : key (clé API) + username + password
//  Actions : state | add_process | remove_process
// ============================================================

require __DIR__ . '/db.php';
require __DIR__ . '/common.php';

$body = read_body();
require_api_key($pdo, $body);

$user = trim((string)($body['username'] ?? ''));
$pass = (string)($body['password'] ?? '');
if ($user === '' || $pass === '' || !check_admin_credentials($pdo, $user, $pass)) {
    usleep(500000);
    json_error('Identifiants admin incorrects.', 401);
}

$action = (string)($body['action'] ?? '');

$list_processes = function () use ($pdo): array {
    return array_values($pdo->query(
        'SELECT process_name FROM blocked_processes ORDER BY process_name'
    )->fetchAll(PDO::FETCH_COLUMN));
};

switch ($action) {

    case 'state':
        $resetHour = (int)cfg_get($pdo, 'reset_hour', '0');
        $limit     = (int)cfg_get($pdo, 'daily_limit', '7200');
        $today     = logical_day($resetHour);
        $st = $pdo->prepare(
            'SELECT u.username, u.alias,
                    SUM(s.seconds)              AS used,
                    MAX(s.blocked)              AS blocked,
                    MAX(s.last_seen)            AS last_seen,
                    GROUP_CONCAT(DISTINCT s.machine SEPARATOR ", ") AS machines
             FROM `usage` s
             JOIN users u ON u.id = s.user_id
             WHERE s.day = ?
             GROUP BY u.id
             ORDER BY used DESC'
        );
        $st->execute([$today]);
        json_response([
            'ok'         => true,
            'day'        => $today,
            'limit'      => $limit,
            'reset_hour' => $resetHour,
            'usage'      => array_map(function ($r) {
                $r['used']    = (int)$r['used'];
                $r['blocked'] = (bool)$r['blocked'];
                return $r;
            }, $st->fetchAll()),
            'processes'  => $list_processes(),
        ]);
        break;

    case 'add_process':
        $name = strtolower(trim((string)($body['name'] ?? '')));
        if (!preg_match('/^[a-z0-9][a-z0-9_.\- ()]{0,63}$/', $name)) {
            json_error('Nom de processus invalide.');
        }
        $pdo->prepare('INSERT IGNORE INTO blocked_processes (process_name)
                       VALUES (?)')->execute([$name]);
        json_response(['ok' => true, 'processes' => $list_processes()]);
        break;

    case 'remove_process':
        $name = strtolower(trim((string)($body['name'] ?? '')));
        $pdo->prepare('DELETE FROM blocked_processes WHERE process_name = ?')
            ->execute([$name]);
        json_response(['ok' => true, 'processes' => $list_processes()]);
        break;

    default:
        json_error('Action inconnue.');
}
