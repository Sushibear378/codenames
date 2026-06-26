@echo off
cd /d "%~dp0"

echo Arbeitsverzeichnis: %cd%
echo.

if not exist start_server.py (
  echo FEHLER: start_server.py nicht gefunden. Diese .bat muss IM codenames-Ordner liegen.
  pause
  exit /b 1
)

echo [1/3] PyInstaller installieren...
python -m pip install pyinstaller || (echo FEHLER: python/pip nicht gefunden. ^& pause ^& exit /b 1)

echo [2/3] Server bauen...
python -m PyInstaller --onefile --windowed --name codenames_server start_server.py

echo [3/3] Client bauen...
python -m PyInstaller --onefile --windowed --name codenames_client start_client.py

echo.
echo Fertig! Die .exe-Dateien liegen in dist\codenames_server.exe und dist\codenames_client.exe
pause