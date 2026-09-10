<?php
// ============================================================
//  Tcontrol — garde de session + jetons CSRF (pages admin)
// ============================================================

session_set_cookie_params([
    'httponly' => true,
    'samesite' => 'Lax',
]);
session_start();

if (empty($_SESSION['admin'])) {
    header('Location: login.php');
    exit;
}

function csrf_token(): string {
    if (empty($_SESSION['csrf'])) {
        $_SESSION['csrf'] = bin2hex(random_bytes(16));
    }
    return $_SESSION['csrf'];
}

function csrf_field(): string {
    return '<input type="hidden" name="csrf" value="'
         . htmlspecialchars(csrf_token(), ENT_QUOTES) . '">';
}

function check_csrf(): void {
    $ok = isset($_POST['csrf'], $_SESSION['csrf'])
        && hash_equals($_SESSION['csrf'], (string)$_POST['csrf']);
    if (!$ok) {
        http_response_code(403);
        exit('Jeton CSRF invalide — rechargez la page.');
    }
}

function e(string $s): string {
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}
