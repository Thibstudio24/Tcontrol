<?php
//  Tcontrol — paramètres : limite, reset, clé API, jeux bloqués, mot de passe
$pageTitle = 'Paramètres';
$active = 'settings';
require __DIR__ . '/header.php';
require __DIR__ . '/../api/db.php';
require __DIR__ . '/../api/common.php';

$msg = '';
$err = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    check_csrf();
    $act = (string)($_POST['act'] ?? '');

    if ($act === 'limit') {
        $h = max(0, min(12, (int)($_POST['hours'] ?? 0)));
        $m = max(0, min(59, (int)($_POST['minutes'] ?? 0)));
        cfg_set($pdo, 'daily_limit', (string)($h * 3600 + $m * 60));
        $msg = "Limite enregistrée — appliquée sur les PC dans la minute (prochain ping).";
    } elseif ($act === 'reset') {
        $rh = max(0, min(23, (int)($_POST['reset_hour'] ?? 0)));
        cfg_set($pdo, 'reset_hour', (string)$rh);
        $msg = "Heure de reset enregistrée — appliquée sur les PC au prochain ping.";
    } elseif ($act === 'regen_key') {
        cfg_set($pdo, 'api_key', bin2hex(random_bytes(24)));
        $msg = "Nouvelle clé API générée. Pensez à mettre à jour l'app sur chaque PC
                (🔑 Admin → Configuration).";
    } elseif ($act === 'add_proc') {
        $name = strtolower(trim((string)($_POST['name'] ?? '')));
        if (preg_match('/^[a-z0-9][a-z0-9_.\- ()]{0,63}$/', $name)) {
            $pdo->prepare('INSERT IGNORE INTO blocked_processes (process_name)
                           VALUES (?)')->execute([$name]);
            $msg = "« $name » ajouté à la liste des jeux bloqués.";
        } else {
            $err = "Nom de processus invalide (ex : fortnite.exe).";
        }
    } elseif ($act === 'del_proc') {
        $name = strtolower(trim((string)($_POST['name'] ?? '')));
        $pdo->prepare('DELETE FROM blocked_processes WHERE process_name = ?')
            ->execute([$name]);
        $msg = "« $name » retiré de la liste.";
    } elseif ($act === 'passwd') {
        $cur  = (string)($_POST['current'] ?? '');
        $new  = (string)($_POST['new'] ?? '');
        $conf = (string)($_POST['confirm'] ?? '');
        if (!check_admin_credentials($pdo, $_SESSION['admin'], $cur)) {
            $err = 'Mot de passe actuel incorrect.';
        } elseif (strlen($new) < 6) {
            $err = 'Le nouveau mot de passe doit faire au moins 6 caractères.';
        } elseif ($new !== $conf) {
            $err = 'La confirmation ne correspond pas.';
        } else {
            $pdo->prepare('UPDATE admins SET pass_hash = ? WHERE username = ?')
                ->execute([password_hash($new, PASSWORD_DEFAULT), $_SESSION['admin']]);
            $msg = "Mot de passe modifié — c'est aussi celui de l'app (bouton 🔑).";
        }
    }
}

