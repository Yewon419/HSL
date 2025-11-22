# 최종 배포 정리 (2025-11-10)

## 📋 상황 요약

Airflow 배치 스케줄 변경사항을 **운영서버(101)에서만 실행**하도록 구성했습니다.
개발 PC는 코드 관리 및 배포만 담당합니다.

---

## 🏗️ 시스템 구조

```
개발 PC (/f/hhstock)
├── 역할: 코드 관리, 배포 패키지 유지
├── Docker: ⏹️ Stopped (운영과 분리)
└── 파일 구조:
    ├── stock-trading-system/airflow/dags/ (최신 DAG)
    ├── airflow/dags/ (mirror)
    └── deployment/101_scheduler/ (배포 패키지)
        └── airflow/dags/ (배포용 최신 DAG)

운영서버 101 (192.168.219.101)
├── 역할: Airflow 실행
├── 경로: /home/hansol/stock-trading-system
├── Docker: 🟢 Running (production)
├── Services:
│   ├── Airflow Scheduler (18:30 KST 매일 실행)
│   ├── Airflow Webserver (http://192.168.219.101:8080)
│   ├── Grafana (http://192.168.219.101:3000)
│   ├── Backend (http://192.168.219.101:8000)
│   └── 기타 서비스들
└── DB: 운영 DB (192.168.219.103:5432)
```

---

## ✅ 완료된 작업

### 1️⃣ 배치 스케줄 변경

**daily_collection_dag**
- 스케줄: 09:30 UTC = 18:30 KST (오후 6시 30분)
- 평일만 실행 (월-금)

**technical_indicator_dag**
- 독립 스케줄 제거
- daily_collection_dag 완료 후 자동 실행 (ExternalTaskSensor)

### 2️⃣ 운영 환경 분리

**개발 PC**
```bash
docker-compose down  # ✅ 완료
# 이제 Docker Compose가 실행되지 않음
```

**운영서버 101**
```bash
# 배포 준비 완료
cd /home/hansol/stock-trading-system
bash ~/deploy.sh
```

### 3️⃣ 배포 패키지 준비

```
deployment/101_scheduler/
├── airflow/dags/
│   ├── daily_collection_dag.py (18:30 KST)
│   ├── technical_indicator_dag.py (의존성)
│   └── common_functions.py
├── docker-compose.yml (pykrx 추가)
├── docker-compose.prod.yml
├── deploy.sh (자동 배포)
├── DEPLOYMENT_GUIDE_20251110.md
└── README.md
```

---

## 🚀 배포 프로세스

### 상황 1: 개발 PC에서 운영서버로 배포

```bash
# 1. 개발 PC에서 변경사항 commit & push
cd /f/hhstock
git add deployment/101_scheduler/airflow/dags/
git commit -m "feat: update DAG files"
git push

# 2. 운영서버에 변경사항 배포
# 방법 A: 직접 배포 스크립트 실행
ssh hansol@192.168.219.101
bash ~/deploy.sh

# 방법 B: SCP로 직접 복사
scp /f/hhstock/deployment/101_scheduler/airflow/dags/* \
    hansol@192.168.219.101:/home/hansol/stock-trading-system/airflow/dags/

docker restart stock-airflow-scheduler
```

### 상황 2: 로컬에서 Airflow 테스트 필요 시

```bash
# 개발 PC에서만 테스트
cd /f/hhstock
docker-compose up -d

# 테스트 완료 후 중지 (운영에 영향 없음)
docker-compose down
```

---

## 📝 현재 설정값

### Airflow 스케줄

| DAG | 시간 | UTC | 설명 |
|-----|------|-----|------|
| daily_collection_dag | 18:30 KST | 09:30 UTC | 주가/지수 수집 |
| technical_indicator_dag | - | - | daily_collection_dag 완료 후 |

### 환경 변수

