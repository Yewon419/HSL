# Airflow 아키텍처 설계

## 📋 요구사항 정의

### 1. 데이터 수집 및 연산
- **목표**: 매일 자동으로 주가 데이터, 시장 지수를 수집하고, 기술적 지표를 연산

### 2. 과거 재처리 (Backfill) 지원
- **목표**: 특정 과거 날짜의 데이터를 다시 처리할 경우, 해당 날짜의 Task Job만 Clear하면 자동으로 재실행
- **동작**: Airflow의 Clear 기능 활용 → 실패한 Task 또는 특정 날짜의 Task만 선택적으로 재처리

### 3. DAG 구조 (총 3개)
- **DAG 1**: `daily_collection_dag` - 주가/지수 데이터 수집 (매일 실행)
- **DAG 2**: `technical_indicator_dag` - 기술적 지표 연산 (매일 실행)
- **DAG 3**: `orchestrator_dag` - 위 두 DAG의 Task Job을 동적으로 생성 및 조율

---

## 🏗️ 아키텍처 도식화

### 전체 아키텍처 흐름

```
┌────────────────────────────────────────────────────────────────────────┐
│                      AIRFLOW ORCHESTRATION                              │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  GENERATE_TASK_DAG (시스템 다운 후 복구)                         │  │
│  │  [수동 트리거]                                                   │  │
│  │                                                                  │  │
│  │  Task 1: detect_missing_dates → 누락된 날짜 감지                │  │
│  │  Task 2: generate_missing_tasks → Task Job 생성                │  │
│  │  Task 3: schedule_tasks → 배치시간 기반 스케줄링                │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│         ↓ (누락 날짜 Task Job 생성)                                   │
│  ┌──────────────────────────────┐     ┌──────────────────────────────┐│
│  │ DAILY COLLECTION DAG         │     │ TECHNICAL INDICATOR DAG      ││
│  │ [매일 06:00 UTC 자동 실행]    │     │ [매일 07:00 UTC 자동 실행]   ││
│  │                              │     │                              ││
│  │ Task 1: fetch_stock_prices   │     │ Task 1: calculate_indicators││
│  │ Task 2: fetch_market_indices │────→│ Task 2: validate_data      ││
│  │ Task 3: save_to_database     │     │ Task 3: update_db          ││
│  └──────────────────────────────┘     └──────────────────────────────┘│
│         ↓                                ↓                            │
│         │ (매일 생성되는 Task Job들)     │ (매일 생성되는 Task Job들)   │
│         │                                │                            │
│         └────────────────────────────────┴──────────────────────────→│
│                                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │         DATABASE (TimescaleDB) - 최종 데이터 저장               │ │
│  │  - stock_prices (주가 데이터)                                   │ │
│  │  - market_indices (시장 지수)                                   │ │
│  │  - technical_indicators (기술적 지표)                           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└────────────────────────────────────────────────────────────────────────┘

매일 생성되는 Task Job 구조:
─────────────────────────────────────────────────────────────────
2025-10-19 (오늘) Task Job
│
├─ [daily_collection_dag] 2025-10-19 Task Job (06:00 UTC 실행) ✅
│  ├─ fetch_stock_prices-2025-10-19
│  ├─ fetch_market_indices-2025-10-19
│  └─ save_to_database-2025-10-19
│
└─ [technical_indicator_dag] 2025-10-19 Task Job (07:00 UTC 실행) ✅
   ├─ calculate_indicators-2025-10-19
   ├─ validate_data-2025-10-19
   └─ update_db-2025-10-19
```

### 매일 실행 시나리오

```
매일 06:00 UTC (15:00 KST - 한국 시간 오후 3시) - 장 마감 후
   │
   ├─→ [DAILY_COLLECTION_DAG] ─────────────────────┐
   │    Task 1: fetch_stock_prices()                │
   │    Task 2: fetch_market_indices()              │
   │    Task 3: save_to_database()                  │
   │                                                │
   └────→ [데이터 저장 완료]                         │
            │                                        │
            └────→ (약 1시간 후 오후 4시)            │
                   │                                 │
                   ├─→ [TECHNICAL_INDICATOR_DAG] ───┤
                   │    Task 1: calculate_indicators() │
                   │    Task 2: validate_data()      │
                   │    Task 3: update_database()    │
                   │                                 │
                   └────→ [지표 연산 완료]            │
                          │                         │
                          └─────→ [당일 처리 완료] ──┘
```

