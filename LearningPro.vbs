' LearningPro_Admin.vbs — Chạy ứng dụng với quyền Administrator
' Cách dùng: double-click file này thay vì LearningPro.vbs
Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute "cmd.exe", _
    "/c ""D:/ProjectRoot/PythonProject/ung_dung_hoc_tap/LearningPro.cmd""", _
    "D:/ProjectRoot/PythonProject/ung_dung_hoc_tap", _
    "runas", 0
