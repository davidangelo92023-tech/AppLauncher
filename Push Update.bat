@echo off
cd /d "%~dp0"
echo ===================================================
echo  Pushing your changes to GitHub
echo  This is what makes the server (Render) and everyone's
echo  "Update available" notice actually pick up new fixes -
echo  nothing changes for anyone until this step runs.
echo ===================================================
echo.

where git >nul 2>nul
if not %errorlevel%==0 (
    echo Couldn't find git on your PATH.
    echo Install it from https://git-scm.com/download/win, then run this again.
    pause
    exit /b 1
)

REM Make sure git knows who's committing - without this, every commit
REM fails silently with "Author identity unknown" and nothing gets
REM pushed even though the script used to say "Done!" anyway. This only
REM sets it for this one repo (--local), not your whole PC.
git config user.name >nul 2>nul
if not %errorlevel%==0 git config --local user.name "David"
git config user.email >nul 2>nul
if not %errorlevel%==0 git config --local user.email "david@applauncher.local"

REM Clear out any leftover half-staged state from a previous run that
REM didn't finish (this only unstages, it never touches your files).
git reset >nul 2>nul

git add -A

git diff --cached --quiet
if %errorlevel%==0 (
    echo Nothing new to commit - your changes are already saved.
    goto :dopush
)

git commit -m "Update App Launcher"
if not %errorlevel%==0 (
    echo.
    echo ===================================================
    echo  The commit step failed - see the error above.
    echo  Nothing was pushed. Copy the error and send it back
    echo  if you're not sure what it means.
    echo ===================================================
    pause
    exit /b 1
)

:dopush
echo.
echo Pushing to GitHub...
git push
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
echo ===================================================
echo  Done! Render usually picks this up within a minute
echo  or two. Sign out and back in to App Launcher after
echo  that to pick up the fix.
echo ===================================================
pause
