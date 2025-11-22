# Claude를 위한 배포 가이드

> **중요**: 이 문서는 Claude가 자동으로 배포를 수행할 때 참조하는 표준 문서입니다.
> 서버 환경이 변경되면 이 문서를 반드시 업데이트하세요.

## 📋 서버 환경 정보

### 서버 구성
| 서버 | IP | 역할 | OS | SSH 사용자 |
|------|-----|------|-----|-----------|
| 102번 서버 | 192.168.219.102 | Backend, Celery | Rocky Linux 9.6 | yunsang |
| 101번 서버 | 192.168.219.101 | Scheduler, Grafana | Rocky Linux 9.6 | yunsang |

### 배포 경로
```bash
# 두 서버 모두 동일한 경로 사용
/opt/stock-trading/
```

### 중요: Git 저장소가 아님
서버의 `/opt/stock-trading/` 디렉토리는 **Git 저장소가 아닙니다**.
- `git pull` 같은 Git 명령어 사용 불가
- 파일 직접 수정 후 Docker 재빌드 방식으로 배포

---

## 🚀 배포 방법

### 1. 로컬에서 스크립트로 배포 (권장)

#### Windows (PowerShell)
```powershell
.\deploy.ps1
```

#### Linux/Mac (Bash)
```bash
./deploy.sh
```

### 2. Claude가 직접 배포 (수동 배포)

Claude가 배포할 때는 다음 단계를 따르세요:

#### Step 1: 102번 서버 배포 (Backend/Celery)

```bash
# 1. SSH 접속 및 컨테이너 중지
ssh yunsang@192.168.219.102 "cd /opt/stock-trading && docker compose down"

# 2. 필요시 파일 직접 수정 (예: Dockerfile)
ssh yunsang@192.168.219.102 "sed -i 's|OLD_CONTENT|NEW_CONTENT|' /opt/stock-trading/PATH/TO/FILE"

# 3. Docker 컨테이너 재빌드 및 시작
ssh yunsang@192.168.219.102 "cd /opt/stock-trading && docker compose up -d --build"

# 4. 컨테이너 상태 확인
ssh yunsang@192.168.219.102 "sleep 10 && docker ps"
```

#### Step 2: 101번 서버 배포 (Scheduler/Grafana)

```bash
# 1. SSH 접속 및 컨테이너 중지
ssh yunsang@192.168.219.101 "cd /opt/stock-trading && docker compose down"

# 2. 필요시 파일 직접 수정
ssh yunsang@192.168.219.101 "sed -i 's|OLD_CONTENT|NEW_CONTENT|' /opt/stock-trading/PATH/TO/FILE"

# 3. Docker 컨테이너 재빌드 및 시작
ssh yunsang@192.168.219.101 "cd /opt/stock-trading && docker compose up -d --build"

# 4. 컨테이너 상태 확인
ssh yunsang@192.168.219.101 "sleep 15 && docker ps"
```

---

## 📁 서버 디렉토리 구조

```
/opt/stock-trading/
├── backend/
│   ├── Dockerfile              # Backend Docker 설정
│   ├── requirements.txt        # Python 패키지
│   ├── main.py                 # FastAPI 메인
│   ├── celery_app.py          # Celery 설정
│   └── frontend/              # ⭐ 최신 프론트엔드 (6개 탭)
│       ├── index.html
│       ├── app.js
│       ├── screening.html
│       ├── rsi_ma_strategy.html
│       └── ...
├── frontend/                   # ⚠️ 구버전 (사용 안 함)
├── docker-compose.yml
└── nginx/
    └── nginx.conf
```

### ⚠️ 중요: Frontend 경로

Dockerfile에서 반드시 **`backend/frontend/`**를 복사해야 합니다:

```dockerfile
# ✅ 올바른 경로
COPY backend/frontend/ /app/frontend

# ❌ 잘못된 경로 (구버전)
COPY frontend/ /app/frontend
```

---

## 🐳 Docker 명령어

### 컨테이너 관리
```bash
# 컨테이너 중지
docker compose down

# 컨테이너 시작 (재빌드)
docker compose up -d --build

# 컨테이너 상태 확인
docker ps

# 특정 컨테이너 로그 확인
docker logs stock-backend
docker logs stock-celery-worker
docker logs stock-celery-beat
docker logs stock-nginx-backend
```

### 컨테이너 내부 접근
```bash
# Backend 컨테이너 접속
docker exec -it stock-backend bash

# 파일 확인
docker exec stock-backend ls -la /app/frontend/
```

---

## 🔍 배포 후 확인 사항

### 1. 컨테이너 상태 확인
```bash
ssh yunsang@192.168.219.102 "docker ps"
```

예상 출력:
```
NAMES                 STATUS                     PORTS
stock-backend         Up X minutes (healthy)     0.0.0.0:8000->8000/tcp
stock-nginx-backend   Up X minutes               0.0.0.0:8080->80/tcp, 0.0.0.0:443->443/tcp
stock-celery-worker   Up X minutes
stock-celery-beat     Up X minutes
```