**운영서버 (docker-compose.prod.yml)**
```bash
ENVIRONMENT=production
DB_HOST=postgres (또는 192.168.219.103)
_PIP_ADDITIONAL_REQUIREMENTS: 'pandas sqlalchemy psycopg2-binary requests beautifulsoup4 pykrx'
```

---

## ⚠️ 주의사항

### 1. 개발 PC와 운영서버 동시 실행 금지

❌ **하지 말 것**:
```bash
# 개발 PC에서 docker-compose up 실행하면 안됨
cd /f/hhstock
docker-compose up -d  # 운영서버와 겹칠 수 있음
```

✅ **올바른 방법**:
```bash
# 운영서버에서만 실행
ssh hansol@192.168.219.101
docker-compose up -d
```

### 2. 배포 전 항상 운영서버 백업

```bash
# 운영서버에서
cd /home/hansol/stock-trading-system
mkdir -p backups/backup_$(date +%Y%m%d_%H%M%S)
cp docker-compose.yml backups/backup_*/
cp .env backups/backup_*/
cp -r airflow/dags backups/backup_*/
```

### 3. DAG 파일 동기화

개발 PC의 DAG 파일을 수정한 후:
1. 운영서버의 deployment/101_scheduler/ 에 복사
2. 운영서버에 배포

```bash
# 개발 PC에서
cp stock-trading-system/airflow/dags/*.py \
   deployment/101_scheduler/airflow/dags/

# 운영서버에 배포
scp -r deployment/101_scheduler/airflow/dags/* \
     hansol@192.168.219.101:/home/hansol/stock-trading-system/airflow/dags/
```

---

## 🔗 관련 문서

- **deployment/101_scheduler/DEPLOYMENT_GUIDE_20251110.md** - 상세 배포 가이드
- **deployment/101_scheduler/README.md** - 패키지 사용 설명서
- **WORK_PROGRESS_20251110.md** - 변경사항 상세
- **start_hsl.md** - 전체 운영 가이드

---

## 📞 문제 해결

### 문제 1: 개발 PC에서 Airflow 접속 불가

**원인**: 개발 PC의 Docker Compose가 중지됨
**해결**: 운영서버 101에 접속
```bash
http://192.168.219.101:8080
```

### 문제 2: 운영서버 DAG가 로드되지 않음

**원인**: deployment/101_scheduler 의 DAG가 동기화되지 않음
**해결**:
```bash
# 개발 PC에서
cp stock-trading-system/airflow/dags/*.py \
   deployment/101_scheduler/airflow/dags/

# 운영서버에 배포
scp -r deployment/101_scheduler/airflow/dags/* \
     hansol@192.168.219.101:~/deploy_temp/airflow/dags/

# 운영서버에서
cd /home/hansol/stock-trading-system
docker-compose restart stock-airflow-scheduler
```

### 문제 3: 배치가 실행되지 않음

**확인**:
```bash
# 운영서버에서
docker exec stock-airflow-scheduler airflow dags list
docker exec stock-airflow-scheduler airflow dags next-execution daily_collection_dag
docker-compose logs -f stock-airflow-scheduler
```

---

## 체크리스트

배포 후 확인:

- [ ] 개발 PC Docker Compose 중지됨 (docker ps 에서 stock- 컨테이너 없음)
- [ ] 운영서버 101 에서 Airflow 실행 중
  - Webserver: http://192.168.219.101:8080
  - Scheduler: docker ps | grep scheduler
- [ ] DAG 로드됨
  - docker exec stock-airflow-scheduler airflow dags list
- [ ] 다음 실행 시간 확인
  - docker exec stock-airflow-scheduler airflow dags next-execution daily_collection_dag
- [ ] 로그 확인
  - docker-compose logs -f stock-airflow-scheduler | grep "daily_collection_dag\|technical_indicator_dag"

---

**작성자**: Claude Code
**작성 일시**: 2025-11-10
**상태**: ✅ 배포 준비 완료