### 시스템 다운/복구 시나리오 (generate_task_dag 활용)

**상황**: 3시(15:00 UTC) 배치 중 시스템 다운

```
15:00 UTC (한국 시간 24:00) - daily_collection_dag 실행 중
   │
   ├─ fetch_stock_prices-2025-10-19 ✅ 완료
   ├─ fetch_market_indices-2025-10-19 ✅ 완료
   │
   └─ save_to_database-2025-10-19 🔴 시스템 다운 (DB 저장 실패)

→ technical_indicator_dag는 아예 실행되지 않음 (대기 중)
```

**복구 프로세스**:

```
Step 1: 시스템 재기동 (16:30)
   └─→ docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

Step 2: Airflow UI에서 generate_task_dag 수동 트리거
   └─→ http://localhost:8080 접속 → generate_task_dag → "Trigger DAG"

Step 3: detect_missing_dates Task 실행
   ├─ Airflow 메타데이터 조회: daily_collection_dag의 최근 성공 실행 = 2025-10-18
   ├─ DB 조회: SELECT MAX(date) FROM stock_prices = 2025-10-18
   └─ 누락 감지: 2025-10-19 (오늘 배치가 완료되지 않음)

Step 4: generate_missing_tasks Task 실행
   ├─ Task Job 동적 생성: daily_collection_dag의 2025-10-19 새로운 Task Job
   └─ Task Job 동적 생성: technical_indicator_dag의 2025-10-19 새로운 Task Job

Step 5: schedule_tasks Task 실행
   ├─ 현재 시간: 16:30 (배치시간 15:00 이후)
   ├─ 동작: 2025-10-19의 Task Job 즉시 실행
   │
   ├─→ [daily_collection_dag] 2025-10-19 실행
   │   ├─ fetch_stock_prices-2025-10-19 ✅
   │   ├─ fetch_market_indices-2025-10-19 ✅
   │   └─ save_to_database-2025-10-19 ✅
   │
   └─→ [technical_indicator_dag] 2025-10-19 실행
       ├─ calculate_indicators-2025-10-19 ✅
       ├─ validate_data-2025-10-19 ✅
       └─ update_db-2025-10-19 ✅

최종 상태: 2025-10-19 모든 데이터 수집 완료 ✅
```

### 배치시간 이전 복구 시나리오

**상황**: 오전에 시스템 다운 후 복구

```
14:00 UTC - 시스템 다운, 복구
   │
   └─→ generate_task_dag 수동 트리거

schedule_tasks 실행:
├─ 현재 시간: 14:00 (배치시간 15:00 이전)
│
└─ 2025-10-19의 Task Job 대기 상태로 생성
   ├─ State: SCHEDULED (아직 실행 안 함)
   ├─ Waiting until 15:00...
   │
   └─ 15:00 도래 시 자동 실행 ✅
```

### 수동 재실행 시나리오 (특정 날짜 선택적 재처리)

**상황**: 2025-10-16, 2025-10-17 데이터 재수집 필요

```
Airflow UI 접근:
   │
   ├─→ daily_collection_dag 클릭
   ├─→ 캘린더에서 2025-10-16 선택 → "Clear"
   ├─→ 캘린더에서 2025-10-17 선택 → "Clear"
   │
   ├─→ Airflow Scheduler 자동 감지 및 재실행
   │
   ├─→ [daily_collection_dag] 2025-10-16 Task Job 재실행 ✅
   ├─→ [daily_collection_dag] 2025-10-17 Task Job 재실행 ✅
   │
   └─→ 완료 후 자동으로
       [technical_indicator_dag] 2025-10-16, 2025-10-17 트리거 ✅
```

---

## 📊 DAG별 상세 설명

### DAG 1: `daily_collection_dag`

**목표**: 매일 주가 데이터와 시장 지수 수집

**스케줄**: 매일 06:00 UTC (한국 시간 15:00 - 오후 3시, 장 마감 후)

**Task 구성**:
| Task | 설명 | 입력 | 출력 | 실패 시 동작 |
|------|------|------|------|------------|
| `fetch_stock_prices` | 증권사 API에서 주가 데이터 수집 | execution_date | CSV/JSON | Retry 3회 |
| `fetch_market_indices` | 시장 지수 수집 (KOSPI, KOSDAQ) | execution_date | CSV/JSON | Retry 3회 |
| `save_to_database` | 수집한 데이터를 DB에 저장 | fetch_stock_prices, fetch_market_indices | DB Row Count | Task 실패 |

