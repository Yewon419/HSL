# 2025-10-28 작업 진행 보고서

**작성 일시**: 2025-10-28 14:30 KST
**상태**: 🟡 진행 중 (마지막 트랜잭션 격리 문제 해결 중)
**다음 실행자**: 사용자 또는 Claude

---

## 📋 오늘의 작업 요약

사용자의 명시적인 3가지 검증 요청에 대해 체계적으로 분석하고 원인을 파악했습니다.

### 요청사항
> "기존에 수집을 성공했던 DAG나 python프로그램을 확인해봐."
> 1. 모듈이 없어서 수집을 못하는 것은 예전에 해결했는데 다시 발생했다. 혹시 다른 것으로 계속 돌리고 있는 것은 아닌지?
> 2. 주가를 정말로 못가져오는가? 1건만이라도 가져와봐.
> 3. 주가는 정상적으로 가져오는데 DB저장이 안된다? 운영DB에 안들어가진다. 개발DB(F디스크)에도 안들어가진다? 기존에는 저장이 되던것이 왜 안될가.

---

## ✅ 검증 결과

### ✅ 검증 1: 모듈 누락 문제 (해결 완료)

**질문**: 로컬 환경과 Docker 환경 간 모듈 설치 상태 차이가 있는가?

**검증 방법**:
```bash
# 로컬 Python 확인
python -c "import pykrx; print('pykrx installed')"
→ ✅ Success

# Docker 컨테이너 확인
docker exec stock-airflow-scheduler python -c "import pykrx; print('pykrx installed')"
→ ❌ ModuleNotFoundError
```

**원인**:
- `docker-compose.yml`의 `_PIP_ADDITIONAL_REQUIREMENTS`에 pykrx 명시되어 있음
- 하지만 기존 Docker 이미지가 캐시되어 있어 재설치되지 않음
- 단순 `docker restart`로는 의존성 재설치 안 됨

**결론**:
- ✅ 로컬 Python 환경: pykrx 정상 설치
- ❌ Docker Airflow: pykrx 미설치 (재빌드 필요)
- ✅ 기존 수집 프로그램들 (collect_*.py)은 로컬 Python에서 직접 실행되므로 정상 작동

**기존 정상 프로그램**:
```
✅ /f/hhstock/collect_20251021.py
✅ /f/hhstock/backend/collect_20251020.py
✅ /f/hhstock/stock-trading-system/backend/collect.py
```

---

### ✅ 검증 2: 데이터 수집 가능성 (해결 완료)

**질문**: pykrx API가 정말로 데이터를 가져올 수 없는가?

**검증 코드**:
```python
from pykrx import stock as pykrx_stock
import pandas as pd
from datetime import date

# 1단계: 종목 목록 조회
kospi = pykrx_stock.get_market_ticker_list(market="KOSPI", date="20251028")
kosdaq = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date="20251028")
print(f"KOSPI: {len(kospi)}, KOSDAQ: {len(kosdaq)}")
→ KOSPI: 958개 ✅, KOSDAQ: 1,801개 ✅

# 2단계: 1건 데이터 수집 테스트
ticker = "095570"
df = pykrx_stock.get_market_ohlcv("20251028", "20251028", ticker)
print(df)
→ 데이터 수집 성공 ✅
```

**수집 결과** (ticker 095570, 2025-10-28):
| 항목 | 값 |
|------|-----|
| 시가 | 4,350원 |
| 고가 | 4,430원 |
| 저가 | 4,295원 |
| 종가 | 4,405원 |
| 거래량 | 213,674주 |

**결론**:
- ✅ KOSPI: 958개 종목 수집 가능
- ✅ KOSDAQ: 1,801개 종목 수집 가능
- ✅ 개별 주가 데이터 수집 가능
- **문제는 저장 단계에 있음** (다음 검증에서 상세 분석)

---

### 🔴 검증 3: DB 저장 실패 원인 분석 (진행 중)

**질문**: 기존에는 저장되던데 왜 지금은 저장이 안 되는가?

**현재 데이터베이스 상태**:
```sql
SELECT COUNT(*) FROM stock_prices;
→ 3,040,694행

SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-28';
→ 0행 (실패)

SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-26';
→ 2,762행 (정상)
```

