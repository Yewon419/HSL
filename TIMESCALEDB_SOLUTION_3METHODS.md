# TimescaleDB dimension_slice_pkey 제약 조건 해결 - 3가지 방법

## 🎯 문제 상황

```
오류: "duplicate key value violates unique constraint 'dimension_slice_pkey'"

원인: DELETE 후 재삽입 시 하이퍼테이블 메타데이터 충돌
```

### 현재 상태
- **하이퍼테이블**: stock_prices (자동 chunking 중)
- **Chunks**: 267개 (매일 새로 생성)
- **Dimension Slice**: 597개 엔트리 (메타데이터)
- **문제**: 2025-10-28 DELETE 후 재삽입 시 메타데이터 충돌

---

## 📚 근본 원인

### TimescaleDB 내부 구조

```
INSERT 시점:
┌─────────────────────────────────────┐
│ INSERT INTO stock_prices ...        │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Chunk 자동 선택/생성                 │
│ (시간 범위별로 자동 분할)            │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ _timescaledb_catalog.dimension_slice │
│ 메타데이터 엔트리 추가                │
│ (Chunk과 시간 범위 매핑)             │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ 실제 데이터 삽입                      │
│ (chunk_xxxxx_yyyyy 테이블)           │
└─────────────────────────────────────┘
```

### DELETE의 문제

```
DELETE FROM stock_prices WHERE date='2025-10-28'
  ↓
chunk 데이터 제거 ✓
  ↓
dimension_slice 메타데이터는 그대로 ✗ (고아 엔트리)
  ↓
재삽입 시도
  ↓
동일한 ID로 메타데이터 추가 시도 → PK 충돌! 💥
```

### 왜 이렇게 설계?

| 관점 | 이유 |
|------|------|
| **성능** | DELETE 시 메타데이터 정리는 비용 높음 |
| **효율** | 빠른 DELETE 보장 |
| **설계** | 시계열 데이터는 삽입만 많이 함 (수정 드문 경우) |

---

## 💡 해결 방법 3가지

### **방법 1: TRUNCATE 사용** ⭐⭐⭐⭐⭐ 권장

#### 개념
```
DELETE vs TRUNCATE:
- DELETE: 행을 하나씩 삭제 → chunk와 메타데이터 불일치 발생
- TRUNCATE: 전체 테이블 재초기화 → 메타데이터도 함께 초기화
```

#### 코드

```python
# 문제 코드 (DELETE)
cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))
# → dimension_slice 메타데이터 충돌!

# 해결 코드 (TRUNCATE)
cursor.execute("TRUNCATE stock_prices CASCADE")
# → 메타데이터도 완전히 초기화됨!
```

#### 문제점

❌ `TRUNCATE`는 WHERE 조건을 지원하지 않음 (전체 테이블만 초기화)

#### 개선된 해결책: TRUNCATE 대신 INSERT IGNORE 사용

```python
def save_stock_prices(prices_df, target_date, engine):
    """stock_prices 저장 (dimension_slice 충돌 회피)"""

    if len(prices_df) == 0:
        return 0

    # psycopg2 직접 사용
    raw_conn = engine.raw_connection()
    cursor = raw_conn.cursor()

    try:
        # 1단계: 해당 날짜 데이터 삭제 (메타데이터는 유지)
        cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))

        # 2단계: 약간의 지연 (TimescaleDB 메타데이터 동기화)
        import time
        time.sleep(0.1)

        # 3단계: 데이터 삽입 (기존 chunk 재사용)
        insert_data = [
            (row['ticker'], row['date'], row['open_price'], row['high_price'],
             row['low_price'], row['close_price'], row['volume'], row['created_at'])
            for _, row in prices_df.iterrows()
        ]

        cursor.executemany("""
            INSERT INTO stock_prices
            (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, date) DO NOTHING
        """, insert_data)

        raw_conn.commit()
        return len(prices_df)

    except Exception as e:
        raw_conn.rollback()
        logger.error(f"Error saving prices: {e}")
        raise
    finally:
        cursor.close()
        raw_conn.close()
```

#### 장점
- ✅ 간단함 (한두 줄 추가)
- ✅ 기존 chunk 재사용 가능
- ✅ 부분 데이터만 처리 가능
- ✅ 메모리 효율적

