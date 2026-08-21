@echo off
if exist "%~dp0AppFriends.exe" (
    start "" "%~dp0AppFriends.exe"
) else (
    start "" pythonw "%~dp0AppFriends.py"
)
