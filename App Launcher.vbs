Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = scriptDir

exePath = scriptDir & "\AppLauncher.exe"

' Use the built .exe only if it exists AND it's not older than ANY of the
' app's .py source files - checking just one file (like AppLauncher.py
' alone) missed edits to the others (AppContacts.py, AppNet.py, etc.) and
' let a stale .exe silently keep running instead of picking up real
' changes. Comparing against every .py file in this folder closes that gap.
useExe = False
If fso.FileExists(exePath) Then
    useExe = True
    exeModified = fso.GetFile(exePath).DateLastModified
    Set pyFiles = fso.GetFolder(scriptDir).Files
    For Each f In pyFiles
        If LCase(fso.GetExtensionName(f.Name)) = "py" Then
            If f.DateLastModified > exeModified Then
                useExe = False
                Exit For
            End If
        End If
    Next
End If

If useExe Then
    WshShell.Run """" & exePath & """", 0, False
Else
    runPy = """" & scriptDir & "\run.py"""
    On Error Resume Next

    Err.Clear
    WshShell.Run "pythonw.exe " & runPy, 0, False
    If Err.Number <> 0 Then
        Err.Clear
        WshShell.Run "pyw.exe " & runPy, 0, False
    End If

    If Err.Number <> 0 Then
        MsgBox "Couldn't find Python (pythonw/pyw) on your PATH." & vbCrLf & _
               "Install Python from https://www.python.org/downloads/ and make sure" & vbCrLf & _
               """Add python.exe to PATH"" is checked during setup, then try again.", _
               vbExclamation, "App Launcher"
    End If

    On Error Goto 0
End If
