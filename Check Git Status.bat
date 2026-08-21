@echo off
cd /d "%~dp0"
echo ===================================================
echo  Checking what git has tracked in this repo
echo  (writes a report to git_status_report.txt so it
echo  can be reviewed for anything personal that
echo  shouldn't be here)
echo ===================================================
echo.

where git >nul 2>nul
if not %errorlevel%==0 (
    echo Couldn't find git on your PATH.
    echo Install it from https://git-scm.com/download/win and try again.
    pause
    exit /b 1
)

echo ===== git status ===== > "git_status_report.txt"
git status >> "git_status_report.txt" 2>&1
echo. >> "git_status_report.txt"
echo ===== git remote (where pushes actually go) ===== >> "git_status_report.txt"
git remote -v >> "git_status_report.txt" 2>&1
echo. >> "git_status_report.txt"
echo ===== last 10 commits (local) ===== >> "git_status_report.txt"
git log -10 --oneline >> "git_status_report.txt" 2>&1
echo. >> "git_status_report.txt"
echo ===== last 10 commits on origin/main (what's actually on GitHub) ===== >> "git_status_report.txt"
git fetch origin >> "git_status_report.txt" 2>&1
git log -10 --oneline origin/main >> "git_status_report.txt" 2>&1
echo. >> "git_status_report.txt"
echo ===== how local main compares to origin/main ===== >> "git_status_report.txt"
git status -uno -b >> "git_status_report.txt" 2>&1
echo. >> "git_status_report.txt"
echo ===== All files git has ever committed (full history) that look ===== >> "git_status_report.txt"
echo ===== personal/unrelated - Music, PCNotif, Ash Tag, photos, etc. ===== >> "git_status_report.txt"
git log --all --pretty=format: --name-only --diff-filter=A | findstr /I "Music PCNotif \"Ash Tag\" .jpg .jpeg .png .heic David" >> "git_status_report.txt" 2>&1
echo. >> "git_status_report.txt"
echo (If that last section is empty, nothing personal was ever committed - good.) >> "git_status_report.txt"

type git_status_report.txt
echo.
echo Done - also saved as git_status_report.txt in this folder.
pause
