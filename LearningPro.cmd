@echo off
setlocal
cd /d "D:/ProjectRoot/PythonProject/ung_dung_hoc_tap"
set "PYTHONUNBUFFERED=1"
set "PYTHONDONTWRITEBYTECODE=1"
set "PYTHONHOME="
set "PYTHONPATH="
set "PATH=D:/ProjectRoot/PythonProject/ung_dung_hoc_tap\.venv\Scripts;%PATH%"
set "VIRTUAL_ENV=D:/ProjectRoot/PythonProject/ung_dung_hoc_tap\.venv"
D:/ProjectRoot/PythonProject/ung_dung_hoc_tap\.venv\Scripts\python.exe -u D:/ProjectRoot/PythonProject/ung_dung_hoc_tap/main.py
endlocal
