<?php
// ============================================================
//  Tcontrol — installateur web (à lancer UNE SEULE FOIS)
//  1. Remplissez les champs ci-dessous dans votre navigateur
//  2. Cliquez sur "Installer"
//  3. SUPPRIMEZ ce fichier (install.php) ensuite !
// ============================================================

$errors  = [];
$done    = false;
$manual  = '';   // contenu de config_db.php à copier à la main si l'écriture échoue

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $dbHost = trim((string)($_POST['db_host'] ?? ''));
    $dbName = trim((string)($_POST['db_name'] ?? ''));
    $dbUser = trim((string)($_POST['db_user'] ?? ''));
    $dbPass = trim((string)($_POST['db_pass'] ?? ''));
    $admUser = trim((string)($_POST['admin_user'] ?? 'admin'));
    $admPass = (string)($_POST['admin_pass'] ?? '');

    if ($dbHost === '' || $dbName === '' || $dbUser === '') {
        $errors[] = 'Remplissez tous les champs de la base de données.';
    }
    if (strlen($admUser) < 3 || strlen($admPass) < 6) {
        $errors[] = 'Identifiant admin >= 3 caractères, mot de passe >= 6 caractères.';
    }

    if (!$errors) {
        try {
            $pdo = new PDO(
                "mysql:host=$dbHost;dbname=$dbName;charset=utf8mb4",
                $dbUser, $dbPass,
                [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
            );
        } catch (PDOException $e) {
            $errors[] = 'Connexion MySQL impossible : vérifiez hôte / base / identifiants.';
        }
    }

    if (!$errors) {
        try {
            $pdo->exec("CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(64) UNIQUE NOT NULL,
                pass_hash VARCHAR(255) NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

            $pdo->exec("CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(128) UNIQUE NOT NULL,
                alias VARCHAR(128) NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

            $pdo->exec("CREATE TABLE IF NOT EXISTS `usage` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                day DATE NOT NULL,
                machine VARCHAR(128) NOT NULL,
                seconds INT NOT NULL DEFAULT 0,
                blocked TINYINT(1) NOT NULL DEFAULT 0,
                last_seen DATETIME NULL,
                UNIQUE KEY uq_user_day_machine (user_id, day, machine),
                KEY idx_day (day),
                CONSTRAINT fk_usage_user FOREIGN KEY (user_id)
                    REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

            $pdo->exec("CREATE TABLE IF NOT EXISTS config (
                k VARCHAR(64) PRIMARY KEY,
                v TEXT
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

            $pdo->exec("CREATE TABLE IF NOT EXISTS blocked_processes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                process_name VARCHAR(128) UNIQUE NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

            // config par défaut (sans écraser une install existante)
            $seed = $pdo->prepare('INSERT IGNORE INTO config (k, v) VALUES (?, ?)');
            $seed->execute(['daily_limit', '7200']);
            $seed->execute(['reset_hour', '0']);
            $seed->execute(['api_key', bin2hex(random_bytes(24))]);

            // compte administrateur
            $st = $pdo->prepare('SELECT COUNT(*) FROM admins WHERE username = ?');
            $st->execute([$admUser]);
            $hash = password_hash($admPass, PASSWORD_DEFAULT);
            if ((int)$st->fetchColumn() === 0) {
                $pdo->prepare('INSERT INTO admins (username, pass_hash) VALUES (?, ?)')
                    ->execute([$admUser, $hash]);
            } else {
                $pdo->prepare('UPDATE admins SET pass_hash = ? WHERE username = ?')
                    ->execute([$hash, $admUser]);
            }
        } catch (PDOException $e) {
            $errors[] = 'Erreur lors de la création des tables : '
                      . htmlspecialchars($e->getMessage(), ENT_QUOTES);
        }
    }

    if (!$errors) {
        $content = "<?php\n"
            . "// Tcontrol — identifiants base de données (généré par install.php)\n"
            . "define('DB_HOST', " . var_export($dbHost, true) . ");\n"
            . "define('DB_NAME', " . var_export($dbName, true) . ");\n"
            . "define('DB_USER', " . var_export($dbUser, true) . ");\n"
            . "define('DB_PASS', " . var_export($dbPass, true) . ");\n"
            . "define('DB_CHARSET', 'utf8mb4');\n";

        $target = __DIR__ . '/api/config_db.php';
        if (@file_put_contents($target, $content) === false) {
            $manual = $content;
        }
        $done = true;
    }
}
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tcontrol — Installation</title>
<style>
  body{font-family:system-ui,'Segoe UI',sans-serif;background:#0b0f14;color:#e5e7eb;
       display:flex;justify-content:center;padding:40px 16px}
  .card{background:#151b24;border:1px solid #293241;border-radius:14px;
        padding:28px;max-width:520px;width:100%}
  h1{margin-top:0;font-size:22px}
  label{display:block;font-size:13px;color:#9ca3af;margin:12px 0 4px}
  input{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;
        border:1px solid #374151;background:#0b0f14;color:#e5e7eb;font-size:14px}
  button{margin-top:20px;width:100%;padding:12px;border:0;border-radius:8px;
         background:#0e7490;color:#fff;font-size:15px;font-weight:600;cursor:pointer}
  button:hover{background:#155e75}
  .err{background:#7f1d1d;border-radius:8px;padding:10px 14px;margin:10px 0;font-size:14px}
  .ok{background:#14532d;border-radius:8px;padding:14px;margin:10px 0}
  .warn{background:#7a5b13;border-radius:8px;padding:12px;margin-top:12px;font-size:13px}
  pre{background:#0b0f14;border:1px solid #374151;padding:12px;border-radius:8px;
      overflow:auto;font-size:12px}
  .hint{font-size:12px;color:#6b7280}
</style>
</head>
<body>
<div class="card">
  <h1>⏱ Tcontrol — Installation</h1>

  <?php if ($done): ?>
    <div class="ok">
      <strong>✅ Installation réussie !</strong><br><br>
      • Interface admin : <a href="admin/login.php" style="color:#4ade80">admin/login.php</a><br>
      • Votre <strong>clé API</strong> est visible dans Paramètres (à copier dans l'app Windows).
    </div>
    <?php if ($manual !== ''): ?>
      <div class="warn">
        ⚠ Écriture impossible de <code>api/config_db.php</code>.
        Créez ce fichier à la main avec ce contenu :
        <pre><?= htmlspecialchars($manual, ENT_QUOTES) ?></pre>
      </div>
    <?php endif; ?>
    <div class="warn">
      🔥 <strong>Important : supprimez maintenant le fichier <code>install.php</code></strong>
      (via le gestionnaire de fichiers d'InfinityFree).
    </div>
  <?php else: ?>
    <p class="hint">Récupérez les identifiants MySQL dans le panneau InfinityFree :
      <em>Control Panel → MySQL Databases</em>.</p>

    <?php foreach ($errors as $e): ?>
      <div class="err">⚠ <?= htmlspecialchars($e, ENT_QUOTES) ?></div>
    <?php endforeach; ?>

    <form method="post">
      <label>Hôte MySQL</label>
      <input name="db_host" required placeholder="sqlXXX.byetcluster.com"
             value="<?= htmlspecialchars($_POST['db_host'] ?? '', ENT_QUOTES) ?>">
      <label>Nom de la base</label>
      <input name="db_name" required placeholder="epiz_XXXXXXXX_tcontrol"
             value="<?= htmlspecialchars($_POST['db_name'] ?? '', ENT_QUOTES) ?>">
      <label>Utilisateur MySQL</label>
      <input name="db_user" required placeholder="epiz_XXXXXXXX"
             value="<?= htmlspecialchars($_POST['db_user'] ?? '', ENT_QUOTES) ?>">
      <label>Mot de passe MySQL</label>
      <input name="db_pass" type="password"
             value="<?= htmlspecialchars($_POST['db_pass'] ?? '', ENT_QUOTES) ?>">

      <label>Identifiant administrateur (site + app)</label>
      <input name="admin_user" required minlength="3" placeholder="admin"
             value="<?= htmlspecialchars($_POST['admin_user'] ?? '', ENT_QUOTES) ?>">
      <label>Mot de passe administrateur (min 6 caractères)</label>
      <input name="admin_pass" type="password" required minlength="6">

      <button type="submit">Installer</button>
    </form>
  <?php endif; ?>
</div>
</body>
</html>
