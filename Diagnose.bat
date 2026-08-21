@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo ============================================
echo   App Launcher - Diagnose ^& Fix
echo ============================================
echo.

rem --- find a working Python command ---
set PYCMD=
where python >nul 2>nul
if %errorlevel%==0 set PYCMD=python
if "%PYCMD%"=="" (
    where py >nul 2>nul
    if !errorlevel!==0 set PYCMD=py
)

if "%PYCMD%"=="" (
    echo [FAIL] Could not find Python on this PC's PATH.
    echo.
    echo   1. Install it from https://www.python.org/downloads/
    echo   2. On the FIRST setup screen, check the box that says
    echo      "Add python.exe to PATH" before clicking Install.
    echo   3. Restart your PC, then double-click this file again.
    echo.
    pause
    exit /b 1
)

echo [OK] Found Python: %PYCMD%
%PYCMD% --version
echo.

echo Checking what App Launcher needs...
echo.

set NEED_FIX=0

%PYCMD% -c "import tkinter" 2>nul
if %errorlevel%==0 (
    echo [OK]   tkinter   ^(the window toolkit - built into Python^)
) else (
    echo [FAIL] tkinter   -- missing from this Python install.
    echo         Reinstall Python from python.org ^(not the Microsoft
    echo         Store version^) and make sure "tcl/tk and IDLE" stays
    echo         checked during setup. This one can't be pip-installed.
    set NEED_FIX=1
)

%PYCMD% -c "import PIL" 2>nul
if %errorlevel%==0 (
    echo [OK]   Pillow    ^(icons ^& backgrounds^)
) else (
    echo [ ]    Pillow    -- not installed yet, will install below.
)

%PYCMD% -c "import webview" 2>nul
if %errorlevel%==0 (
    echo [OK]   pywebview ^(in-app browser^)
) else (
    echo [ ]    pywebview -- not installed yet, will install below.
)

echo.
echo Installing/repairing packages via pip...
echo.
%PYCMD% -m pip install -r requirements.txt
echo.
echo ============================================
if "%NEED_FIX%"=="1" (
    echo tkinter is still missing - see the FAIL note above.
    echo That one has to be fixed by reinstalling Python itself.
) else (
    echo Done. Try double-clicking "App Launcher.vbs" now.
)
echo.
echo If it still doesn't open, or you saw red error text
echo above, copy everything in this window and send it back
echo so it can get fixed.
echo ============================================
pause
