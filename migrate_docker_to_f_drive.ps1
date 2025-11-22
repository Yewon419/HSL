# Docker 데이터를 F드라이브로 완전 마이그레이션 스크립트
# 작성: 2025-10-27

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Docker 데이터 F드라이브 마이그레이션" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Docker Compose 중지
Write-Host "`n[Step 1] Docker Compose 중지 중..." -ForegroundColor Yellow
cd "F:\hhstock\stock-trading-system"
docker-compose down
Start-Sleep -Seconds 5

# 2. F드라이브에 데이터 디렉토리 생성
Write-Host "`n[Step 2] F드라이브 데이터 디렉토리 생성 중..." -ForegroundColor Yellow
$dataDirs = @(
    "F:\docker-data\postgres",
    "F:\docker-data\influxdb",
    "F:\docker-data\grafana",
    "F:\docker-data\airflow-logs",
    "F:\docker-data\airflow-plugins"
)

foreach ($dir in $dataDirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  ✓ 생성됨: $dir" -ForegroundColor Green
    } else {
        Write-Host "  ✓ 이미 존재: $dir" -ForegroundColor Green
    }
}

# 3. docker-compose.yml 수정
Write-Host "`n[Step 3] docker-compose.yml 수정 중..." -ForegroundColor Yellow

$composePath = "F:\hhstock\stock-trading-system\docker-compose.yml"
$composeContent = Get-Content -Path $composePath -Raw

# 볼륨 섹션 수정
$oldVolumes = @"
volumes:
  postgres_data:
  influxdb_data:
  grafana_data:
"@

$newVolumes = @"
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: F:\docker-data\postgres
  influxdb_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: F:\docker-data\influxdb
  grafana_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: F:\docker-data\grafana
"@

$composeContent = $composeContent -replace [regex]::Escape($oldVolumes), $newVolumes

# airflow 볼륨 수정 (상대 경로에서 절대 경로로)
$composeContent = $composeContent -replace './airflow/logs:/opt/airflow/logs', 'F:\docker-data\airflow-logs:/opt/airflow/logs'
$composeContent = $composeContent -replace './airflow/plugins:/opt/airflow/plugins', 'F:\docker-data\airflow-plugins:/opt/airflow/plugins'

Set-Content -Path $composePath -Value $composeContent
Write-Host "  ✓ docker-compose.yml 수정 완료" -ForegroundColor Green

# 4. .env.development 확인
Write-Host "`n[Step 4] 환경 설정 확인 중..." -ForegroundColor Yellow
if (Test-Path "F:\hhstock\.env.development") {
    Write-Host "  ✓ .env.development 파일 존재" -ForegroundColor Green
} else {
    Write-Host "  ⚠ .env.development 파일 미존재 (이전 단계에서 생성됨)" -ForegroundColor Yellow
}

# 5. Docker Compose 재시작
Write-Host "`n[Step 5] Docker Compose 시작 중..." -ForegroundColor Yellow
docker-compose up -d
Start-Sleep -Seconds 30

# 6. 상태 확인
Write-Host "`n[Step 6] Docker 컨테이너 상태 확인 중..." -ForegroundColor Yellow
docker ps --format "table {{.Names}}\t{{.Status}}"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "마이그레이션 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`n📊 데이터 저장 위치:" -ForegroundColor Cyan
Write-Host "  - PostgreSQL: F:\docker-data\postgres" -ForegroundColor White
Write-Host "  - InfluxDB: F:\docker-data\influxdb" -ForegroundColor White
Write-Host "  - Grafana: F:\docker-data\grafana" -ForegroundColor White
Write-Host "  - Airflow Logs: F:\docker-data\airflow-logs" -ForegroundColor White
Write-Host "  - Airflow Plugins: F:\docker-data\airflow-plugins" -ForegroundColor White
