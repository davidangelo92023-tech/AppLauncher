@echo off
cd /d "%~dp0"
echo Installing packages needed by App Launcher (Pillow, pywebview)...
echo.
where python >nul 2>nul
if not %errorlevel%==0 (
    echo Couldn't find Python on your PATH.
    echo Install it from https://www.python.org/downloads/ and check
    echo "Add python.exe to PATH" during setup, then run this again.
    pause
    exit /b 1
)
python -m pip install -r requirements.txt
echo.
echo ===================================================
echo Done - look above for any errors.
echo If you see a line like "Successfully installed ... pywebview ...",
echo the browser button should work now. If you see red error text
echo instead, copy it and send it back so it can get fixed.
echo ===================================================
pause
