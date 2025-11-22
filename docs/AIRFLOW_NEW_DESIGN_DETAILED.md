# Airflow 새 설계 - 상세 구조

## 핵심 개념
**매일 자동 수집 보장 + 실패 시 자동 재시도**

---

## DAG 구조

### 1. `generate_daily_collection_dag` (Task Generator DAG)
**목적**: 매일 1개의 Task Job 생성 (generate된 DAG 생성)

**스케줄**: 매일 16:00 UTC (한국시간 오전 1시) - 또는 원하는 시작 시간
```
매일 16시 → generate_daily_collection_dag 실행
  ↓
2개의 task group을 포함한 dynamic_daily_collection_dag 생성
  (아직 실행 X, 생성만 함)
```

**생성 구조**:
```python
# generate_daily_collection_dag가 생성하는 구조
dynamic_daily_collection_dag_2025-10-20 (예시)
├── price_task_group (주가 작업 그룹)
│   ├── fetch_stock_prices (주가 수집)
│   ├── save_stock_prices (주가 저장)
│   └── verify_stock_prices (주가 저장 확인 → collection_log 테이블 기록)
│
└── indices_task_group (지수 작업 그룹)
    ├── fetch_market_indices (지수 수집)
    ├── save_market_indices (지수 저장)
    └── verify_market_indices (지수 저장 확인 → collection_log 테이블 기록)
```

---

### 2. `daily_collection_dag` (실행 DAG)
**목적**: 매시간 체크 → 해당 시간이면 실행, 실패면 재실행

**스케줄**: `0 16-23 * * 1-5` (매일 16시~23시 매시간)
```
16시 → 확인 (아직 17시 아니므로 스킵)
17시 → 실행 (오늘 10-20 주가/지수 수집 작업 실행)
18시 → 확인 (이미 완료면 스킵, 실패면 재실행)
19시 → 확인 (이미 완료면 스킵, 실패면 재실행)
...
23시 → 최종 확인 (이미 완료면 스킵, 실패면 재실행)
```

**실행 로직**:
```python
def should_run_today_collection(target_date):
    """
    오늘 데이터 수집 여부 확인

    1. 현재 시간이 17시 이상인가?
    2. 대상 날짜의 task group이 생성되었는가?
    3. collection_log에서 오늘 항목이 있는가?
       - success: 스킵
       - failed: 재실행
       - not_found: 첫 실행
    """
```

**매시간 실행 흐름**:
```
현재 시간 >= 17시?
  ├─ NO → 아무것도 안 함 (다음 시간 대기)
  └─ YES → collection_log 확인
      ├─ 성공 기록 있음 → 스킵
      ├─ 실패 기록 있음 → 재실행 (retry count 증가)
      └─ 기록 없음 → 첫 실행
```

---

### 3. `technical_indicator_dag` (기술적 지표 DAG)
**목적**: 18시에 주가/지수 수집 완료 확인 후 지표 계산

**스케줄**: `0 18-23 * * 1-5` (매일 18시~23시 매시간)

**실행 로직**:
```python
def should_run_indicator_calculation(target_date):
    """
    지표 계산 수행 조건 확인

    1. 현재 시간이 18시 이상인가?
    2. collection_log에서 오늘 항목의 상태가 'success'인가?
       - YES → 지표 계산 수행
       - NO → 대기
    """
```

**매시간 실행 흐름**:
```
현재 시간 >= 18시?
  ├─ NO → 아무것도 안 함 (다음 시간 대기)
  └─ YES → collection_log 확인
      ├─ 오늘 수집 성공?
      │   ├─ YES → 지표 계산 수행
      │   └─ NO → 대기 (수집이 완료될 때까지)
      └─ 지표 계산 완료 후 indicator_log 기록
```

---

## 데이터베이스 테이블

### `collection_log` (수집 상태 추적)
```sql
CREATE TABLE collection_log (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    collection_date DATE NOT NULL,  -- 실제 수집된 날짜

    -- 주가 상태
    price_status VARCHAR(20),  -- 'pending', 'success', 'failed', 'retrying'
    price_count INTEGER,
    price_error_message TEXT,
    price_completed_at TIMESTAMP,
    price_retry_count INTEGER DEFAULT 0,

    -- 지수 상태
    indices_status VARCHAR(20),  -- 'pending', 'success', 'failed', 'retrying'
    indices_count INTEGER,
    indices_error_message TEXT,
    indices_completed_at TIMESTAMP,
    indices_retry_count INTEGER DEFAULT 0,

    -- 전체 상태
    overall_status VARCHAR(20),  -- 'pending', 'partial', 'success', 'failed'

    started_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date)
);
```

