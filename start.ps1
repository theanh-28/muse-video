# Khởi chạy Muse Animation Studio với Local Codex + Docker Compose
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Muse Animation Studio - Local Codex + Docker Compose" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Dọn dẹp tiến trình cũ nếu cổng 8765 đang bị chiếm
$oldConn = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($oldConn) {
    Write-Host "Đang giải phóng cổng 8765 từ tiến trình cũ ($($oldConn.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $oldConn.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
}

Write-Host "`n[1/2] Đang kiểm tra Muse2API Gateway trong Docker..." -ForegroundColor Yellow
docker compose up -d muse2api
if ($LASTEXITCODE -ne 0) {
    Write-Error "Không thể khởi động container muse2api trong Docker."
    exit $LASTEXITCODE
}

Write-Host "`n[2/2] Đang khởi chạy Web Studio với Codex trên máy cá nhân..." -ForegroundColor Green
uv run python -m animation_studio.cli.main web --open-browser
