@echo off
setlocal
cd /d "%~dp0"
echo ======================================
echo        VOIDEX - Windows build
echo ======================================
echo.
py -3.12 -m pip install --upgrade pip
if errorlevel 1 goto failed
py -3.12 -m pip install -r requirements.txt
if errorlevel 1 goto failed
py -3.12 voidex_icon.py
if errorlevel 1 goto failed
py -3.12 -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name Voidex ^
  --icon "assets\voidex.ico" ^
  --add-data "assets;assets" ^
  --collect-all customtkinter ^
  --collect-all minecraft_launcher_lib ^
  voidex.py
if errorlevel 1 goto failed
echo.
echo Build complete: dist\Voidex.exe
pause
exit /b 0
:failed
echo.
echo Build failed. Read the error above.
pause
exit /b 1
