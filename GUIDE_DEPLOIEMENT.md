# 🚀 Guide de déploiement pas à pas — Tcontrol

Ce guide est personnalisé pour ton installation :
- 🌐 Site : **https://tcontrol.thibstudio.rf.gd**
- 📦 Repo : https://github.com/Thibstudio24/Tcontrol

Durée totale : **~25 minutes**.

---

## Étape 0 — Prérequis

- [ ] Un PC Windows pour l'app (Windows 10 ou 11)
- [ ] **Python 3.10+** installé sur le PC qui servira à fabriquer le `.exe`
      (coche bien *"Add Python to PATH"* pendant l'installation)
      → https://www.python.org/downloads/
- [ ] Une connexion internet

---

## Étape 1 — Ton site existe déjà ✔ (5 min)

Ton domaine `tcontrol.thibstudio.rf.gd` est déjà créé chez InfinityFree
(il répond bien, son dossier est juste vide pour l'instant). Tu peux donc
allègrement sauter la création :

1. Connecte-toi sur **https://dash.infinityfree.com**
2. Clique sur ton hébergement `tcontrol.thibstudio.rf.gd` → **« Control Panel »** (vPanel).

> 🔧 Si un jour tu repars de zéro : *Create Account* → choisis le sous-domaine →
> attends qu'il soit *Active*.

### 1bis — Créer la base de données

5. Dans le panneau, section **Databases** → **MySQL Databases** :
   - nom : `tcontrol` (il deviendra p. ex. `epiz_34567890_tcontrol`)
   - crée et **note précieusement** :
     - `MySQL Host Name` (genre `sql305.byetcluster.com`)
     - `MySQL Database Name`
     - `MySQL Username` (souvent le même préfixe que la base)
     - `MySQL Password` = le mot de passe de ton compte d'hébergement
       (celui choisi à la création du *compte d'hébergement*, pas du compte InfinityFree)

---

## Étape 2 — Uploader les fichiers du site (5 min)

1. Dans le panneau : **Files → Online File Manager** (ou FileZilla en FTP,
   hôte `ftpupload.net`).
2. Ouvre le dossier **`htdocs/`** et supprime les fichiers par défaut
   (`index2.html`, etc.).
3. Upload **tout le contenu** du dossier `site/` du projet
   (dossiers `api/` et `admin/`, fichiers `index.php`, `install.php`…).
   Option simple : zippe le contenu de `site/`, upload le zip, puis
   *Extract* dans `htdocs/`.

> Structure attendue ensuite :
> ```
> htdocs/
> ├── index.php
> ├── install.php
> ├── api/…
> └── admin/…
> ```

---

## Étape 3 — Installer (2 min)

1. Ouvre dans ton navigateur : **https://tcontrol.thibstudio.rf.gd/install.php**
2. Remplis :
   - **Hôte MySQL**, **Nom de la base**, **Utilisateur**, **Mot de passe** (étape 1bis)
   - **Identifiant + mot de passe administrateur** → ce seront TES identifiants
     pour le site ET pour le bouton 🔑 de l'app. Garde-les !
3. Clique **Installer**. Tu dois voir *« ✅ Installation réussie ! »*
4. **🔥 Supprime le fichier `install.php`** via le File Manager (important !)

> 💡 Si le message « Écriture impossible de api/config_db.php » apparaît :
> crée le fichier `api/config_db.php` à la main dans le File Manager et
> colle le contenu affiché.

---

## Étape 4 — Tester le site (2 min)

1. Va sur **https://tcontrol.thibstudio.rf.gd/** → page d'accueil Tcontrol.
2. Va sur `/admin/login.php` → connecte-toi.
3. Tu dois voir le tableau de bord vide (*« Personne ne s'est encore connecté »*).
4. Ouvre **Paramètres** :
   - note la **clé API** (48 caractères)
   - règle la **limite quotidienne** (ex : 2 h 00) et l'**heure de reset** (défaut 00h00)

✅ Le site est prêt.

---

## Étape 5 — Fabriquer l'app Windows `.exe` (5 min)

Sur le PC de build :

1. Copie le dossier `app/` du projet quelque part (ex : `C:\dev\tcontrol\app`).
2. Double-clique sur **`build.bat`**.
   - le script installe les dépendances (internet requis) puis compile
3. À la fin : **`dist\Tcontrol.exe`** est prêt. 🎉

> Le `.exe` est autonome : Python n'est **pas** nécessaire sur les autres PC.

---

## Étape 6 — Configurer l'app sur chaque PC (2 min / PC)

1. Copie `Tcontrol.exe` sur le PC (ex : `C:\Program Files\Tcontrol\` ou le Bureau).
2. Lance-le une première fois.
3. Clique **🔑 Admin** (en haut à droite) → tes identifiants du site.
4. Onglet **Configuration** :
   - **URL de l'API** : **déjà pré-remplie** (`https://tcontrol.thibstudio.rf.gd/api`) ✅
   - **Clé API** : colle celle des Paramètres du site
   - **Enregistrer et synchroniser** → le statut passe à **« ● en ligne »**
   - coche **« Démarrer automatiquement avec Windows »** ✅
5. Onglet **Jeux bloqués** : la liste des processus actifs s'affiche →
   clique **Bloquer** à côté de chaque jeu à surveiller
   (astuce : lance le jeu d'abord, puis **🔄 Actualiser les processus**).

✅ Le PC est équipé : le chrono partagé démarre dès qu'un jeu surveillé tourne.

> 📁 Config & cache de l'app : `%APPDATA%\Tcontrol\` (config.json, cache.json).
> Si tu changes l'URL/clé plus tard : 🔑 → Configuration.

---

## Étape 7 — Vérifier que tout marche ensemble (3 min)

1. Sur le PC, lance un des jeux bloqués (même 1 minute suffit).
2. Le chrono de l'app descend ; le site (page d'accueil admin) affiche
   ton utilisateur au bout d'1 minute max.
3. Test express de la fin de temps : sur le site → Paramètres → met la limite
   à **0 h 01 min** → attends 1-2 minutes :
   - toast « 5 minutes » à 5 min restantes, « 10 minutes » à 10 min, puis
   - toast « Temps écoulé », le jeu se ferme et **impossible de le relancer** 🚫
   - le site affiche le badge **bloqué**
4. Remets la limite normale. Pour débloquer tout de suite sans attendre le reset,
   tu peux mettre une limite énorme (le blocage saute au prochain ping).

---

## 🧪 Fonctionnement quotidien

- L'app démarre **toute seule** avec Windows, **minimisée** à côté de l'horloge.
- Fermer la fenêtre = l'app continue en zone de notification
  (icône horloge bleue → clic droit : ouvrir / quitter).
- **Quitter vraiment** = bouton 🔑 → panneau admin → *Quitter Tcontrol*
  (mot de passe requis).
- Sur le site → *Historique* : les 7 derniers jours. Au-delà : suppression auto.

---

## ⚠️ Point important : le pare-feu d'InfinityFree

InfinityFree protège les sites gratuits avec un **contrôle anti-bots JavaScript**,
qui bloque parfois les requêtes n venant pas d'un navigateur — donc potentiellement
le ping de l'app. L'app gère ce cas proprement (elle passe en **cache local** et
affiche « hors ligne » au lieu de planter).

Si tu constates que l'app reste « hors ligne » en permanence alors que le site
s'ouvre dans le navigateur, deux options :

1. **Utiliser un nom de domaine perso** (gratuit sur Freenom/alternatives ou ~1 €/an)
   associé au compte InfinityFree : le contrôle anti-bots est souvent plus souple.
2. **Héberger les mêmes fichiers ailleurs** — le site n'utilise que **PHP + MySQL**,
   il fonctionne tel quel sur n'importe quel hébergeur les proposant
   (ex. **AlwaysData** (offre gratuite 100 Mo), Hostinger, o2switch…).
   Il suffit de refaire les étapes 2→4 et de changer l'URL dans l'app.

L'interface admin web (navigateur) fonctionne dans tous les cas.

---

## 🆘 Dépannage

| Problème | Solution |
|---|---|
| App « hors ligne » | Vérifie l'URL (doit finir par `/api`), la clé API, et le point pare-feu ci-dessus |
| « Réponse invalide (pas du JSON) » | Pare-feu InfinityFree → voir section ci-dessus |
| Le jeu ne se ferme pas | Son nom de processus ≠ celui bloqué. Dans 🔑 → Jeux bloqués, actualise les processus **pendant que le jeu tourne** et bloque le bon |
| Le jeu se relance quand même | Vérifie que le statut app = « ● en ligne » et que le badge bloqué est actif. Certains jeux se relancent via un lanceur : bloque **aussi le lanceur** (steam.exe, epicgameslauncher.exe…) |
| Chrono qui ne tourne pas | Le chrono ne compte que si un jeu **de la liste bloquée** tourne (choix voulu) |
| Site : « Base de données injoignable » | Identifiants MySQL dans `api/config_db.php` incorrects → refais l'étape 1bis |
| Mot de passe admin oublié | Relance `install.php` (ré-upload-le) : il **réinitialise** le mot de passe admin (en gardant les données) |
| Les toasts ne s'affichent pas | Vérifie que Windows n'est pas en « Assistant de concentration » / notifications désactivées pour Tcontrol |

---

## 🔁 Mise à jour de l'app

1. Modifie le code, relance `build.bat`, redistribue le nouveau `Tcontrol.exe`.
2. La config (`%APPDATA%\Tcontrol\config.json`) est conservée entre les versions.
