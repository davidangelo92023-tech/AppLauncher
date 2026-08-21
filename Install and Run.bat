@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title App Launcher setup

if exist "%~dp0.setup_ok" goto :launch

echo ============================================
echo   App Launcher - one-time setup
echo ============================================
echo.

rem Already have a built exe (no Python needed at all)? Skip straight to launch.
if exist "%~dp0AppLauncher.exe" (
    echo ok>"%~dp0.setup_ok"
    goto :launch
)

rem ---- find Python ----
set "PYEXE="
where python >nul 2>nul
if %errorlevel%==0 set "PYEXE=python"
if "%PYEXE%"=="" (
    where py >nul 2>nul
    if !errorlevel!==0 set "PYEXE=py"
)
if "%PYEXE%"=="" if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
)

rem Windows sometimes has a fake "python" stub that just opens the Microsoft
rem Store instead of running - make sure whatever we found actually works.
if not "%PYEXE%"=="" (
    "%PYEXE%" --version >nul 2>nul
    if errorlevel 1 set "PYEXE="
)

if "%PYEXE%"=="" (
    echo Python wasn't found on this PC - downloading and installing it now.
    echo This only happens once and takes a minute or two. Please wait...
    echo.
    set "PYINSTALLER=%TEMP%\applauncher-python-setup.exe"
    powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.6/python-3.12.6-amd64.exe' -OutFile '%PYINSTALLER%' -UseBasicParsing } catch { exit 1 }"

    if not exist "%PYINSTALLER%" (
        echo.
        echo Couldn't download Python automatically - your internet connection
        echo or a firewall may be blocking it. Please install it yourself from:
        echo https://www.python.org/downloads/
        echo Make sure "Add python.exe to PATH" is checked during setup, then
        echo double-click this file again.
        pause
        exit /b 1
    )

    echo Installing Python silently, please wait...
    "%PYINSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_tcltk=1 Include_test=0
    del "%PYINSTALLER%" >nul 2>nul

    if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
        set "PYEXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    ) else (
        echo.
        echo Python installed, but this window can't see it yet.
        echo Please double-click this file again to finish setup.
        pause
        exit /b 1
    )
    echo Python installed.
    echo.
)

echo Found Python:
"%PYEXE%" --version
echo.

echo Installing required packages...
"%PYEXE%" -m pip install --quiet --disable-pip-version-check -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo Package install hit a problem - copy the text above and send it back
    echo so it can get fixed. Diagnose.bat also does a fuller check.
    pause
    exit /b 1
)

echo ok>"%~dp0.setup_ok"
echo.
echo Setup complete!
echo.

:launch
if exist "%~dp0App Launcher.vbs" (
    start "" wscript "%~dp0App Launcher.vbs"
) else (
    start "" pythonw "%~dp0run.py"
)
exit /b 0
