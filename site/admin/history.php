<?php
//  Tcontrol — historique des 7 derniers jours
$pageTitle = 'Historique';
$active = 'history';
require __DIR__ . '/header.php';
require __DIR__ . '/../api/db.php';
require __DIR__ . '/../api/common.php';

$resetHour = (int)cfg_get($pdo, 'reset_hour', '0');
$limit     = (int)cfg_get($pdo, 'daily_limit', '7200');
$today     = logical_day($resetHour);

// --- résumé par jour (7 jours) ---------------------------------------------
$days = [];
for ($i = 0; $i < 7; $i++) {
    $days[] = date('Y-m-d', strtotime($today . " -$i days"));
}

$in = implode(',', array_fill(0, count($days), '?'));
$st = $pdo->prepare(
    "SELECT s.day,
            COUNT(DISTINCT s.user_id) AS users,
            SUM(s.seconds)            AS total,
            SUM(s.blocked)            AS blocked_users
     FROM `usage` s
     WHERE s.day IN ($in)
     GROUP BY s.day"
);
$st->execute($days);
$summary = [];
foreach ($st->fetchAll() as $r) { $summary[$r['day']] = $r; }

// --- détail du jour sélectionné --------------------------------------------
$sel = (string)($_GET['day'] ?? $today);
if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $sel) || !in_array($sel, $days, true)) {
    $sel = $today;
}

$st = $pdo->prepare(
    'SELECT u.username, u.alias,
            SUM(s.seconds)   AS used,
            MAX(s.blocked)   AS blocked,
            MAX(s.last_seen) AS last_seen,
            GROUP_CONCAT(DISTINCT s.machine SEPARATOR ", ") AS machines
     FROM `usage` s
     JOIN users u ON u.id = s.user_id
     WHERE s.day = ?
     GROUP BY u.id
     ORDER BY used DESC'
);
$st->execute([$sel]);
$rows = $st->fetchAll();
?>

<h1>Historique — 7 derniers jours</h1>
<p class="muted">Au-delà de 7 jours, les données sont supprimées automatiquement.</p>

<div class="day-grid">
<?php foreach ($days as $i => $d):
    $s = $summary[$d] ?? null;
    $label = $i === 0 ? "Aujourd'hui" : ($i === 1 ? 'Hier' : date('D d/m', strtotime($d)));
?>
  <a class="day-card <?= $d === $sel ? 'sel' : '' ?>" href="?day=<?= e($d) ?>">
    <b><?= e($label) ?></b>
    <?php if ($s): ?>
      <span><?= (int)$s['users'] ?> util. — <?= e(fmt_hm((int)$s['total'])) ?></span>
      <span class="<?= (int)$s['blocked_users'] > 0 ? 'bad-txt' : 'ok-txt' ?>">
        <?= (int)$s['blocked_users'] ?> bloqué(s)
      </span>
    <?php else: ?>
      <span class="muted">aucune activité</span>
    <?php endif; ?>
  </a>
<?php endforeach; ?>
</div>

<h2 style="margin-top:28px">Détail du <?= e(date('d/m/Y', strtotime($sel))) ?></h2>

<?php if (!$rows): ?>
  <div class="card empty">Aucune connexion ce jour-là.</div>
<?php else: ?>
<div class="card">
<table>
  <thead>
    <tr><th>Utilisateur</th><th>Machine(s)</th><th>Temps</th>
        <th>Statut</th><th>Dernière activité</th></tr>
  </thead>
  <tbody>
  <?php foreach ($rows as $r): ?>
    <tr>
      <td><strong><?= e($r['alias'] ?: $r['username']) ?></strong></td>
      <td><?= e($r['machines']) ?></td>
      <td><strong><?= e(fmt_hm((int)$r['used'])) ?></strong></td>
      <td><?= $r['blocked'] ? '<span class="badge bad">🚫 bloqué</span>'
                            : '<span class="badge ok">autorisé</span>' ?></td>
      <td class="muted"><?= e($r['last_seen'] ? date('H:i', strtotime($r['last_seen'])) : '—') ?></td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>
</div>
<?php endif; ?>

<?php require __DIR__ . '/footer.php'; ?>
