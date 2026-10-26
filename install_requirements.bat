@echo off
setlocal
cd /d "%~dp0"
py -3.12 -m pip install --upgrade pip
if errorlevel 1 goto failed
py -3.12 -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Dependencies installed successfully.
pause
exit /b 0
:failed
echo.
echo Could not install dependencies. Make sure Python 3.12 (64-bit) is installed.
pause
exit /b 1
