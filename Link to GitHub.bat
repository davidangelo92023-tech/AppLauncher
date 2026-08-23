@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo  Link this folder to your GitHub repo
echo ============================================================
echo.
echo This turns THIS folder into a real git working copy pointed at
echo the same repo as your other App Launcher copy (AppLauncher.git),
echo so Push Update.bat will work directly from here afterward.
echo.
echo IMPORTANT: this does NOT delete, overwrite, or move any of your
echo files. It only sets up git's own bookkeeping (a .git folder).
echo.
echo Press any key to continue, or close this window to cancel.
pause >nul
echo.

where git >nul 2>nul
if not %errorlevel%==0 (
    echo Couldn't find git on your PATH.
    echo Install it from https://git-scm.com/download/win, then run this again.
    pause
    exit /b 1
)

if exist ".git" (
    echo This folder is already linked to git - nothing to do.
    pause
    exit /b 0
)

echo Setting up git...
git init -b main
if not %errorlevel%==0 (
    echo.
    echo "git init" failed - see the error above. Nothing else was changed.
    pause
    exit /b 1
)

git remote add origin https://github.com/davidangelo92023-tech/AppLauncher.git

echo.
echo Fetching your repo history from GitHub...
git fetch origin
if not %errorlevel%==0 (
    echo.
    echo ===================================================
    echo  Fetch failed - see the error above. If it asked you
    echo  to sign in, follow the prompts in the window/browser
    echo  that opened, then run this file again.
    echo  Nothing else was changed - it's safe to retry.
    echo ===================================================
    pause
    exit /b 1
)

git reset origin/main >nul
if not %errorlevel%==0 (
    echo.
    echo "git reset" failed - see the error above. Copy it and send it back
    echo if you're not sure what it means.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done. This folder is now linked to your GitHub repo.
echo  Your files here were NOT changed - only git's own bookkeeping
echo  was set up.
echo.
echo  Run "git status" here to see what's different from what's
echo  already on GitHub before your next Push Update.bat run.
echo ============================================================
pause