### `indicator_log` (지표 계산 상태 추적)
```sql
CREATE TABLE indicator_log (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    indicator_date DATE NOT NULL,

    status VARCHAR(20),  -- 'pending', 'success', 'failed', 'retrying'
    indicators_count INTEGER,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date)
);
```

---

## 실행 예시

### 2025-10-20 (월요일) 시나리오

```
[16:00] generate_daily_collection_dag 실행
  ↓
  dynamic_daily_collection_dag_2025-10-20 생성
  (주가 task group, 지수 task group 포함)
  ↓
  collection_log: INSERT (date=2025-10-20, status=pending)

[16:01~16:59] daily_collection_dag 매시간 체크
  → 17시 아직 아니므로 스킵

[17:00] daily_collection_dag 실행
  ↓
  주가 task group 실행
    ├─ fetch_stock_prices (pykrx 호출, 959개 수집)
    ├─ save_stock_prices (DB 저장)
    └─ verify_stock_prices (확인 → collection_log 업데이트)
  ↓
  지수 task group 실행
    ├─ fetch_market_indices (pykrx 호출, 2개 수집)
    ├─ save_market_indices (DB 저장)
    └─ verify_market_indices (확인 → collection_log 업데이트)
  ↓
  collection_log: UPDATE (date=2025-10-20, overall_status=success)

[18:00] technical_indicator_dag 실행
  ↓
  collection_log 확인 (2025-10-20 status=success) ✓
  ↓
  지표 계산 실행
    ├─ calculate_indicators (RSI, MACD, SMA, BB)
    ├─ save_indicators (DB 저장)
    └─ verify_indicators (확인 → indicator_log 업데이트)
  ↓
  indicator_log: UPDATE (date=2025-10-20, status=success)
```

### 실패 시나리오

```
[17:00] daily_collection_dag 실행
  ↓
  주가 수집 실패 (API 에러)
  ↓
  collection_log: UPDATE (price_status=failed, price_retry_count=1)

[18:00] daily_collection_dag 매시간 체크
  ↓
  collection_log 확인 → price_status=failed 확인
  ↓
  재실행 시작
    ├─ fetch_stock_prices (재시도 1회)
    ├─ save_stock_prices
    └─ verify_stock_prices (이번엔 성공)
  ↓
  collection_log: UPDATE (price_status=success, price_retry_count=1)

[18:00] technical_indicator_dag 실행
  ↓
  collection_log 확인 (이제 success) ✓
  ↓
  지표 계산 실행 시작...
```

---

## 매시간 체크 로직

### daily_collection_dag 매시간 실행 코드 개요
```python
@task
def check_and_run_daily_collection():
    current_hour = datetime.now().hour
    target_date = date.today()

    # 17시 이전이면 스킵
    if current_hour < 17:
        return {'status': 'skipped', 'reason': 'before_collection_time'}

    # collection_log 확인
    log_entry = get_collection_log(target_date)

    if log_entry is None:
        # 첫 실행
        return {'status': 'run', 'action': 'first_run'}

    if log_entry['overall_status'] == 'success':
        # 이미 성공
        return {'status': 'skipped', 'reason': 'already_success'}

    if log_entry['overall_status'] == 'failed':
        # 재시도
        if log_entry['price_retry_count'] < 3 or log_entry['indices_retry_count'] < 3:
            return {'status': 'run', 'action': 'retry', 'retry_count': log_entry['price_retry_count']}
        else:
            return {'status': 'failed', 'reason': 'max_retry_exceeded'}
```

---

## 핵심 포인트

| 항목 | 설명 |
|------|------|
| **daily_collection_dag** | 16시부터 매시간 실행, 17시부터 수집 시작, 실패 시 재시도 |
| **technical_indicator_dag** | 18시부터 매시간 실행, 주가/지수 수집 완료 확인 후만 실행 |
| **재시도** | 최대 3회 자동 재시도 |
| **모니터링** | collection_log / indicator_log 테이블로 상태 추적 |
| **수동 복구** | manual_collection_dag로 특정 날짜 수동 수집 가능 |

---

## 체크리스트

- [ ] generate_daily_collection_dag 작성 (task group 생성)
- [ ] daily_collection_dag 작성 (16~23시 매시간, 17시부터 실행)
- [ ] technical_indicator_dag 작성 (18~23시 매시간, 수집 확인 후 실행)
- [ ] collection_log 테이블 생성
- [ ] indicator_log 테이블 생성
- [ ] 3개 DAG 배포
- [ ] 자동 실행 테스트
- [ ] 실패 시나리오 테스트

---

**이해가 완벽한가요? 추가 질문이 있으면 이제 물어봐.**
