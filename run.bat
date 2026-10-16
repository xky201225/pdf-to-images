@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if %errorlevel% neq 0 (
  echo 未找到 Python，请先安装 Python 3.9 或更高版本。
  pause
  exit /b 1
)

if not exist "%~dp0lib\pypdfium2" (
  echo 正在安装依赖 pypdfium2 ...
  python -m pip install -r requirements.txt
)

start "" http://127.0.0.1:8765
python app.py
pause