**근본 원인**: **TimescaleDB 청크(Chunk) 손상**

#### 문제의 구조:
```
1단계: 2025-10-28 데이터 삽입 시도
  ↓
2단계: TimescaleDB가 자동으로 _hyper_1_XX_chunk 생성
  ↓
3단계: INSERT 중 오류 발생 (외래키 제약, 메타데이터 문제 등)
  ↓
4단계: 트랜잭션 롤백
  ↓
5단계: 청크는 남아있음 (고아 청크)
  ↓
6단계: 재시도 시 "relation already exists" 오류
```

**발생한 오류들** (시간순):
1. `dimension_slice_pkey` 제약 조건 오류
2. `DuplicateTable: relation "_hyper_1_XX_chunk" already exists`
3. `InFailedSqlTransaction: current transaction is aborted`

---

## 🔧 구현된 해결책 (진행 상황)

### 시도 1: ❌ UPSERT 패턴 (INSERT ... ON CONFLICT)
```python
cursor.executemany("""
    INSERT INTO stock_prices (...)
    VALUES (...)
    ON CONFLICT (ticker, date) DO UPDATE SET ...
""", insert_data)
```
**실패 이유**: TimescaleDB 메타데이터 생성 트리거 → 고아 청크 누적

### 시도 2: ❌ 임시 테이블 방식
```python
# 1. CREATE TEMP TABLE temp_prices
# 2. INSERT INTO temp_prices
# 3. DELETE FROM stock_prices
# 4. INSERT INTO stock_prices SELECT FROM temp_prices
```
**실패 이유**: DELETE 작업 자체가 청크 메타데이터 문제 유발

### 시도 3: ⏳ SQLAlchemy 단일 행 삽입 (현재 진행 중)
```python
Session = sessionmaker(bind=engine)
session = Session()

for _, row in normalized_df.iterrows():
    query = text("""
        INSERT INTO stock_prices (...)
        VALUES (:ticker, :date, ...)
    """)
    try:
        session.execute(query, {...})
    except Exception as e:
        if 'unique constraint' in str(e).lower():
            continue  # 중복 무시하고 계속
        else:
            raise
session.commit()
```

**진행 상황**:
- ✅ 코드 구현 완료
- ✅ Docker에 파일 복사 완료
- ⏳ 실행 결과: 새로운 오류 발생
  ```
  InFailedSqlTransaction: current transaction is aborted,
  commands ignored until end of transaction block
  ```

**다음 수정 방향**:
- 각 행마다 개별 세션 생성 (연결 격리)
- 또는 per-row 자동 커밋 활성화

---

## 📝 수정된 파일 목록

### 1. `F:\hhstock\stock-trading-system\airflow\dags\common_functions.py`

**수정 부분 1**: `fetch_stock_prices_api()` (라인 62-130)
- ✅ KOSPI + KOSDAQ 별도 수집 추가
- ✅ 데이터베이스 유효한 종목 필터링 추가
- 예상 결과: 958개 → 2,759개 (약 190% 증가)

**수정 부분 2**: `save_stock_prices()` (라인 220-275)
- ❌ UPSERT 패턴 → 실패
- ❌ 임시 테이블 방식 → 실패
- ⏳ SQLAlchemy 단일 행 삽입 → 진행 중 (트랜잭션 격리 문제)

### 2. `F:\hhstock\stock-trading-system\airflow\dags\daily_collection_dag.py`

**수정 부분**: `fetch_and_save_stock_prices()` (라인 143)
```python
# Before:
prices_df = fetch_stock_prices_api(target_date)

# After:
prices_df = fetch_stock_prices_api(target_date, engine)
```

---

## 🚀 내일 실행해야 할 작업

### 우선순위 1: 트랜잭션 격리 문제 해결 (긴급)

**문제**: `InFailedSqlTransaction: current transaction is aborted`

**원인**: 한 세션에서 첫 행 실패 후 이후 행들이 모두 실패

