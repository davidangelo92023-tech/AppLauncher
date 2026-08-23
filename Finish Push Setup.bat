@echo off
cd /d "%~dp0"
echo ============================================================
echo  Finishing git setup for this folder
echo ============================================================
echo.
echo This tells git that this folder's "main" branch pushes to
echo GitHub's "main" branch (a one-time setup step I missed earlier),
echo then pushes your already-made commit.
echo.

git push --set-upstream origin main
if not %errorlevel%==0 (
    echo.
    echo ===================================================
    echo  Push failed - see the errors above. If it asked you
    echo  to sign in, follow the prompts in the window/browser
    echo  that opened, then run this file again.
    echo ===================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Done! From now on, plain old Push Update.bat will work
echo  directly from this folder.
echo ============================================================
pause
