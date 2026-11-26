@echo off
chcp 65001 >nul
echo ========================================================
echo   Muse Animation Studio - Local Codex + Docker Compose
echo ========================================================

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8765 ^| findstr LISTENING') do (
    echo Dang giai phong cong 8765 tu tien trinh %%a...
    taskkill /F /PID %%a >nul 2>&1
)

echo [1/2] Khoi dong Muse2API Gateway trong Docker...
docker compose up -d muse2api
if %errorlevel% neq 0 (
    echo [LOI] Khong the khoi dong Docker container muse2api.
    pause
    exit /b %errorlevel%
)
echo [2/2] Khoi chay Web Studio voi Codex tren may ca nhan...
uv run python -m animation_studio.cli.main web --open-browser