### 2. 서비스 접근 테스트
```bash
# Backend API (8000 포트)
curl -I http://192.168.219.102:8000/static/index.html

# Nginx Proxy (8080 포트)
curl -I http://192.168.219.102:8080/

# 주요 HTML 파일 확인
curl -I http://192.168.219.102:8000/static/screening.html
curl -I http://192.168.219.102:8000/static/rsi_ma_strategy.html
```

### 3. Frontend 탭 확인
브라우저에서 http://192.168.219.102:8000 접속 후 다음 6개 탭이 모두 있는지 확인:
1. 📊 차트 분석
2. 📈 지표 분석
3. 🎯 신호 분석
4. 🤖 AI 추천
5. 🔍 스크리닝 & 백테스팅
6. 📊 RSI+MA 전략

### 4. 백엔드 로그 확인
```bash
ssh yunsang@192.168.219.102 "docker logs --tail 50 stock-backend"
```

---

## 🚨 트러블슈팅

### 문제 1: Frontend 탭이 보이지 않음

**원인**: Dockerfile이 잘못된 frontend 경로를 복사
```bash
# 확인
ssh yunsang@192.168.219.102 "docker exec stock-backend ls -la /app/frontend/"

# screening.html, rsi_ma_strategy.html이 없으면 Dockerfile 수정 필요
ssh yunsang@192.168.219.102 "sed -i 's|COPY frontend/ /app/frontend|COPY backend/frontend/ /app/frontend|' /opt/stock-trading/backend/Dockerfile"

# 재빌드
ssh yunsang@192.168.219.102 "cd /opt/stock-trading && docker compose down && docker compose up -d --build"
```

### 문제 2: 컨테이너가 unhealthy 상태

**확인 방법**:
```bash
# 로그 확인
ssh yunsang@192.168.219.102 "docker logs stock-backend"

# Health check 확인
ssh yunsang@192.168.219.102 "docker inspect stock-backend | grep -A 10 Health"
```

**참고**: "unhealthy" 상태여도 실제로 요청은 정상 처리될 수 있음. 로그와 실제 동작을 확인하세요.

### 문제 3: 포트 접속 안 됨

```bash
# 포트 리스닝 확인
ssh yunsang@192.168.219.102 "netstat -tlnp | grep -E '8000|8080'"

# 방화벽 확인
ssh yunsang@192.168.219.102 "sudo firewall-cmd --list-ports"
```

### 문제 4: Docker Compose 명령어 오류

```bash
# "docker-compose: command not found" 오류 시
# Docker Compose V2 사용 (docker compose, 하이픈 없음)
docker compose up -d

# Docker Compose V1 (docker-compose, 하이픈 있음)
docker-compose up -d
```

---

## 📝 배포 체크리스트

배포 전:
- [ ] 로컬에서 테스트 완료
- [ ] Git에 커밋 및 푸시 완료
- [ ] 변경 사항 확인 (Dockerfile, requirements.txt 등)

배포 중:
- [ ] 102번 서버 컨테이너 중지
- [ ] 102번 서버 파일 수정 (필요시)
- [ ] 102번 서버 컨테이너 재빌드
- [ ] 102번 서버 상태 확인
- [ ] 101번 서버 컨테이너 중지
- [ ] 101번 서버 파일 수정 (필요시)
- [ ] 101번 서버 컨테이너 재빌드
- [ ] 101번 서버 상태 확인

배포 후:
- [ ] Frontend 모든 탭 확인
- [ ] API 엔드포인트 테스트
- [ ] 로그 확인 (오류 없는지)
- [ ] Celery 작업 실행 확인

---

## 🌐 서비스 URL

배포 완료 후 접속 가능한 URL:

| 서비스 | URL | 설명 |
|--------|-----|------|
| Backend API | http://192.168.219.102:8000 | FastAPI 백엔드 |
| Nginx Proxy | http://192.168.219.102:8080 | Nginx 프록시 |
| API Docs | http://192.168.219.102:8000/docs | Swagger UI |
| Grafana | http://192.168.219.101:3000 | 모니터링 대시보드 |
| Airflow | http://192.168.219.101:8080 | 워크플로우 관리 |

---

## 📌 주의사항

1. **Git 명령어 사용 불가**: 서버는 Git 저장소가 아니므로 `git pull` 사용 불가
2. **직접 수정 후 재빌드**: 파일 수정은 SSH로 직접 하고 Docker 재빌드
3. **Frontend 경로**: 반드시 `backend/frontend/` 사용
4. **Docker Compose V2**: `docker compose` (하이픈 없음) 사용
5. **SSH 사용자**: 두 서버 모두 `yunsang` 사용
6. **배포 경로**: 두 서버 모두 `/opt/stock-trading/` 사용

---

**마지막 업데이트**: 2025-10-09
**작성자**: AI Assistant (Claude)