**특징**:
- `execution_date` 변수를 활용하여 매일 다른 날짜의 데이터 처리
- 재처리 시: 특정 날짜의 Task만 Clear → 자동 재실행
- Task 간 의존성: `fetch_*` → `save_to_database` (직렬 실행)

**예시 (Python Operator)**:
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

def fetch_stock_prices(**context):
    execution_date = context['execution_date'].date()
    # 해당 날짜의 주가 데이터 수집
    print(f"Fetching stock prices for {execution_date}")

def fetch_market_indices(**context):
    execution_date = context['execution_date'].date()
    # 해당 날짜의 시장 지수 수집
    print(f"Fetching market indices for {execution_date}")

def save_to_database(**context):
    # 데이터 DB 저장
    print("Saving data to database")

with DAG(
    'daily_collection_dag',
    start_date=datetime(2025, 10, 1),
    schedule_interval='0 6 * * *',  # 매일 06:00 UTC
    catchup=True,  # 과거 날짜 자동 처리
    default_args={'retries': 3}
) as dag:

    fetch_prices = PythonOperator(task_id='fetch_stock_prices', python_callable=fetch_stock_prices)
    fetch_indices = PythonOperator(task_id='fetch_market_indices', python_callable=fetch_market_indices)
    save_db = PythonOperator(task_id='save_to_database', python_callable=save_to_database)

    [fetch_prices, fetch_indices] >> save_db
```

---

### DAG 2: `technical_indicator_dag`

**목표**: 매일 기술적 지표 (RSI, MACD, Bollinger Band 등) 연산

**스케줄**: 매일 07:00 UTC (한국 시간 16:00 - 오후 4시, collection 이후 1시간)

**Task 구성**:
| Task | 설명 | 입력 | 출력 | 의존성 |
|------|------|------|------|--------|
| `calculate_indicators` | RSI, MACD, SMA, Bollinger Band 연산 | stock_prices (DB) | DataFrame | daily_collection_dag 완료 |
| `validate_data` | 연산된 지표 데이터 검증 | calculate_indicators 결과 | Validation Report | 이전 Task 완료 |
| `update_indicators_db` | 연산된 지표를 DB 저장 | validate_data 결과 | DB Row Count | 이전 Task 완료 |

**특징**:
- `daily_collection_dag` 완료 후 자동 트리거
- 과거 데이터 재처리 시: 해당 날짜의 주가 데이터를 기반으로 다시 연산
- 데이터 검증으로 오류 방지

**예시 (Python Operator)**:
```python
def calculate_indicators(**context):
    execution_date = context['execution_date'].date()
    # DB에서 주가 데이터 조회
    # RSI, MACD, SMA 등 계산
    print(f"Calculating indicators for {execution_date}")

def validate_data(**context):
    # 지표 데이터 검증 (null 체크, 범위 체크 등)
    print("Validating indicator data")

def update_indicators_db(**context):
    # 검증된 지표를 DB 저장
    print("Updating technical_indicators table")

with DAG(
    'technical_indicator_dag',
    start_date=datetime(2025, 10, 1),
    schedule_interval='0 7 * * *',  # 매일 07:00 UTC
    catchup=True,
    default_args={'retries': 2}
) as dag:

    calc_ind = PythonOperator(task_id='calculate_indicators', python_callable=calculate_indicators)
    validate = PythonOperator(task_id='validate_data', python_callable=validate_data)
    update_db = PythonOperator(task_id='update_indicators_db', python_callable=update_indicators_db)

    calc_ind >> validate >> update_db
