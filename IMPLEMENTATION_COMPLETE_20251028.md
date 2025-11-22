# 주가 수집 시스템 개선 구현 완료 - 2025-10-28

**작성 일시**: 2025-10-28 22:45 KST
**최종 상태**: 구현 완료, Docker 리로드 진행 중

---

## 1. 문제 분석 및 해결

### 문제 1: 종목 수 부족 (958개 → 2,759개)

**원인**:
- `pykrx_stock.get_market_ticker_list()`의 기본 파라미터가 `market="KOSPI"`만 지정
- KOSDAQ 종목 1,801개 누락

**해결책** (Method 1 구현 - 권장):
- KOSPI와 KOSDAQ을 별도로 수집
- 유효한 종목만 필터링하여 외래키 제약 조건 에러 방지

### 문제 2: TimescaleDB 제약 조건 충돌

**원인**:
- DELETE → INSERT 패턴에서 DELETE는 데이터만 지우고 metadata는 유지
- TimescaleDB의 `dimension_slice_pkey` 충돌 발생
- 반복 실행 시 동일 ID로 insert 시도 → PK 중복 에러

**해결책** (Method 3 구현 - 권장):
- UPSERT 패턴으로 변경: `ON CONFLICT (ticker, date) DO UPDATE`
- DELETE 제거하여 metadata 충돌 방지

### 문제 3: 존재하지 않는 종목의 외래키 에러

**원인**:
- pykrx가 반환하는 종목 중 일부(예: ticker '317450')가 stocks 마스터 테이블에 없음
- INSERT 시 외래키 제약 조건 위반

**해결책**:
- stocks 테이블의 유효한 종목 목록을 먼저 로드
- pykrx에서 수집한 종목을 필터링하여 유효한 것만 DB에 저장

---

## 2. 구현 변경 사항

### 파일 1: `stock-trading-system/airflow/dags/common_functions.py`

#### 함수: `fetch_stock_prices_api()` (Line 62-130)

**변경점**:
1. **KOSPI + KOSDAQ 별도 수집**
   ```python
   kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
   kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
   all_tickers = list(set(kospi_tickers) | set(kosdaq_tickers))
   ```

2. **유효한 종목 필터링**
   ```python
   # Get valid tickers from database
   cursor.execute("SELECT ticker FROM stocks ORDER BY ticker")
   valid_tickers = set([row[0] for row in cursor.fetchall()])

   # Filter
   valid_tickers_for_date = [t for t in all_tickers if t in valid_tickers]
   ```

**예상 결과**:
- KOSPI: 958개
- KOSDAQ: 1,801개
- 합계: 2,759개 (중복 제거 후)
- 유효한 종목만 처리 → 외래키 에러 제거

#### 함수: `save_stock_prices()` (Line 220-252)

**변경점**:
1. **DELETE 제거**
   ```python
   # Before:
   cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))

   # After: (제거됨)
   ```

2. **UPSERT 패턴 구현**
   ```python
   cursor.executemany("""
       INSERT INTO stock_prices
       (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
       ON CONFLICT (ticker, date) DO UPDATE SET
           open_price = EXCLUDED.open_price,
           high_price = EXCLUDED.high_price,
           low_price = EXCLUDED.low_price,
           close_price = EXCLUDED.close_price,
           volume = EXCLUDED.volume,
           created_at = EXCLUDED.created_at
   """, insert_data)
   ```

**예상 결과**:
- 중복 데이터는 자동으로 UPDATE
- TimescaleDB metadata 충돌 제거
- dimension_slice_pkey 에러 해결

### 파일 2: `stock-trading-system/airflow/dags/daily_collection_dag.py`

#### 함수: `fetch_and_save_stock_prices()` (Line 143)

**변경점**:
```python
# Before:
prices_df = fetch_stock_prices_api(target_date)

# After:
prices_df = fetch_stock_prices_api(target_date, engine)
```

---

## 3. 예상 결과 (수정 후)

### 데이터 수집량
```
현재:     958개 (KOSPI만)
수정후:  2,759개 (KOSPI + KOSDAQ)
증가율:  188% ↑
```

### 일일 데이터량
```
현재:    ~10-15 MB
수정후:  ~25-40 MB
```

### 에러 처리
- ✅ 외래키 제약 조건 에러 해결
- ✅ TimescaleDB dimension_slice_pkey 충돌 해결
- ✅ ON CONFLICT로 중복 데이터 자동 처리

---

## 4. 테스트 현황

### 코드 검증
- ✅ fetch_stock_prices_api() - KOSPI/KOSDAQ 필터링 추가
- ✅ save_stock_prices() - UPSERT 패턴 구현
- ✅ daily_collection_dag.py - engine 파라미터 전달

### 다음 테스트
- Docker 컨테이너 Python 캐시 재로드 (진행 중)
- DAG 테스트 실행: `airflow dags test daily_collection_dag 2025-10-28`
- 결과 확인:
  - 수집된 종목 수: 2,759개 인지 확인
  - stock_prices 테이블에 데이터 저장 여부 확인
  - collection_log의 status = 'success' 확인

---

## 5. 스케줄 및 다음 단계

### 즉시 (지금)
1. ✅ 코드 수정 완료
2. ⏳ Docker 캐시 재로드 완료 (scheduler restart)
3. 다음: DAG 테스트 실행 및 결과 검증

### 내일 (2025-10-29)
- 19:25 KST: 자동 daily_collection_dag 실행
- 기대 결과: 2,759개 수집, 모두 저장 성공

### 선택사항 (1주 후)
- Method 2 (주간 hypertable 정리) 적용 고려
- 장기 안정성 강화

---

## 6. 파일 목록

| 파일 | 변경사항 | 상태 |
|------|---------|------|
| `common_functions.py:62-130` | fetch_stock_prices_api - KOSDAQ 추가 | ✅ 완료 |
| `common_functions.py:220-252` | save_stock_prices - UPSERT 패턴 | ✅ 완료 |
| `daily_collection_dag.py:143` | engine 파라미터 추가 | ✅ 완료 |

---

## 7. 주의사항

### 성능 영향
- 수집 시간: 5분 → 10-15분 증가
- API 호출: 958회 → ~2,700회 증가
- 메모리: ~30MB 필요 (충분)

### 저장 공간
- 현재: 1,257일분 × 958개 ≈ 1.2GB
- 수정후: 1,257일분 × 2,759개 ≈ 3.3GB
- 운영DB 여유공간 확인 필요 (현재 충분함)

---

## 8. 추가 자료

- **5가지 해결방안 비교**: SOLUTION_COMPARISON_5METHODS.md
- **TimescaleDB 3가지 해결방안**: TIMESCALEDB_SOLUTION_3METHODS.md
- **시스템 상태 및 조치 계획**: SYSTEM_STATUS_AND_ACTION_PLAN_20251028.md

---

**상태**: 🟡 구현 완료, Docker 리로드 진행 중
**다음 액션**: DAG 테스트 실행 및 결과 검증
