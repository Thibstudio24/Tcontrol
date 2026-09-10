@echo off
REM ============================================================
REM  Build de Tcontrol en .exe autonome (Windows)
REM  Prérequis : Python 3.10+ installe (https://python.org)
REM ============================================================
cd /d %~dp0

echo [1/3] Installation des dependances...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto erreur

echo [2/3] Generation de l'icone...
if not exist assets mkdir assets
python -c "from PIL import Image; im=Image.open(r'assets\logo.png') if __import__('os').path.exists(r'assets\logo.png') else Image.new('RGBA',(256,256),(14,116,144,255)); im.save(r'assets\icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"

echo [3/3] Compilation avec PyInstaller...
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
    --name Tcontrol ^
    --icon assets\icon.ico ^
    --add-data "assets;assets" ^
    main.py
if errorlevel 1 goto erreur

echo.
echo ============================================================
echo  OK ! L'executable est : dist\Tcontrol.exe
echo  Place-le ou tu veux puis lance-le une fois.
echo  La config se fait ensuite depuis le bouton (cle) Admin.
echo ============================================================
pause
exit /b 0

:erreur
echo.
echo ERREUR pendant le build. Verifie que Python est installe et dans le PATH.
pause
exit /b 1
