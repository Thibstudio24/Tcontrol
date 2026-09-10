<?php
//  Tcontrol — tableau de bord : activité du jour
$pageTitle = "Aujourd'hui";
$active = 'index';
require __DIR__ . '/header.php';
require __DIR__ . '/../api/db.php';
require __DIR__ . '/../api/common.php';

$resetHour = (int)cfg_get($pdo, 'reset_hour', '0');
$limit     = (int)cfg_get($pdo, 'daily_limit', '7200');
$today     = logical_day($resetHour);

$st = $pdo->prepare(
    'SELECT u.username, u.alias,
            SUM(s.seconds)   AS used,
            MAX(s.blocked)   AS blocked,
            MAX(s.last_seen) AS last_seen,
            GROUP_CONCAT(DISTINCT s.machine SEPARATOR ", ") AS machines,
            COUNT(DISTINCT s.machine) AS nb_machines
     FROM `usage` s
     JOIN users u ON u.id = s.user_id
     WHERE s.day = ?
     GROUP BY u.id
     ORDER BY used DESC'
);
$st->execute([$today]);
$rows = $st->fetchAll();

$nbBlocked = count(array_filter($rows, fn($r) => (bool)$r['blocked']));
cleanup_old($pdo);
?>

<div class="page-head">
  <div>
    <h1>Journée du <?= e(date('d/m/Y', strtotime($today))) ?></h1>
    <p class="muted">Limite : <strong><?= e(fmt_hm($limit)) ?></strong> ·
       reset à <?= str_pad((string)$resetHour, 2, '0', STR_PAD_LEFT) ?>h00 ·
       rafraîchissement auto 60 s</p>
  </div>
  <button class="btn" onclick="location.reload()">🔄 Rafraîchir</button>
</div>

<div class="stats">
  <div class="stat"><b><?= count($rows) ?></b><span>utilisateur(s) connecté(s)</span></div>
  <div class="stat"><b><?= $nbBlocked ?></b><span>bloqué(s)</span></div>
  <div class="stat"><b><?= e(fmt_hm(array_sum(array_map(fn($r) => (int)$r['used'], $rows)))) ?></b><span>temps cumulé</span></div>
</div>

<?php if (!$rows): ?>
  <div class="card empty">Personne ne s'est encore connecté aujourd'hui. 🎮</div>
<?php else: ?>
<div class="card">
<table>
  <thead>
    <tr>
      <th>Utilisateur</th>
      <th>Machine(s)</th>
      <th>Temps de jeu</th>
      <th>Progression</th>
      <th>Statut</th>
      <th>Dernière activité</th>
    </tr>
  </thead>
  <tbody>
  <?php foreach ($rows as $r):
      $used = (int)$r['used'];
      $blockedU = (bool)$r['blocked'];
      $pct = $limit > 0 ? min(100, round($used / $limit * 100)) : 0;
      $online = $r['last_seen']
          && (time() - strtotime($r['last_seen']) < 180);
  ?>
    <tr>
      <td><strong><?= e($r['alias'] ?: $r['username']) ?></strong>
        <?php if ($r['alias']): ?><br><span class="muted small"><?= e($r['username']) ?></span><?php endif; ?>
      </td>
      <td><?= e($r['machines']) ?>
        <?php if ((int)$r['nb_machines'] > 1): ?><span class="tag">multi-PC</span><?php endif; ?>
      </td>
      <td><strong><?= e(fmt_hm($used)) ?></strong></td>
      <td class="bar-cell">
        <div class="bar"><span style="width:<?= $pct ?>%"
          class="<?= $blockedU ? 'full' : ($pct > 75 ? 'warn' : '') ?>"></span></div>
        <span class="muted small"><?= $pct ?> %</span>
      </td>
      <td>
        <?php if ($blockedU): ?>
          <span class="badge bad">🚫 bloqué</span>
        <?php else: ?>
          <span class="badge ok">autorisé</span>
        <?php endif; ?>
        <?= $online ? '<span class="dot on" title="en ligne"></span>'
                    : '<span class="dot off" title="hors ligne"></span>' ?>
      </td>
      <td class="muted"><?= e($r['last_seen'] ? date('H:i:s', strtotime($r['last_seen'])) : '—') ?></td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>
</div>
<?php endif; ?>

<script>setTimeout(() => location.reload(), 60000);</script>
<?php require __DIR__ . '/footer.php'; ?>
