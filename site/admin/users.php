<?php
//  Tcontrol — gestion des utilisateurs (alias, suppression)
$pageTitle = 'Utilisateurs';
$active = 'users';
require __DIR__ . '/header.php';
require __DIR__ . '/../api/db.php';
require __DIR__ . '/../api/common.php';

$msg = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    check_csrf();
    $act = (string)($_POST['act'] ?? '');

    if ($act === 'alias') {
        $uid   = (int)($_POST['uid'] ?? 0);
        $alias = trim((string)($_POST['alias'] ?? ''));
        $st = $pdo->prepare('UPDATE users SET alias = ? WHERE id = ?');
        $st->execute([$alias === '' ? null : mb_substr($alias, 0, 64), $uid]);
        $msg = $alias === '' ? 'Alias supprimé.' : 'Alias enregistré.';
    } elseif ($act === 'delete') {
        $uid = (int)($_POST['uid'] ?? 0);
        $pdo->prepare('DELETE FROM users WHERE id = ?')->execute([$uid]);
        $msg = 'Utilisateur supprimé (avec tout son historique).';
    }
}

$resetHour = (int)cfg_get($pdo, 'reset_hour', '0');
$today = logical_day($resetHour);

$rows = $pdo->query(
    'SELECT u.id, u.username, u.alias, u.created_at,
            (SELECT COALESCE(SUM(seconds),0) FROM `usage` s
              WHERE s.user_id = u.id AND s.day = ' . $pdo->quote($today) . ') AS today,
            (SELECT COALESCE(SUM(seconds),0) FROM `usage` s
              WHERE s.user_id = u.id) AS total,
            (SELECT MAX(last_seen) FROM `usage` s
              WHERE s.user_id = u.id) AS last_seen
     FROM users u
     ORDER BY u.created_at DESC'
)->fetchAll();
?>

<h1>Utilisateurs</h1>
<p class="muted">Un utilisateur est créé automatiquement au premier ping depuis un PC
   (identifié par son nom de session Windows). L'alias remplace le nom affiché partout.</p>

<?php if ($msg !== ''): ?><div class="notice">✅ <?= e($msg) ?></div><?php endif; ?>

<?php if (!$rows): ?>
  <div class="card empty">Aucun utilisateur pour l'instant.</div>
<?php else: ?>
<div class="card">
<table>
  <thead>
    <tr><th>Nom Windows</th><th>Alias</th><th>Aujourd'hui</th>
        <th>Total (7 j)</th><th>Dernière activité</th><th></th></tr>
  </thead>
  <tbody>
  <?php foreach ($rows as $r): ?>
    <tr>
      <td><strong><?= e($r['username']) ?></strong><br>
          <span class="muted small">depuis le <?= e(date('d/m/Y', strtotime($r['created_at']))) ?></span></td>
      <td>
        <form method="post" class="inline">
          <?= csrf_field() ?>
          <input type="hidden" name="act" value="alias">
          <input type="hidden" name="uid" value="<?= (int)$r['id'] ?>">
          <input name="alias" value="<?= e((string)$r['alias']) ?>"
                 placeholder="ex : Lucas" maxlength="64" class="input-sm">
          <button class="btn sm" type="submit">💾</button>
        </form>
      </td>
      <td><?= e(fmt_hm((int)$r['today'])) ?></td>
      <td><?= e(fmt_hm((int)$r['total'])) ?></td>
      <td class="muted"><?= e($r['last_seen'] ?? 'jamais') ?></td>
      <td>
        <form method="post" class="inline"
              onsubmit="return confirm('Supprimer <?= e($r['username']) ?> et tout son historique ?')">
          <?= csrf_field() ?>
          <input type="hidden" name="act" value="delete">
          <input type="hidden" name="uid" value="<?= (int)$r['id'] ?>">
          <button class="btn sm danger" type="submit">🗑</button>
        </form>
      </td>
    </tr>
  <?php endforeach; ?>
  </tbody>
</table>
</div>
<?php endif; ?>

<?php require __DIR__ . '/footer.php'; ?>
