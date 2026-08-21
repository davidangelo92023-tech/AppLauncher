@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo  Building AppLauncher.exe / AppBrowser.exe / AppFriends.exe
echo  This is a ONE-TIME step. It needs Python + internet
echo  access (to download PyInstaller and the app's
echo  dependencies). The .exe files it produces do NOT
echo  need Python - those are what you share with friends.
echo ===================================================
echo.

where python >nul 2>nul
if not %errorlevel%==0 (
    echo Couldn't find Python on your PATH.
    echo Install it from https://www.python.org/downloads/ and check
    echo "Add python.exe to PATH" during setup, then run this again.
    pause
    exit /b 1
)

echo Installing build dependencies...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt pyinstaller
if not %errorlevel%==0 (
    echo.
    echo pip install failed - see the errors above.
    pause
    exit /b 1
)

echo.
echo Building AppLauncher.exe ...
python -m PyInstaller --noconfirm --onefile --windowed --name AppLauncher --icon icon.ico run.py
if not %errorlevel%==0 goto :buildfail

echo.
echo Building AppBrowser.exe ...
python -m PyInstaller --noconfirm --onefile --windowed --name AppBrowser --icon icon.ico ^
    --hidden-import webview.platforms.edgechromium ^
    --hidden-import webview.platforms.winforms ^
    --hidden-import clr ^
    AppBrowser.py
if not %errorlevel%==0 goto :buildfail

echo.
echo Building AppFriends.exe ...
python -m PyInstaller --noconfirm --onefile --windowed --name AppFriends --icon icon.ico AppFriends.py
if not %errorlevel%==0 goto :buildfail

echo.
echo Collecting finished .exe files...
copy /y "dist\AppLauncher.exe" ".\AppLauncher.exe" >nul
copy /y "dist\AppBrowser.exe" ".\AppBrowser.exe" >nul
copy /y "dist\AppFriends.exe" ".\AppFriends.exe" >nul

echo Cleaning up build folders...
rmdir /s /q build >nul 2>nul
rmdir /s /q dist >nul 2>nul
del /q *.spec >nul 2>nul

echo.
echo ===================================================
echo  Done! AppLauncher.exe, AppBrowser.exe and
echo  AppFriends.exe are now sitting in this folder.
echo  Double-click AppLauncher.exe (or "App Launcher.vbs")
echo  to run it - no Python needed from here on.
echo ===================================================
pause
exit /b 0

:buildfail
echo.
echo Build failed - see the errors above.
echo (AppBrowser.py depends on pywebview, which can be picky about
echo  hidden imports depending on your Windows/WebView2 setup - if
echo  only that one fails, AppLauncher.exe and AppFriends.exe are
echo  likely still fine to use.)
pause
exit /b 1