#### 단점
- ❌ 여전히 고아 메타데이터 누적
- ❌ 시간이 지나면서 메타데이터 테이블 증가

#### 구현 시간: **10분**

---

### **방법 2: 정기적 재생성** ⭐⭐⭐⭐

#### 개념
```
문제를 근본적으로 해결하되, 정기적으로 실행:
- 매주 또는 매월 1회 하이퍼테이블 재생성
- 고아 메타데이터 완전 정리
- 오래된 데이터는 아카이브
```

#### 코드

```python
def recreate_hypertable_for_date_range(engine, from_date, to_date):
    """
    주어진 기간의 데이터를 임시 테이블로 옮기고
    하이퍼테이블을 재생성 후 데이터 복원

    주 1회 야간에 자동 실행 권장
    """

    raw_conn = engine.raw_connection()
    cursor = raw_conn.cursor()

    try:
        print(f"Step 1: Backup data ({from_date} ~ {to_date})")

        # 1단계: 보존할 데이터 백업 (임시 테이블로)
        cursor.execute(f"""
            CREATE TABLE stock_prices_backup AS
            SELECT * FROM stock_prices
            WHERE date >= '{from_date}' AND date <= '{to_date}'
        """)
        raw_conn.commit()
        print(f"  [O] Backup complete: {cursor.rowcount} rows")

        print("\nStep 2: Drop and recreate hypertable")

        # 2단계: 하이퍼테이블 삭제 (메타데이터 포함)
        cursor.execute("SELECT drop_if_exists('public.stock_prices')")
        raw_conn.commit()
        print("  [O] Hypertable dropped")

        # 3단계: 일반 테이블로 재생성
        print("\nStep 3: Create regular table")
        cursor.execute("""
            CREATE TABLE stock_prices (
                ticker VARCHAR(6) NOT NULL,
                date DATE NOT NULL,
                open_price NUMERIC,
                high_price NUMERIC,
                low_price NUMERIC,
                close_price NUMERIC NOT NULL,
                volume BIGINT,
                created_at TIMESTAMP WITH TIME ZONE,
                CONSTRAINT unique_stock_prices_ticker_date UNIQUE (ticker, date),
                CONSTRAINT stocks_fk FOREIGN KEY (ticker) REFERENCES stocks(ticker)
            )
        """)
        raw_conn.commit()
        print("  [O] Regular table created")

        # 4단계: 다시 하이퍼테이블로 변환
        print("\nStep 4: Convert to hypertable")
        cursor.execute("""
            SELECT create_hypertable('stock_prices', 'date',
                                    if_not_exists => TRUE)
        """)
        raw_conn.commit()
        print("  [O] Hypertable created")

        # 5단계: 인덱스 재생성
        print("\nStep 5: Recreate indexes")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_prices_ticker_date
            ON stock_prices (ticker, date DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_prices_date
            ON stock_prices (date DESC)
        """)
        raw_conn.commit()
        print("  [O] Indexes created")

        # 6단계: 데이터 복원
        print("\nStep 6: Restore data")
        cursor.execute("""
            INSERT INTO stock_prices
            SELECT * FROM stock_prices_backup
        """)
        raw_conn.commit()
        inserted = cursor.rowcount
        print(f"  [O] Data restored: {inserted} rows")

        # 7단계: 백업 테이블 삭제
        print("\nStep 7: Clean up")
        cursor.execute("DROP TABLE stock_prices_backup")
        raw_conn.commit()
        print("  [O] Backup table removed")

        print("\n[SUCCESS] Hypertable recreation complete!")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        raw_conn.rollback()
        raise
    finally:
        cursor.close()
        raw_conn.close()
```

#### 사용 예

```python
# 매주 일요일 자정에 실행하는 DAG 작성
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'stock-system',
    'retries': 1,
}

dag = DAG(
    'maintain_hypertable',
    default_args=default_args,
    schedule_interval='0 0 * * 0',  # 매주 일요일 자정
    catchup=False,
)

def maintain_task():
    from common_functions import get_db_engine
    engine = get_db_engine()

    # 지난 30일 데이터 범위만 재생성
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=30)

    recreate_hypertable_for_date_range(engine, from_date, to_date)

maintain_task = PythonOperator(
    task_id='maintain_hypertable',
    python_callable=maintain_task,
    dag=dag,
)
```

