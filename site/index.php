<?php
// Page d'accueil publique de Tcontrol.
$installed = file_exists(__DIR__ . '/api/config_db.php');
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tcontrol — Contrôle du temps de jeu</title>
<style>
  *{box-sizing:border-box}
  body{margin:0;font-family:system-ui,'Segoe UI',sans-serif;background:#0b0f14;
       color:#e5e7eb;display:flex;flex-direction:column;align-items:center;
       min-height:100vh;padding:60px 20px}
  .logo{width:96px;height:96px;border-radius:24px;background:#0e7490;
        display:flex;align-items:center;justify-content:center;font-size:48px;
        box-shadow:0 10px 40px rgba(34,211,238,.25)}
  h1{font-size:34px;margin:24px 0 8px}
  p{color:#9ca3af;max-width:520px;text-align:center;line-height:1.6}
  .btn{display:inline-block;margin-top:24px;background:#0e7490;color:#fff;
       padding:12px 28px;border-radius:10px;text-decoration:none;font-weight:600}
  .btn:hover{background:#155e75}
  .features{display:flex;gap:14px;margin-top:40px;flex-wrap:wrap;
            justify-content:center;max-width:820px}
  .f{background:#151b24;border:1px solid #293241;border-radius:12px;
     padding:18px;width:240px}
  .f b{display:block;margin-bottom:6px}
  .f span{font-size:13px;color:#9ca3af;line-height:1.5}
  footer{margin-top:60px;color:#4b5563;font-size:12px}
</style>
</head>
<body>
  <div class="logo">⏱</div>
  <h1>Tcontrol</h1>
  <p>Contrôle du temps de jeu multi-PC. Une seule limite quotidienne, synchronisée
     sur tous les ordinateurs de la maison. Quand le temps est écoulé, les jeux
     sélectionnés se ferment et ne peuvent plus être relancés jusqu'au lendemain.</p>

  <?php if ($installed): ?>
    <a class="btn" href="admin/login.php">🔑 Espace administrateur</a>
  <?php else: ?>
    <a class="btn" href="install.php">🚀 Lancer l'installation</a>
  <?php endif; ?>

  <div class="features">
    <div class="f"><b>🖥 Multi-PC</b><span>Le temps de jeu se synchronise entre
      tous les ordinateurs : impossible de tricher en changeant de PC.</span></div>
    <div class="f"><b>🔔 Notifications</b><span>L'utilisateur est prévenu à
      10 minutes, 5 minutes, puis à la fin du temps de jeu.</span></div>
    <div class="f"><b>🚫 Blocage réel</b><span>Les jeux surveillés se ferment
      automatiquement et toute relance est bloquée jusqu'au reset quotidien.</span></div>
  </div>

  <footer>Tcontrol — projet open source.</footer>
</body>
</html>
