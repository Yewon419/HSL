# Airflow DAG System Deployment Checklist

**최종 배포 체크리스트**
**작성일**: 2025-10-20
**상태**: 준비 완료

---

## ✅ 구현 완료 항목

### 1. 데이터베이스 레이어
- [x] `collection_log` 테이블 생성
  - 위치: stocktrading DB
  - 컬럼: collection_date, price_status, indices_status, overall_status 등
  - 인덱스: idx_collection_log_date, idx_collection_log_status

- [x] `indicator_log` 테이블 생성
  - 위치: stocktrading DB
  - 컬럼: indicator_date, status, retry_count 등
  - 인덱스: idx_indicator_log_date, idx_indicator_log_status

### 2. 소프트웨어 레이어

#### 공통 함수 라이브러리
- [x] `common_functions.py` 확장
  - 데이터베이스 연결 함수 (기존)
  - 데이터 수집 함수 (기존)
  - 데이터 저장 함수 (기존)
  - **신규**: 상태 추적 함수 (collection_log, indicator_log)
  - **신규**: 지표 관리 함수

#### DAG 파일
- [x] `generate_daily_collection_dag.py` (신규)
  - 크기: 3.4K
  - Task: generate_daily_collection
  - 스케줄: 0 16 * * 1-5

- [x] `daily_collection_dag.py` (신규)
  - 크기: 8.9K
  - Task: check_and_decide, price_collection, indices_collection
  - 스케줄: 0 16-23 * * 1-5
  - 기능: 시간 기반 수집, 자동 재시도

- [x] `technical_indicator_dag.py` (신규)
  - 크기: 9.2K
  - Task: check_indicator_readiness, calculate_indicators
  - 스케줄: 0 18-23 * * 1-5
  - 기능: 수집 완료 확인 후 지표 계산

- [x] `manual_collection_dag.py` (기존)
  - 크기: 6.0K
  - Task: fetch_stock_prices, fetch_market_indices, save_to_database
  - 스케줄: 없음 (수동 트리거)

### 3. 문서
- [x] `docs/AIRFLOW_COMPLETE_DESIGN.md` - 완전한 시스템 설계 문서
- [x] `IMPLEMENTATION_SUMMARY.md` - 구현 완료 요약
- [x] `DEPLOYMENT_CHECKLIST.md` - 이 파일

---

## 🚀 배포 절차

### 단계 1: 사전 확인

**체크리스트**:
- [ ] Git 상태 확인
  ```bash
  cd F:/hhstock
  git status
  ```

- [ ] Docker 컨테이너 확인
  ```bash
  docker ps
  docker-compose ps
  ```

- [ ] 데이터베이스 연결 확인
  ```bash
  docker exec stock-db psql -U admin -d stocktrading -c "SELECT 1"
  ```

### 단계 2: 기존 Airflow 정리

```bash
# 1. Airflow 컨테이너 중지
docker-compose down

# 2. DAG 디렉토리 정리 (선택사항 - 백업 파일 정리)
cd stock-trading-system/airflow/dags/
rm -f daily_collection_dag_old.py technical_indicator_dag_old.py
```

### 단계 3: Airflow 서비스 시작

```bash
# 1. docker-compose.yml 위치로 이동
cd F:/hhstock

# 2. 서비스 시작
docker-compose up -d

# 3. Airflow 초기화 대기 (2-3분)
sleep 180

# 4. 로그 확인
docker-compose logs airflow-scheduler | head -50
```

### 단계 4: DAG 로드 확인

```bash
# 1. DAG 목록 확인
docker exec airflow-scheduler airflow dags list

# 예상 결과:
# dag_id                          | owner       | paused
# --------------------------------|-------------|--------
# daily_collection_dag            | stock-sys   | True
# generate_daily_collection_dag   | stock-sys   | True
# manual_collection_dag           | stock-sys   | True
# technical_indicator_dag         | stock-sys   | True

# 2. 특정 DAG 세부 정보 확인
docker exec airflow-scheduler airflow dags show generate_daily_collection_dag
```

### 단계 5: DAG 활성화

```bash
# Airflow UI에서 활성화:
# 1. http://localhost:8080 접속
# 2. 좌측 메뉴에서 "DAGs" 클릭
# 3. 각 DAG의 슬라이더를 OFF → ON으로 변경
#    - generate_daily_collection_dag
#    - daily_collection_dag
#    - technical_indicator_dag
#    - manual_collection_dag

# 또는 CLI에서:
docker exec airflow-scheduler airflow dags unpause generate_daily_collection_dag
docker exec airflow-scheduler airflow dags unpause daily_collection_dag
docker exec airflow-scheduler airflow dags unpause technical_indicator_dag
docker exec airflow-scheduler airflow dags unpause manual_collection_dag
```

### 단계 6: 초기 수집 테스트

#### Option A: 수동 트리거로 테스트

```bash
# 1. manual_collection_dag 실행 (2025-10-20 데이터 수집)
docker exec airflow-scheduler airflow dags test manual_collection_dag 2025-10-20

# 2. Airflow UI에서 결과 확인
#    → DAGs > manual_collection_dag > Graph
```

