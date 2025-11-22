# Airflow DAG System Implementation Summary

**완료일**: 2025-10-20
**상태**: ✅ 완료

---

## 📋 구현 내용

새로운 Airflow DAG 시스템이 완전히 구현되고 배포될 준비가 되었습니다.

### 1. 데이터베이스 테이블 (✅ 생성됨)

#### collection_log (수집 상태 추적)
```sql
CREATE TABLE collection_log (
  id SERIAL PRIMARY KEY,
  collection_date DATE NOT NULL UNIQUE,
  price_status VARCHAR(20) DEFAULT 'pending',
  price_count INTEGER,
  price_last_error TEXT,
  price_completed_at TIMESTAMP,
  price_retry_count INTEGER DEFAULT 0,
  indices_status VARCHAR(20) DEFAULT 'pending',
  indices_count INTEGER,
  indices_last_error TEXT,
  indices_completed_at TIMESTAMP,
  indices_retry_count INTEGER DEFAULT 0,
  overall_status VARCHAR(20) DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

#### indicator_log (지표 계산 상태 추적)
```sql
CREATE TABLE indicator_log (
  id SERIAL PRIMARY KEY,
  indicator_date DATE NOT NULL UNIQUE,
  status VARCHAR(20) DEFAULT 'pending',
  indicators_count INTEGER,
  last_error TEXT,
  completed_at TIMESTAMP,
  retry_count INTEGER DEFAULT 0,
  required_prices_count INTEGER,
  collected_prices_count INTEGER,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. 공통 함수 라이브러리 (✅ 생성됨)

**파일**: `stock-trading-system/airflow/dags/common_functions.py`

#### 데이터베이스 연결
- `get_db_engine()` - PostgreSQL 엔진 생성
- `get_database_url()` - 데이터베이스 URL 생성

#### 데이터 수집
- `fetch_stock_prices_api(target_date)` - pykrx에서 주가 수집
- `fetch_market_indices_api(target_date)` - pykrx에서 지수 수집

#### 데이터 저장
- `save_stock_prices(prices_df, target_date, engine)` - 주가 DB 저장
- `save_market_indices(indices_df, target_date, engine)` - 지수 DB 저장

#### 상태 추적 (신규)
- `update_collection_log_price(target_date, status, count, error, engine)` - 주가 수집 상태 업데이트
- `update_collection_log_indices(target_date, status, count, error, engine)` - 지수 수집 상태 업데이트
- `get_collection_status(target_date, engine)` - 수집 상태 조회
- `update_indicator_log(target_date, status, count, error, engine)` - 지표 상태 업데이트
- `get_indicator_status(target_date, engine)` - 지표 상태 조회

#### 기술 지표 계산
- `calculate_rsi(prices, period)` - RSI 계산
- `calculate_macd(prices, fast, slow, signal)` - MACD 계산
- `calculate_sma(prices, period)` - SMA 계산
- `calculate_bollinger_bands(prices, period, std_dev)` - Bollinger Bands 계산
- `save_technical_indicators(indicators_list, engine)` - 지표 DB 저장

### 3. DAG 구현 (✅ 4개 DAG 생성됨)

#### DAG 1: generate_daily_collection_dag
**파일**: `stock-trading-system/airflow/dags/generate_daily_collection_dag.py`

- **목적**: 매일 16:00 UTC에 collection_log에 오늘 날짜 엔트리 생성
- **스케줄**: `0 16 * * 1-5` (매일 16시, 평일만)
- **Task**:
  - `generate_daily_collection` - collection_log 엔트리 생성

#### DAG 2: daily_collection_dag
**파일**: `stock-trading-system/airflow/dags/daily_collection_dag.py`

- **목적**: 16:00~23:00 UTC 매시간 실행, 17:00 이후부터 주가/지수 수집
- **스케줄**: `0 16-23 * * 1-5` (매시간, 평일만)
- **로직**:
  - 16:00~16:59: 스킵
  - 17:00 이후: collection_log 확인 → 수집/재시도/스킵
  - 최대 재시도: 3회
- **Task Groups**:
  - `check_and_decide` - 수집 여부 결정
  - `price_collection` - 주가 수집/저장
  - `indices_collection` - 지수 수집/저장

#### DAG 3: technical_indicator_dag
**파일**: `stock-trading-system/airflow/dags/technical_indicator_dag.py`

- **목적**: 18:00~23:00 UTC 매시간 실행, 수집 완료 후 지표 계산
- **스케줄**: `0 18-23 * * 1-5` (매시간, 평일만)
- **로직**:
  - 18:00 이전: 스킵
  - 18:00 이후: collection_log 확인 → overall_status='success' 확인 → 지표 계산
  - 최대 재시도: 3회
- **Tasks**:
  - `check_indicator_readiness` - 지표 계산 준비 상태 확인
  - `calculate_indicators` - RSI, MACD, SMA, Bollinger Bands 등 계산

#### DAG 4: manual_collection_dag
**파일**: `stock-trading-system/airflow/dags/manual_collection_dag.py`

- **목적**: 수동 트리거로 특정 날짜의 데이터 수집/계산
- **스케줄**: 없음 (수동만)
- **execution_date**: 수집 대상 날짜 지정
- **Tasks**:
  - `fetch_stock_prices` - 주가 수집
  - `fetch_market_indices` - 지수 수집
  - `save_to_database` - DB 저장

---

## 🔄 실행 흐름

### 정상 시나리오 (2025-10-20)

```
16:00 UTC (오전 1시)
  ↓
generate_daily_collection_dag 실행
  → collection_log INSERT (collection_date=2025-10-20, overall_status=pending)

16:00~16:59
  ↓
daily_collection_dag 매시간 체크 (16:00)
  → 시간 < 17시 → 스킵

17:00 (오전 10시)
  ↓
daily_collection_dag 실행 (17:00)
  ├─ check_and_decide: 첫 실행 확인 → execute
  ├─ price_collection (병렬):
  │  └─ fetch_and_save_prices: 959개 주가 저장
  │     → update_collection_log_price (status=success, count=959)
  └─ indices_collection (병렬):
     └─ fetch_and_save_indices: 2개 지수 저장
        → update_collection_log_indices (status=success, count=2)

collection_log UPDATE: overall_status=success

18:00 (오전 11시)
  ↓
technical_indicator_dag 실행 (18:00)
  ├─ check_indicator_readiness: collection_log 확인
  │  → overall_status=success ✓
  └─ calculate_indicators: 모든 주식 지표 계산
     ├─ RSI, MACD, SMA, Bollinger Bands 계산
     ├─ 959개 지표 저장
     └─ update_indicator_log (status=success, count=959)
```

### 실패 시나리오

```
17:00
  ↓
daily_collection_dag 실행
  ├─ fetch_stock_prices: API 에러
  └─ update_collection_log_price (status=retrying, retry_count=1)

collection_log UPDATE: overall_status=failed

18:00
  ↓
daily_collection_dag 매시간 체크 (18:00)
  ├─ check_and_decide: 재시도 확인
  │  → price_retry_count=1 < 3 → retry 가능
  └─ price_collection 재실행
     → fetch_stock_prices: 성공
     → update_collection_log_price (status=success, retry_count=1)

collection_log UPDATE: overall_status=success

18:00
  ↓
technical_indicator_dag 실행
  → 지표 계산 수행
```

---

## 📂 파일 구조

```
stock-trading-system/airflow/dags/
├── common_functions.py (확장됨 - 상태 추적 함수 추가)
├── generate_daily_collection_dag.py (신규)
├── daily_collection_dag.py (신규)
├── technical_indicator_dag.py (신규)
└── manual_collection_dag.py (기존)
```

---

## ✅ 체크리스트

### 완료된 항목
- [x] collection_log 테이블 생성
- [x] indicator_log 테이블 생성
- [x] 인덱스 생성 (성능 최적화)
- [x] common_functions.py 확장 (상태 추적 함수)
- [x] generate_daily_collection_dag.py 구현
- [x] daily_collection_dag.py 구현
- [x] technical_indicator_dag.py 구현
- [x] manual_collection_dag.py 기존 유지
- [x] Python 문법 검증 완료

### 다음 단계 (배포 후)
- [ ] Airflow 서비스 시작 (`docker-compose up`)
- [ ] Airflow UI에서 4개 DAG 확인
- [ ] DAG 활성화 (UI에서 toggle)
- [ ] 첫 수집 실행 모니터링
- [ ] 실패 시나리오 테스트
- [ ] 수동 수집 DAG 테스트

---

## 🔍 테스트 방법

### 1. DAG 파일 문법 확인
```bash
cd stock-trading-system/airflow/dags/
python -m py_compile generate_daily_collection_dag.py daily_collection_dag.py technical_indicator_dag.py manual_collection_dag.py
```

### 2. Docker 컨테이너에서 테스트
```bash
docker-compose up -d
# Airflow 초기화 및 DAG 로드 대기 (2-3분)
docker exec airflow-scheduler airflow dags list
```

### 3. Airflow UI 접속
```
http://localhost:8080
```

---

## 📝 주요 특징

### 1. 자동 재시도 메커니즘
- 최대 3회 자동 재시도
- `collection_log`와 `indicator_log`에서 재시도 상태 추적
- 매시간 DAG 실행으로 자동 복구

### 2. 상태 추적
- `collection_log`: 주가/지수 수집 상태
- `indicator_log`: 지표 계산 상태
- 각 로그에 재시도 횟수, 에러 메시지, 완료 시간 기록

### 3. 시간 기반 조건부 실행
- 16:00: 준비 (collection_log 생성)
- 17:00: 수집 시작 (주가/지수)
- 18:00: 지표 계산 시작 (수집 완료 확인)
- 매시간 재시도

### 4. 의존성 관리
- `daily_collection_dag`: 독립적 실행
- `technical_indicator_dag`: `daily_collection_dag` 상태 의존
- `manual_collection_dag`: 수동 트리거로 모든 단계 수행

---

## 🚀 배포 및 운영

### 배포 스크립트
```bash
# 1. 기존 Airflow 서비스 중지
docker-compose down

# 2. DAG 파일 배포 (이미 완료)
# stock-trading-system/airflow/dags/ 에 4개 DAG 파일 존재

# 3. 서비스 시작
docker-compose up -d

# 4. DAG 로드 확인
docker-compose logs airflow-scheduler | grep "Loaded DAG"
```

### 모니터링
- Airflow UI: http://localhost:8080
- 수집 상태: `collection_log` 테이블 쿼리
- 지표 상태: `indicator_log` 테이블 쿼리
- 에러 로그: Airflow 로그 또는 Docker 로그

### 문제 해결
```bash
# 로그 확인
docker-compose logs -f airflow-scheduler

# DAG 문법 확인
docker exec airflow-scheduler airflow dags list

# 특정 DAG 실행 권한 설정
docker exec airflow-scheduler airflow dags unpause <dag_id>
```

---

## 📊 성능 최적화

- **NullPool**: Airflow 직렬화 문제 방지
- **인덱스**: `collection_date`, `overall_status` 에 인덱스 추가
- **배치 처리**: 여러 주식을 한 번에 처리
- **타임아웃**: 기술 지표 계산 시 충분한 시간 할당

---

## 🔐 보안 고려사항

- 데이터베이스 자격증명: 환경 변수 사용 (`DATABASE_URL`)
- 재시도 제한: 최대 3회로 무한 루프 방지
- 에러 로깅: 모든 에러 메시지 기록

---

**작성**: 2025-10-20
**상태**: ✅ 구현 완료, 배포 준비됨
