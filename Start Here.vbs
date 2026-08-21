Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

markerPath = scriptDir & "\.setup_ok"
batPath = scriptDir & "\Install and Run.bat"
mainVbs = scriptDir & "\App Launcher.vbs"

If fso.FileExists(markerPath) Then
    ' Already set up before - launch straight in, silently.
    WshShell.Run """" & mainVbs & """", 0, False
Else
    ' First time - run the setup script with a visible window so they can
    ' see what's happening (it may download Python), then it launches the
    ' app itself when done.
    WshShell.Run """" & batPath & """", 1, True
End If