#### Option B: 자동 실행 대기

```bash
# 다음 스케줄 시간에 자동 실행:
# 16:00 - generate_daily_collection_dag 실행
# 17:00 - daily_collection_dag 실행
# 18:00 - technical_indicator_dag 실행
```

### 단계 7: 데이터 검증

```bash
# 수집 상태 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT collection_date, overall_status, price_count, indices_count
FROM collection_log
ORDER BY collection_date DESC
LIMIT 5;
"

# 지표 상태 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT indicator_date, status, indicators_count, retry_count
FROM indicator_log
ORDER BY indicator_date DESC
LIMIT 5;
"
```

---

## 🔍 모니터링 및 문제 해결

### 로그 확인

```bash
# 실시간 로그 모니터링
docker-compose logs -f airflow-scheduler

# 특정 DAG 로그
docker exec airflow-scheduler airflow dags list -o plain | grep "daily_collection_dag"
```

### 공통 문제 및 해결

| 문제 | 원인 | 해결 방법 |
|------|------|---------|
| DAG이 보이지 않음 | 파일이 없거나 문법 오류 | `docker-compose logs` 확인, DAG 파일 문법 검증 |
| Task가 실행 안됨 | DAG이 paused 상태 | Airflow UI에서 DAG 활성화 |
| 수집 실패 | pykrx API 에러 | 수동으로 재시도 또는 다음 시간 자동 재시도 대기 |
| DB 연결 오류 | 데이터베이스 서비스 중단 | `docker exec stock-db psql ...` 로 DB 연결 테스트 |

### 성능 모니터링

```bash
# Airflow 메트릭
docker exec airflow-scheduler airflow dags list -o json | jq '.'

# 데이터베이스 쿼리 시간
time docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-20'
"
```

---

## 📋 운영 가이드

### 일일 점검

**매일 오전 2시 (UTC 17:00 이후)**
```bash
# 1. 수집 상태 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT * FROM collection_log WHERE collection_date = CURRENT_DATE;
"

# 2. 실패가 있으면 Airflow UI에서 확인
# DAGs > daily_collection_dag > Graph > 실패한 Task 클릭

# 3. 수동 재시도가 필요하면
docker exec airflow-scheduler airflow dags test daily_collection_dag 2025-10-20
```

### 주간 점검

**매주 월요일**
```bash
# 1. DAG 실행 통계
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
  DATE(collection_date) as date,
  COUNT(*) as total_runs,
  SUM(CASE WHEN overall_status='success' THEN 1 ELSE 0 END) as success,
  SUM(CASE WHEN overall_status='failed' THEN 1 ELSE 0 END) as failed
FROM collection_log
WHERE collection_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(collection_date)
ORDER BY date DESC;
"

# 2. 수집 데이터 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
  DATE(date) as date,
  COUNT(DISTINCT ticker) as ticker_count,
  COUNT(*) as total_records
FROM stock_prices
WHERE date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(date)
ORDER BY date DESC;
"
```

### 월간 유지보수

**매월 1일**
```bash
# 1. 로그 테이블 정리 (선택사항)
docker exec stock-db psql -U admin -d stocktrading -c "
DELETE FROM collection_log
WHERE collection_date < CURRENT_DATE - INTERVAL '90 days';
"

# 2. 인덱스 상태 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT * FROM pg_stat_user_indexes WHERE tablename IN ('collection_log', 'indicator_log');
"

# 3. 백업 수행 (별도 스크립트)
# backup.sh 실행
```

---

## ✨ 주요 특징 재확인

### 자동 재시도 메커니즘
- ✅ 최대 3회 자동 재시도
- ✅ 매시간 DAG 실행으로 자동 복구
- ✅ `collection_log`, `indicator_log` 에 상태 기록

### 시간 기반 조건부 실행
- ✅ 16:00: 준비 (collection_log 생성)
- ✅ 17:00: 수집 시작
- ✅ 18:00: 지표 계산 시작
- ✅ 매시간 재시도

### 의존성 관리
- ✅ `daily_collection_dag` → 독립적
- ✅ `technical_indicator_dag` → `daily_collection_dag` 상태 확인
- ✅ `manual_collection_dag` → 수동 트리거

---

## 📞 연락처 및 지원

### 긴급 문제
1. Docker 로그 확인: `docker-compose logs`
2. DAG 파일 문법: `python -m py_compile <file>.py`
3. DB 연결: `docker exec stock-db psql -U admin -d stocktrading -c "SELECT 1"`

### 참고 문서
- `docs/AIRFLOW_COMPLETE_DESIGN.md` - 전체 설계
- `IMPLEMENTATION_SUMMARY.md` - 구현 요약
- Airflow 공식 문서: https://airflow.apache.org/docs/

---

**배포 준비 상태**: ✅ 완료
**마지막 업데이트**: 2025-10-20 20:35 UTC
**다음 단계**: Docker 환경에서 `docker-compose up -d` 실행
