# 주식 트레이딩 시스템 배포 스크립트 (PowerShell)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "🚀 주식 트레이딩 시스템 배포 시작" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 102 서버 배포 (Backend/Celery)
Write-Host "📦 102 서버 배포 중 (Backend/Celery)..." -ForegroundColor Blue

ssh yunsang@192.168.219.102 "cd /opt/stock-trading && docker compose down && docker compose up -d --build && sleep 10 && docker ps"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 102 서버 배포 성공" -ForegroundColor Green
} else {
    Write-Host "❌ 102 서버 배포 실패" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 101 서버 배포 (Scheduler/Grafana)
Write-Host "📦 101 서버 배포 중 (Scheduler/Grafana)..." -ForegroundColor Blue

ssh yunsang@192.168.219.101 "cd /opt/stock-trading && docker compose down && docker compose up -d --build && sleep 15 && docker ps"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ 101 서버 배포 성공" -ForegroundColor Green
} else {
    Write-Host "❌ 101 서버 배포 실패" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "🎉 배포 완료!" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "서비스 URL:"
Write-Host "  • Backend API: http://192.168.219.102:8000"
Write-Host "  • Grafana:     http://192.168.219.101:3000"
Write-Host "  • Airflow:     http://192.168.219.101:8080"
Write-Host "=========================================" -ForegroundColor Cyan
