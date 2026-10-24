@echo off
rem Gera o executável em dist\TURZX Studio\ e o pacote zip em dist\.
cd /d "%~dp0"
python -m pip install -r requirements.txt pyinstaller || exit /b 1
python -m PyInstaller --noconfirm --clean --windowed --name "TURZX Studio" --icon assets\icon.ico ^
  --add-data "web;web" --add-data "assets;assets" --add-data "tools;tools" --add-data "third_party;third_party" ^
  --hidden-import tray --hidden-import pystray._win32 app.py || exit /b 1
for /f %%v in ('python -c "import version; print(version.VERSION)"') do set VER=%%v
powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\TURZX Studio' -DestinationPath 'dist\TURZX-Studio-%VER%-win64.zip'"
echo.
echo Pronto: dist\TURZX Studio\TURZX Studio.exe  e  dist\TURZX-Studio-%VER%-win64.zip