```

---

### DAG 3: `generate_task_dag` (복구 및 누락 감지)

**목표**: 시스템 다운 후 재기동 시 누락된 날짜의 Task Job을 자동으로 생성하고 관리

**스케줄**: 시스템 기동 후 수동 트리거 또는 정기적 체크 (예: 매일 05:00 UTC)

**동작 흐름**:

```
generate_task_dag 실행
   │
   ├─ Task 1: detect_missing_dates
   │   └─ daily_collection_dag과 technical_indicator_dag의 실행 기록 조회
   │   └ DB의 stock_prices, technical_indicators 마지막 데이터 날짜 확인
   │   └ 누락된 날짜 목록 도출 (예: 2025-10-16, 2025-10-17)
   │
   ├─ Task 2: generate_missing_tasks
   │   ├─ 누락된 각 날짜에 대해 Task Job 생성
   │   ├─ execution_date를 설정하여 강제 실행
   │   └ 생성된 Task Job 목록 반환
   │
   └─ Task 3: schedule_tasks
       ├─ 각 Task Job의 execution_date와 현재 시간 비교
       ├─ 배치시간(3:00 PM UTC) 이전이면 → Task 일시정지 상태로 생성 후 대기
       ├─ 배치시간 이후이면 → 즉시 Task 실행
       └─ 누락된 모든 날짜를 순차적으로 처리하여 최종 동기화
```

**Task 구성**:
| Task | 설명 | 입력 | 출력 | 동작 |
|------|------|------|------|------|
| `detect_missing_dates` | 누락된 날짜 감지 | Airflow 실행 기록, DB 데이터 | 누락 날짜 목록 | 1회 실행 |
| `generate_missing_tasks` | 누락된 날짜의 Task Job 생성 | detect_missing_dates 결과 | 생성된 Task 정보 | 동적 Task 생성 |
| `schedule_tasks` | Task 실행 시간 조정 | generate_missing_tasks 결과 | 스케줄링 완료 | 배치시간 기반 대기/실행 |

**특징**:
- **시스템 복구 시나리오**: 3시 배치 중 시스템 다운 → 기동 후 generate_task_dag 수동 실행 → 누락 감지 → 자동 재생성
- **배치시간 전 생성**: execution_date가 미래이면 대기했다가 시간 도래 시 자동 실행
- **배치시간 이후 생성**: execution_date가 과거이면 즉시 실행하고, 다음 날부터 정상 스케줄로 돌아옴
- **순차 처리**: 하루씩 순차적으로 처리하여 누락된 전체 기간 커버

**예시 (Python Operator)**:
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine('postgresql+psycopg2://admin:admin123@localhost:5435/stocktrading')

def detect_missing_dates(**context):
    """누락된 날짜 감지"""
    # Airflow 메타데이터에서 daily_collection_dag의 마지막 성공 실행 날짜 조회
    # DB에서 stock_prices의 마지막 date 조회
    query = "SELECT MAX(date) FROM stock_prices"
    last_date_db = pd.read_sql(query, engine).iloc[0, 0]

    # Airflow 스케줄러에서 기대하는 날짜 범위와 비교
    # 누락된 날짜 목록 생성
    missing_dates = ['2025-10-16', '2025-10-17']  # 예시
    context['task_instance'].xcom_push(key='missing_dates', value=missing_dates)
    print(f"Missing dates: {missing_dates}")

def generate_missing_tasks(**context):
    """누락된 날짜의 Task Job 생성"""
    missing_dates = context['task_instance'].xcom_pull(
        task_ids='detect_missing_dates',
        key='missing_dates'
    )

    # 각 누락 날짜에 대해 Task Job 생성
    for date_str in missing_dates:
        print(f"Generating Task Job for {date_str}")
        # DagRun을 프로그래매틱하게 생성

    context['task_instance'].xcom_push(key='generated_tasks', value=missing_dates)

def schedule_tasks(**context):
    """배치시간 기반으로 Task 스케줄링"""
    generated_tasks = context['task_instance'].xcom_pull(
        task_ids='generate_missing_tasks',
        key='generated_tasks'
    )

    batch_time = datetime.strptime('15:00', '%H:%M').time()  # 3:00 PM UTC
    current_time = datetime.now().time()

    for task_date in generated_tasks:
        execution_dt = datetime.strptime(task_date, '%Y-%m-%d')

        if execution_dt.time() < batch_time:
            print(f"Task {task_date}: Waiting until batch time {batch_time}")
            # Task를 대기 상태로 생성
        else:
            print(f"Task {task_date}: Executing immediately (batch time passed)")
            # Task를 즉시 실행

with DAG(
    'generate_task_dag',
    start_date=datetime(2025, 10, 1),
    schedule_interval=None,  # 수동 트리거
    catchup=False
) as dag:

    detect = PythonOperator(task_id='detect_missing_dates', python_callable=detect_missing_dates)
    generate = PythonOperator(task_id='generate_missing_tasks', python_callable=generate_missing_tasks)
    schedule = PythonOperator(task_id='schedule_tasks', python_callable=schedule_tasks)

    detect >> generate >> schedule
```

