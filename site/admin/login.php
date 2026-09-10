<?php
//  Tcontrol — connexion à l'interface d'administration
session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax']);
session_start();

$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    require __DIR__ . '/../api/db.php';
    require __DIR__ . '/../api/common.php';

    $user = trim((string)($_POST['username'] ?? ''));
    $pass = (string)($_POST['password'] ?? '');

    if ($user !== '' && $pass !== ''
            && check_admin_credentials($pdo, $user, $pass)) {
        session_regenerate_id(true);
        $_SESSION['admin'] = $user;
        header('Location: index.php');
        exit;
    }
    sleep(1); // ralentit la force brute
    $error = 'Identifiants incorrects.';
}

function e(string $s): string { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tcontrol — Connexion admin</title>
<link rel="stylesheet" href="style.css">
</head>
<body class="login-page">
<div class="login-card">
  <div class="login-logo">⏱</div>
  <h1>Tcontrol</h1>
  <p class="muted">Espace administrateur</p>

  <?php if ($error !== ''): ?>
    <div class="alert"><?= e($error) ?></div>
  <?php endif; ?>

  <form method="post">
    <label>Identifiant</label>
    <input name="username" required autocomplete="username">
    <label>Mot de passe</label>
    <input name="password" type="password" required autocomplete="current-password">
    <button type="submit">Se connecter</button>
  </form>
  <p class="muted small" style="margin-top:18px">
    <a href="../index.php">← retour à l'accueil</a>
  </p>
</div>
</body>
</html>
