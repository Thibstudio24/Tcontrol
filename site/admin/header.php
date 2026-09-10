<?php
// En-tête commun des pages admin. Définir $pageTitle avant l'inclusion.
require_once __DIR__ . '/auth.php';
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?= e($pageTitle ?? 'Tcontrol') ?> — Tcontrol</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<nav class="topnav">
  <div class="brand">⏱ Tcontrol <span class="muted">admin</span></div>
  <div class="links">
    <a href="index.php"    class="<?= ($active ?? '') === 'index'    ? 'on' : '' ?>">Aujourd'hui</a>
    <a href="history.php"  class="<?= ($active ?? '') === 'history'  ? 'on' : '' ?>">Historique (7 j)</a>
    <a href="users.php"    class="<?= ($active ?? '') === 'users'    ? 'on' : '' ?>">Utilisateurs</a>
    <a href="settings.php" class="<?= ($active ?? '') === 'settings' ? 'on' : '' ?>">Paramètres</a>
    <a href="logout.php" class="logout">Déconnexion (<?= e($_SESSION['admin']) ?>)</a>
  </div>
</nav>
<main class="content">
