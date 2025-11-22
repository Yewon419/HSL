#!/bin/bash

echo "========================================="
echo "🚀 주식 트레이딩 시스템 배포 시작"
echo "========================================="
echo ""

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 102 서버 배포 (Backend/Celery)
echo -e "${BLUE}📦 102 서버 배포 중 (Backend/Celery)...${NC}"
ssh yunsang@192.168.219.102 << 'EOF'
  set -e
  cd /opt/stock-trading

  echo "  → Docker 컨테이너 중지..."
  docker compose down

  echo "  → Docker 이미지 빌드 및 시작..."
  docker compose up -d --build

  echo "  → 컨테이너 상태 확인..."
  sleep 10
  docker ps

  echo "✅ 102 서버 배포 완료"
EOF

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ 102 서버 배포 성공${NC}"
else
  echo -e "${RED}❌ 102 서버 배포 실패${NC}"
  exit 1
fi

echo ""

# 101 서버 배포 (Scheduler/Grafana)
echo -e "${BLUE}📦 101 서버 배포 중 (Scheduler/Grafana)...${NC}"
ssh yunsang@192.168.219.101 << 'EOF'
  set -e
  cd /opt/stock-trading

  echo "  → Docker 컨테이너 중지..."
  docker compose down

  echo "  → Docker 이미지 빌드 및 시작..."
  docker compose up -d --build

  echo "  → 컨테이너 상태 확인..."
  sleep 15
  docker ps

  echo "✅ 101 서버 배포 완료"
EOF

if [ $? -eq 0 ]; then
  echo -e "${GREEN}✅ 101 서버 배포 성공${NC}"
else
  echo -e "${RED}❌ 101 서버 배포 실패${NC}"
  exit 1
fi

echo ""
echo "========================================="
echo -e "${GREEN}🎉 배포 완료!${NC}"
echo "========================================="
echo ""
echo "서비스 URL:"
echo "  • Backend API: http://192.168.219.102:8000"
echo "  • Grafana:     http://192.168.219.101:3000"
echo "  • Airflow:     http://192.168.219.101:8080"
echo "========================================="