---

## 🔄 Task Job 생성 및 재처리 프로세스

### 정상 실행 흐름

```
Airflow Scheduler
   │
   ├─ 매일 06:00 UTC
   │   └─→ daily_collection_dag 인스턴스 생성
   │        ├─ Task Job 1: fetch_stock_prices (2025-10-19)
   │        ├─ Task Job 2: fetch_market_indices (2025-10-19)
   │        └─ Task Job 3: save_to_database (2025-10-19)
   │
   └─ 매일 07:00 UTC (collection 완료 후)
      └─→ technical_indicator_dag 인스턴스 생성
           ├─ Task Job 1: calculate_indicators (2025-10-19)
           ├─ Task Job 2: validate_data (2025-10-19)
           └─ Task Job 3: update_indicators_db (2025-10-19)
```

### 재처리 (Clear) 흐름

```
사용자: Airflow UI → daily_collection_dag → 2025-10-16 선택 → "Clear"
   │
   ├─→ Airflow Backend: daily_collection_dag의 2025-10-16 인스턴스 모든 Task 상태 → "NONE" (초기화)
   │
   ├─→ Airflow Scheduler: 상태 감지 → 자동으로 Task 재실행
   │    └─ Task Job 1: fetch_stock_prices (2025-10-16) - 재실행
   │    └─ Task Job 2: fetch_market_indices (2025-10-16) - 재실행
   │    └─ Task Job 3: save_to_database (2025-10-16) - 재실행
   │
   ├─→ 데이터 수집 완료 후
   │
   └─→ technical_indicator_dag의 2025-10-16 인스턴스도 자동 트리거
        └─ Task Job 1-3: 지표 재연산
```

---

## 💾 데이터베이스 연동

### Task에서 데이터베이스 쿼리 예시

```python
from sqlalchemy import create_engine
import pandas as pd

# DB 연결
engine = create_engine('postgresql+psycopg2://admin:admin123@localhost:5435/stocktrading')

# 데이터 조회
def fetch_from_db(**context):
    query = "SELECT * FROM stock_prices WHERE date = %s"
    execution_date = context['execution_date'].date()
    df = pd.read_sql(query, engine, params=[execution_date])
    return df

# 데이터 저장
def save_to_db(**context):
    df = context['task_instance'].xcom_pull(task_ids='fetch_stock_prices')
    df.to_sql('stock_prices', engine, if_exists='append', index=False)
```

---

## 🎯 핵심 정리

| 항목 | 설명 |
|------|------|
| **DAG 수** | 3개 |
| | - `daily_collection_dag`: 매일 06:00 UTC 자동 실행 (주가, 지수 수집) |
| | - `technical_indicator_dag`: 매일 07:00 UTC 자동 실행 (지표 연산) |
| | - `generate_task_dag`: 시스템 복구 시 수동 트리거 (누락 감지 및 Task Job 생성) |
| **일일 Task 생성** | 2개 DAG × 3 Tasks = 6개 Task Job/일 (매일 자동 생성) |
| **매일 Task Job** | execution_date 변수로 자동 생성되므로 시각적 모니터링 용이 |
| **특정 날짜 재처리** | Airflow UI에서 Clear 기능으로 특정 날짜만 선택적 재실행 |
| **시스템 복구** | generate_task_dag에서 누락 날짜 자동 감지 → Task Job 동적 생성 |
| **배치시간 관리** | 복구 시 배치시간 전이면 대기, 이후면 즉시 실행 |
| **의존성** | daily_collection_dag 완료 후 technical_indicator_dag 자동 트리거 |
| **데이터 흐름** | API → DB (stock_prices, market_indices) → 연산 → DB (technical_indicators) |

---

## 🚀 배포 시작 단계

1. **DAG 1 구현**: `daily_collection_dag.py` 작성
2. **DAG 2 구현**: `technical_indicator_dag.py` 작성
3. **DAG 3 구현** (선택): `orchestrator_dag.py` 작성
4. **테스트**: Airflow UI에서 DAG 실행 및 Task Job 검증
5. **배포**: Production 환경으로 DAG 배포
6. **모니터링**: Airflow UI, 로그, 알림 설정