$limit     = (int)cfg_get($pdo, 'daily_limit', '7200');
$resetHour = (int)cfg_get($pdo, 'reset_hour', '0');
$apiKey    = cfg_get($pdo, 'api_key', '');
$procs     = $pdo->query('SELECT process_name FROM blocked_processes
                          ORDER BY process_name')->fetchAll(PDO::FETCH_COLUMN);

$base = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off' ? 'https' : 'http')
      . '://' . ($_SERVER['HTTP_HOST'] ?? 'votre-site')
      . rtrim(dirname(dirname($_SERVER['SCRIPT_NAME'] ?? '/admin/index.php')), '/');
?>

<h1>Paramètres</h1>

<?php if ($msg !== ''): ?><div class="notice">✅ <?= e($msg) ?></div><?php endif; ?>
<?php if ($err !== ''): ?><div class="alert">⚠ <?= e($err) ?></div><?php endif; ?>

<div class="grid-2">

  <div class="card">
    <h2>⏳ Limite quotidienne</h2>
    <p class="muted small">Identique pour tous les utilisateurs. Le chrono tourne
       uniquement quand un jeu surveillé est lancé.</p>
    <form method="post" class="hform">
      <?= csrf_field() ?>
      <input type="hidden" name="act" value="limit">
      <input type="number" name="hours" min="0" max="12"
             value="<?= intdiv($limit, 3600) ?>" class="input-sm"> <span>h</span>
      <input type="number" name="minutes" min="0" max="59"
             value="<?= intdiv($limit % 3600, 60) ?>" class="input-sm"> <span>min</span>
      <button class="btn" type="submit">Enregistrer</button>
    </form>

    <h2 style="margin-top:22px">🌙 Heure de reset</h2>
    <p class="muted small">Le compteur repart à zéro à cette heure chaque jour.</p>
    <form method="post" class="hform">
      <?= csrf_field() ?>
      <input type="hidden" name="act" value="reset">
      <select name="reset_hour" class="input-sm">
        <?php for ($i = 0; $i < 24; $i++): ?>
          <option value="<?= $i ?>" <?= $i === $resetHour ? 'selected' : '' ?>>
            <?= str_pad((string)$i, 2, '0', STR_PAD_LEFT) ?>h00
          </option>
        <?php endfor; ?>
      </select>
      <button class="btn" type="submit">Enregistrer</button>
    </form>
  </div>

  <div class="card">
    <h2>🔐 Clé API (pour les PC)</h2>
    <p class="muted small">À copier dans l'app : 🔑 Admin → Configuration.
       Dans l'app, indiquez l'URL :</p>
    <code class="code"><?= e($base) ?>/api</code>
    <p class="muted small" style="margin-top:14px">Clé API actuelle :</p>
    <code class="code key"><?= e($apiKey) ?></code>
    <form method="post" style="margin-top:12px"
          onsubmit="return confirm('Régénérer la clé ? Les PC devront être reconfigurés.')">
      <?= csrf_field() ?>
      <input type="hidden" name="act" value="regen_key">
      <button class="btn warn-btn" type="submit">♻ Régénérer la clé</button>
    </form>
  </div>

  <div class="card">
    <h2>🎮 Jeux bloqués (<?= count($procs) ?>)</h2>
    <p class="muted small">Noms des processus surveillés (communs à tous les PC).
       Ajout possible aussi depuis l'app (🔑 Admin → Jeux bloqués).</p>
    <form method="post" class="hform">
      <?= csrf_field() ?>
      <input type="hidden" name="act" value="add_proc">
      <input name="name" placeholder="ex : fortnite.exe" class="input" required>
      <button class="btn" type="submit">Ajouter</button>
    </form>
    <ul class="proc-list">
      <?php foreach ($procs as $p): ?>
        <li>
          <code><?= e($p) ?></code>
          <form method="post" class="inline">
            <?= csrf_field() ?>
            <input type="hidden" name="act" value="del_proc">
            <input type="hidden" name="name" value="<?= e($p) ?>">
            <button class="btn sm danger" type="submit">✖</button>
          </form>
        </li>
      <?php endforeach; ?>
      <?php if (!$procs): ?><li class="muted">aucun pour l'instant</li><?php endif; ?>
    </ul>
  </div>

  <div class="card">
    <h2>🔑 Mot de passe administrateur</h2>
    <p class="muted small">Valable pour le site ET pour l'app (bouton 🔑 → Quitter).</p>
    <form method="post">
      <?= csrf_field() ?>
      <input type="hidden" name="act" value="passwd">
      <label>Mot de passe actuel</label>
      <input name="current" type="password" class="input" required>
      <label>Nouveau mot de passe (min 6 caractères)</label>
      <input name="new" type="password" class="input" required minlength="6">
      <label>Confirmation</label>
      <input name="confirm" type="password" class="input" required minlength="6">
      <button class="btn" type="submit" style="margin-top:12px">Modifier</button>
    </form>
  </div>

</div>

<?php require __DIR__ . '/footer.php'; ?>
