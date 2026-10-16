@echo off
setlocal
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do (
  taskkill /PID %%a /F >nul 2>nul
)
echo 服务已停止。
exit /b 0
