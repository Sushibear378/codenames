@echo off
pip install pyinstaller
pyinstaller --onefile --windowed --name codenames_server start_server.py
pyinstaller --onefile --windowed --name codenames_client start_client.py
echo.
echo Fertig! Die .exe-Dateien liegen in dist\codenames_server.exe und dist\codenames_client.exe
pause