**해결책**:
```python
# 각 행마다 개별 세션 생성
for _, row in normalized_df.iterrows():
    session = Session()  # 새 세션 생성
    try:
        query = text("INSERT INTO stock_prices ...")
        session.execute(query, {...})
        session.commit()
    except Exception as e:
        session.rollback()
        if 'unique constraint' not in str(e).lower():
            logger.warning(f"Failed to insert {row['ticker']}")
            continue
    finally:
        session.close()
```

### 우선순위 2: 테스트 실행 (검증)

```bash
# 1단계: Docker 재시작 및 코드 복사
docker cp /f/hhstock/stock-trading-system/airflow/dags/common_functions.py stock-airflow-scheduler:/opt/airflow/dags/
docker restart stock-airflow-scheduler
sleep 15

# 2단계: DAG 테스트 실행
docker exec stock-airflow-scheduler airflow dags test daily_collection_dag 2025-10-28

# 3단계: 결과 확인
# 기대: price_status = 'success', 950개 이상 저장됨
docker exec stock-db psql -U admin -d stocktrading -c "
  SELECT COUNT(*) as total_rows FROM stock_prices WHERE date = '2025-10-28';"
```

### 우선순위 3: Docker pykrx 모듈 설치 (장기)

```bash
cd /f/hhstock/stock-trading-system
docker-compose down
docker-compose build --no-cache  # 이미지 재빌드 (pykrx 포함)
docker-compose up -d
```

### 우선순위 4: 최종 검증

**체크리스트**:
- [ ] 2025-10-28 데이터 950개 이상 저장 확인
- [ ] collection_log status = 'success' 확인
- [ ] 2025-10-29 자동 스케줄 실행 확인 (19:25 KST)
- [ ] 지표 계산 성공 여부 확인

---

## 📊 현재 코드 상태

### ✅ 완료된 수정

```
stock-trading-system/airflow/dags/
├── common_functions.py
│   ├── Line 62-130: KOSPI+KOSDAQ 수집 ✅
│   ├── Line 143: engine 파라미터 전달 ✅
│   └── Line 220-275: SQLAlchemy 단일행 삽입 ⏳ (진행 중)
└── daily_collection_dag.py
    └── Line 143: engine 파라미터 전달 ✅
```

### ⏳ 진행 중

- SQLAlchemy 트랜잭션 격리 개선
- 각 행마다 개별 세션 생성 로직

---

## 🔍 디버깅 팁

### 로그 확인
```bash
# Docker Airflow 로그 실시간 모니터링
docker logs -f stock-airflow-scheduler 2>&1 | grep -E "(ERROR|save_stock_prices|Collected)"

# PostgreSQL 로그
docker logs stock-db 2>&1 | tail -50
```

### DB 상태 확인
```bash
# 2025-10-28 데이터 행 수
docker exec stock-db psql -U admin -d stocktrading -c \
  "SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-28';"

# 컬렉션 로그 확인
docker exec stock-db psql -U admin -d stocktrading -c \
  "SELECT collection_date, overall_status, price_status, price_count, error FROM collection_log WHERE collection_date = '2025-10-28';"

# 청크 상태 확인
docker exec stock-db psql -U admin -d stocktrading -c \
  "SELECT tablename FROM pg_tables WHERE tablename LIKE '_hyper_%' ORDER BY tablename DESC LIMIT 10;"
```

---

## 💡 핵심 교훈

1. **TimescaleDB의 자동 청킹**: 트랜잭션 실패 후 청크는 남아있음 → 고아 청크 누적
2. **ON CONFLICT의 한계**: TimescaleDB 메타데이터 생성을 막을 수 없음
3. **트랜잭션 격리**: 한 세션 내에서 첫 행 실패 시 이후 모든 행 실패
4. **개별 연결의 중요성**: 각 행마다 개별 커밋으로 격리 수준 상향

---

## ⏭️ 다음 단계

1. **즉시** (5분): SQLAlchemy 코드에서 각 행마다 개별 세션 생성으로 수정
2. **다음** (15분): Docker 파일 복사 및 DAG 테스트 실행
3. **검증** (10분): DB에 데이터 저장 여부 확인
4. **모니터링** (지속): 2025-10-29 19:25 자동 스케줄 실행 모니터링

---

**최종 상태**: 🟡 마지막 트랜잭션 격리 문제만 해결하면 완료 예상
