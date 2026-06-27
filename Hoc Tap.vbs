Set objShell = CreateObject("WScript.Shell")
objShell.Run "cmd /c cd /d """ & CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName) & """ && uv run python main.py", 0, False
