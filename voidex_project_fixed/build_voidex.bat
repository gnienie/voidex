@echo off
setlocal
cd /d "%~dp0"
py -m pip install --upgrade pip
py -m pip install pyinstaller pillow certifi
py -m PyInstaller --noconfirm --clean --onefile --windowed --name voidex --icon voidex.ico --add-data "voidex_logo.png;." --collect-data certifi voidex.py
if errorlevel 1 (
  echo.
  echo BUILD FAILED. Check the error above.
  pause
  exit /b 1
)
echo.
echo Build complete: dist\voidex.exe
pause
