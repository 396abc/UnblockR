Dim sDir
sDir = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
CreateObject("WScript.Shell").Run "pythonw """ & sDir & "\uninstall.py""", 0, False
