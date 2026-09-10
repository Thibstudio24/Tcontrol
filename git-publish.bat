@echo off
REM ============================================================
REM  Publie le projet sur GitHub (Thibstudio24/Tcontrol)
REM  Prerequis : Git installe (https://git-scm.com/download/win)
REM ============================================================
cd /d %~dp0

if not exist .git (
    git init -b main
)

git add .
git commit -m "Tcontrol v1.0 : app Windows + site PHP + docs"

git remote remove origin 2>nul
git remote add origin https://github.com/Thibstudio24/Tcontrol.git

git push -u origin main

echo.
echo ============================================================
echo  Termine ! Si le push demande une authentification :
echo  - utilise ton compte GitHub + un Personal Access Token
echo    (github.com -^> Settings -^> Developer settings -^> Tokens)
echo  - ou plus simple : ouvre ce dossier avec GitHub Desktop.
echo ============================================================
pause