#### 장점
- ✅ 근본적 해결 (메타데이터 완전 정리)
- ✅ 성능 최적화 (오래된 chunk 정리)
- ✅ 장기 안정성 보장

#### 단점
- ❌ 실행 시간 김 (5~10분)
- ❌ 해당 기간 조회 불가 (유지보수 창)
- ❌ 복잡한 구현

#### 실행 시간: **5~10분** (운영 중 조정 가능)
#### 구현 시간: **1시간**

---

### **방법 3: ON CONFLICT DO UPDATE 활용** ⭐⭐⭐⭐⭐ 최간단

#### 개념
```
DELETE를 하지 말고 처음부터 충돌을 예상하는 UPSERT 사용:
- 기존 데이터가 있으면 UPDATE
- 없으면 INSERT
→ DELETE 오버헤드와 메타데이터 충돌 모두 해결
```

#### 코드

```python
def save_stock_prices_upsert(prices_df, target_date, engine):
    """UPSERT 방식: DELETE 없이 INSERT/UPDATE 통합"""

    if len(prices_df) == 0:
        return 0

    raw_conn = engine.raw_connection()
    cursor = raw_conn.cursor()

    try:
        # DELETE 하지 말고 바로 UPSERT!
        # (메타데이터 충돌 발생 불가)

        insert_data = [
            (row['ticker'], row['date'],
             float(row['open_price']), float(row['high_price']),
             float(row['low_price']), float(row['close_price']),
             int(row['volume']), row['created_at'])
            for _, row in prices_df.iterrows()
        ]

        # PostgreSQL UPSERT 문법
        cursor.executemany("""
            INSERT INTO stock_prices
            (ticker, date, open_price, high_price, low_price,
             close_price, volume, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, date) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume,
                created_at = EXCLUDED.created_at
        """, insert_data)

        raw_conn.commit()
        logger.info(f"Saved {len(prices_df)} prices for {target_date}")
        return len(prices_df)

    except Exception as e:
        raw_conn.rollback()
        logger.error(f"Error saving prices: {e}")

        # UPSERT도 실패하면 원인은 다른 것
        # → 데이터 이슈, 타입 불일치 등
        raise
    finally:
        cursor.close()
        raw_conn.close()
```

#### TimescaleDB의 UPSERT 제약사항 해결

⚠️ **주의**: TimescaleDB의 하이퍼테이블은 ON CONFLICT 지원이 제한적일 수 있음

만약 하이퍼테이블에서 ON CONFLICT 오류 발생 시:

```python
def save_stock_prices_hybrid(prices_df, target_date, engine):
    """하이퍼테이블 호환 UPSERT"""

    raw_conn = engine.raw_connection()
    cursor = raw_conn.cursor()

    try:
        insert_data = [
            (row['ticker'], row['date'],
             float(row['open_price']), float(row['high_price']),
             float(row['low_price']), float(row['close_price']),
             int(row['volume']), row['created_at'])
            for _, row in prices_df.iterrows()
        ]

        # 1단계: 삭제 (하지만 commit하지 않음 - 트랜잭션 유지)
        cursor.execute(
            "DELETE FROM stock_prices WHERE date = %s",
            (target_date,)
        )

        # 2단계: 즉시 삽입 (같은 트랜잭션)
        cursor.executemany("""
            INSERT INTO stock_prices
            (ticker, date, open_price, high_price, low_price,
             close_price, volume, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, insert_data)

        # 3단계: 한 번에 커밋 (원자성 보장)
        raw_conn.commit()

        return len(prices_df)

    except Exception as e:
        raw_conn.rollback()
        logger.error(f"Error: {e}")
        raise
    finally:
        cursor.close()
        raw_conn.close()
```

#### 장점
- ✅ 가장 간단 (기존 코드 최소 변경)
- ✅ 빠름 (DELETE 오버헤드 없음)
- ✅ 메타데이터 충돌 발생 불가
- ✅ 이미 있는 데이터도 자동 업데이트
- ✅ 트랜잭션 안전성 보장

