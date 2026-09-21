# ⏱ Tcontrol

**Contrôle parental du temps de jeu, synchronisé sur plusieurs PC.**

📦 Repo : [github.com/Thibstudio24/Tcontrol](https://github.com/Thibstudio24/Tcontrol)

Tcontrol est un système en deux parties :

1. **Une application Windows** (`app/`) qui tourne en arrière-plan sur chaque PC,
   chronomètre le temps passé sur les jeux sélectionnés, prévient l'utilisateur
   (notifications à 10 min, 5 min puis temps écoulé) et **ferme puis bloque**
   les jeux quand la limite quotidienne est atteinte.
2. **Un site PHP/MySQL** (`site/`, pensé pour InfinityFree) qui centralise tout :
   le temps se **synchronise entre tous les PC** — si un utilisateur change de
   machine, son compteur le suit. L'interface admin web permet de suivre qui a
   joué, combien de temps, et s'il a été bloqué (historique de 7 jours).

---

## ✨ Fonctionnalités

| | App Windows | Site web |
|---|---|---|
| 👤 **Utilisateurs** | Identification automatique (session Windows), chrono visible, liste des jeux surveillés | Connexion auto au 1ᵉʳ ping, alias renommables |
| ⏳ **Limite** | Affichage du temps restant en direct | Une limite **globale commune**, modifiable en ligne et appliquée partout en moins d'1 min |
| 🔔 **Notifications** | Toasts Windows à **10 min**, **5 min** et **0 min** | — |
| 🚫 **Blocage** | Fermeture forcée + **anti-relance** jusqu'au reset | Statut « bloqué » visible dans les rapports |
| 🔄 **Synchro** | Ping toutes les **60 s**, cache local si hors ligne | Temps cumulé **toutes machines confondues** |
| 🛡 **Anti-contournement** | Quitter = mot de passe admin · démarrage auto Windows · réduction en zone de notification | — |
| 🌙 **Reset** | — | Heure configurable (défaut minuit), rétention **7 jours max** |
| 🔑 **Admin** | Bouton 🔑 (mêmes identifiants que le site) : choix des jeux parmi les processus actifs | Dashboard du jour + historique 7 j + gestion jeux / limite / clé API |

---

## 🗂 Structure du projet

```
tcontrol/
├── app/                        ← application Windows (Python)
│   ├── main.py                 ← interface graphique + point d'entrée
│   ├── core/
│   │   ├── monitor.py          ← boucle : comptage / blocage / notifications / synchro
│   │   ├── processes.py        ← détection et fermeture des processus (psutil/taskkill)
│   │   ├── sync.py             ← client de l'API PHP
│   │   ├── state.py            ← cache local (mode hors ligne)
│   │   ├── config.py           ← config (%APPDATA%\Tcontrol\config.json)
│   │   ├── notify.py           ← toasts Windows
│   │   ├── tray_helper.py      ← icône zone de notification
│   │   ├── autostart.py        ← démarrage automatique (registre)
│   │   ├── crypto.py           ← déblocage admin hors ligne
│   │   └── logic.py            ← utilitaires (jour logique, formats…)
│   ├── requirements.txt
│   └── build.bat               ← génère dist\Tcontrol.exe (PyInstaller)
│
├── site/                       ← à uploader sur InfinityFree (dans htdocs/)
│   ├── install.php             ← installateur (crée les tables + l'admin + config_db.php)
│   ├── index.php               ← page d'accueil publique
│   ├── api/
│   │   ├── ping.php            ← synchro des apps (POST JSON, toutes les 60 s)
│   │   ├── auth.php            ← vérif identifiants admin (app)
│   │   ├── admin.php           ← API d'admin pour l'app (jeux bloqués, état)
│   │   ├── db.php / common.php / .htaccess
│   └── admin/
│       ├── index.php           ← tableau de bord du jour
│       ├── history.php         ← 7 derniers jours
│       ├── users.php           ← alias & utilisateurs
│       ├── settings.php        ← limite, reset, clé API, jeux, mot de passe
│       └── login.php / logout.php / auth.php / header.php / footer.php / style.css
│
├── assets/logo.png
├── GUIDE_DEPLOIEMENT.md        ← pas-à-pas InfinityFree détaillé (personnalisé)
├── git-publish.bat             ← push vers GitHub en 1 double-clic
├── .gitignore                  ← protège les secrets (config_db.php…)
└── README.md
```

---

## 🚀 Mise en route (résumé)

Le détail complet avec captures est dans **[GUIDE_DEPLOIEMENT.md](GUIDE_DEPLOIEMENT.md)**.

### 1. Le site (InfinityFree)

1. Crée un compte + un site gratuit sur [infinityfree.com](https://www.infinityfree.com)
2. Crée une base MySQL dans le panneau (note hôte, nom, utilisateur, mot de passe)
3. Upload le contenu de `site/` à la racine (`htdocs/`)
4. Ouvre `https://ton-site/install.php`, remplis le formulaire → **supprime `install.php`**
5. Connecte-toi à `/admin/login.php`, récupère la **clé API** dans *Paramètres*

### 2. L'app Windows

```bat
cd app
build.bat
```

→ `dist\Tcontrol.exe`. Copie-le sur chaque PC, lance-le, puis bouton **🔑 Admin** :
- **Configuration** : URL de l'API (`https://ton-site/api`) + clé API → *Enregistrer*
- **Jeux bloqués** : coche les processus à surveiller (ex : `steam.exe`, `fortnite.exe`…)
- Coche **« Démarrer automatiquement avec Windows »**

C'est tout : le chrono démarre dès qu'un jeu surveillé tourne, et le statut
apparaît en direct sur le site.

---

## 🔌 Protocole de synchro (pour les curieux)

`POST /api/ping.php` — JSON :

```json
{
  "key": "<clé API>",
  "user": "lucas", "machine": "PC-SALON",
  "delta": 58,                        // secondes de jeu depuis le dernier ping
  "day": "2026-09-10",                // jour logique du delta
  "running": ["fortnite.exe"],
  "blocked": false
}
```

Réponse :

```json
{
  "ok": true, "day": "2026-09-10",
  "limit": 7200, "used": 1830, "remaining": 5370,
  "blocked": false, "reset_hour": 0,
  "alias": "Lucas", "processes": ["fortnite.exe", "steam.exe"]
}
```

- Le serveur **additionne les deltas** par utilisateur/jour (toutes machines confondues)
  → le compteur est naturellement **partagé entre les PC**.
- En cas de coupure internet, l'app continue avec son **cache local** et envoie le
  delta accumulé au retour du réseau (à la minute près — mode tolérant).
- Le « jour logique » tient compte de l'heure de reset (ex : reset 4h → une session
  à 2h du matin compte encore sur la veille).

## 🔒 Sécurité

- Mots de passe admin hashés (**bcrypt**), identiques pour le site et l'app
- **Clé API** (48 caractères aléatoires) requise sur chaque requête machine
- Requêtes SQL **préparées** partout, sorties HTML échappées, sessions `HttpOnly`,
  jetons **CSRF** sur les formulaires, tempo anti-force-brute sur les logins
- `config_db.php` interdit d'accès direct par `.htaccess`

## 🧰 Développement de l'app

```bash
cd app
pip install -r requirements.txt
python main.py
```

Python 3.10+ · [customtkinter](https://customtkinter.tomschimansky.com/) · psutil · requests · pystray · win10toast-persist

> ⚠️ Note InfinityFree : son pare-feu anti-bots peut bloquer les requêtes
> hors-navigateur. Les fichiers du site fonctionnent **tels quels sur n'importe
> quel hébergeur PHP+MySQL** — voir la section dédiée du guide de déploiement.