#### 단점
- ❌ ON CONFLICT 지원 확인 필요 (하이퍼테이블)
- ❌ 약간의 성능 오버헤드 (UPDATE 로직)

#### 구현 시간: **15분**

---

## 📊 3가지 방법 비교

| 기준 | 방법 1 | 방법 2 | 방법 3 |
|------|--------|--------|---------|
| **구현 난도** | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| **실행 속도** | ⭐⭐⭐⭐ 빠름 | ⭐ 느림 | ⭐⭐⭐⭐ 빠름 |
| **근본 해결** | ❌ 임시 | ✅ 완전 | ✅ 완전 |
| **메타데이터** | ❌ 누적 | ✅ 정리 | ✅ 안전 |
| **즉시 적용** | ✅ 가능 | ⚠️ 부분 | ✅ 가능 |
| **운영 영향** | 없음 | 유지보수 창 | 없음 |
| **코드 복잡도** | 낮음 | 높음 | 중간 |
| **신뢰성** | 중간 | 높음 | 높음 |

---

## 🎯 상황별 추천

### 상황 1: "지금 당장 2025-10-28 데이터를 수집해야 해"
→ **방법 1** (DELETE + 지연 + INSERT)
- 10분 안에 적용 가능
- 즉시 효과

### 상황 2: "향후 계속 같은 문제가 반복되는 것 같아"
→ **방법 3** (ON CONFLICT DO UPDATE)
- 근본 원인 해결
- 향후 재발 불가

### 상황 3: "장기적으로 안정성 보장하고 싶어"
→ **방법 2** (정기 재생성) + **방법 3** (UPSERT)
- Phase 1: 방법 3로 현재 문제 해결
- Phase 2: 주 1회 방법 2 자동 실행
- 최고의 안정성과 성능

---

## ✅ 추천 최종 방안: 조합 전략

```
즉시 적용:
└─ 방법 1 (DELETE + 지연) → 2025-10-28 데이터 수집

단기 (1시간):
└─ 방법 3 (UPSERT) 구현 → common_functions.py 수정

장기 (선택사항):
└─ 방법 2 (주간 유지보수) → Airflow DAG 추가
```

---

## 🚀 구현 순서

### Phase 1: 현재 문제 해결 (20분)

**파일**: `stock-trading-system/airflow/dags/common_functions.py`

```python
# line 198 이후 수정
import time

def save_stock_prices(prices_df, target_date, engine):
    if len(prices_df) == 0:
        return 0

    raw_conn = engine.raw_connection()
    cursor = raw_conn.cursor()

    try:
        # DELETE 실행
        cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))

        # 메타데이터 동기화 지연 (300ms)
        time.sleep(0.3)

        # INSERT (기존 chunk 재사용)
        insert_data = [
            (row['ticker'], row['date'], row['open_price'], row['high_price'],
             row['low_price'], row['close_price'], row['volume'], row['created_at'])
            for _, row in prices_df.iterrows()
        ]

        cursor.executemany("""
            INSERT INTO stock_prices
            (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, insert_data)

        raw_conn.commit()
        return len(prices_df)
    except Exception as e:
        raw_conn.rollback()
        raise
    finally:
        cursor.close()
        raw_conn.close()
```

### Phase 2: 근본 해결 (1시간)

UPSERT 방식으로 전환 (방법 3)

### Phase 3: 장기 안정화 (선택사항)

주간 유지보수 DAG 추가 (방법 2)

---

## ❓ FAQ

**Q: 왜 처음부터 UPSERT를 안 썼나?**
A: 개발 당시 ON CONFLICT가 하이퍼테이블에서 불완전 지원하는 것으로 알려짐

**Q: 메타데이터가 계속 쌓이면?**
A: 약 1년에 365개, 수 년에 걸쳐 약간의 성능 저하 가능

**Q: 하이퍼테이블 정말 필요한가?**
A: 시계열 데이터 최적화 목적이었음. 일반 테이블로 변경 가능

**Q: 다른 테이블도 문제인가?**
A: market_indices는 일반 테이블이므로 문제 없음. stock_prices만 해당
