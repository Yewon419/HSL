# 시스템 상태 및 조치 계획 - 2025-10-28

**작성 일시**: 2025-10-28 22:30 KST
**최종 업데이트**: 금일 11:00 GMT+9

---

## 📊 현재 시스템 상태

### 해결된 문제 ✅

| 문제 | 상태 | 해결 방법 |
|------|------|---------|
| 데이터베이스 연결 오류 | ✅ 완료 | 192.168.219.103 운영DB로 변경 (common_functions.py line 24) |
| Airflow 종속성 부족 | ✅ 완료 | pykrx, pytz 추가 (docker-compose.yml) |
| 타임존 오류 | ✅ 완료 | UTC → KST 변경 (daily_collection_dag.py) |
| SQL 문법 오류 | ✅ 완료 | 트레일링 쉼표 제거 |

### 미해결 문제 🔴

| 문제 | 원인 | 영향 | 우선순위 |
|------|------|------|---------|
| 종목 수 부족 | get_market_ticker_list() 기본값 = KOSPI만 | 1,801개(65%) 누락 | 🔴 높음 |
| TimescaleDB 제약 조건 | dimension_slice 메타데이터 충돌 | 주가 저장 불가 | 🔴 높음 |

---

## 🎯 즉시 조치 방안 (Priority 1)

### 1번: KOSDAQ 종목 수집 추가 (30분) ⭐⭐⭐⭐⭐

**파일**: `stock-trading-system/airflow/dags/common_functions.py`
**현재 라인**: ~65번 (fetch_stock_prices_api 함수)

#### 현재 코드
```python
tickers = pykrx_stock.get_market_ticker_list(date=date_str)
```

#### 수정 코드
```python
kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
tickers = list(set(kospi_tickers) | set(kosdaq_tickers))
# 결과: 958개 + 1,801개 = 2,759개 (중복 제거 후)
```

**예상 효과**: 955개 → 2,759개 (약 190% 증가)

---

### 2번: TimescaleDB 제약 조건 해결 (15분 + 20분 테스트)

**권장**: 방법 3 (UPSERT 방식)

#### 파일: `stock-trading-system/airflow/dags/common_functions.py`
#### 라인: ~198번 (save_stock_prices 함수)

#### 핵심 변경: DELETE → UPSERT

```python
# 변경 전
cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))
for row in prices:
    cursor.execute("INSERT INTO ...")

# 변경 후 (UPSERT)
cursor.executemany("""
    INSERT INTO stock_prices (ticker, date, ...)
    VALUES (%s, %s, ...)
    ON CONFLICT (ticker, date) DO UPDATE SET ...
""", insert_data)
```

**예상 효과**:
- 현재: 주가 저장 실패 (dimension_slice 충돌)
- 수정 후: 모든 주가 저장 성공 ✅

---

## 📅 권장 조치 일정

### 🟢 **오늘 (2025-10-28) - 지금부터 1시간**

#### Task 1: 방법 1 적용 (20분)
```
1. common_functions.py line 65 수정
2. KOSDAQ 명시적 지정 추가
3. Docker 재시작
4. DAG 재로드
```

#### Task 2: 방법 3 적용 (20분)
```
1. common_functions.py line 198 수정
2. UPSERT 문법으로 변경
3. Docker 재시작
4. 테스트 실행
```

#### Task 3: 테스트 (20분)
```
1. 2025-10-28 데이터 재수집 테스트
2. 2,759개 수집 여부 확인
3. 모든 데이터 저장 여부 확인
```

---

### 🟡 **내일 (2025-10-29) - 자동 스케줄**

#### Daily Collection DAG
- 시간: 19:25 KST (10:25 UTC)
- 기능: KOSPI + KOSDAQ 자동 수집 (2,759개)
- 저장: 모든 주가 저장 성공 예상

#### Technical Indicator DAG
- 시간: 20:50 KST (11:50 UTC)
- 기능: 기술 지표 자동 계산

---

### 🔵 **1주 후 (선택사항) - 장기 안정화**

#### 방법 2 적용: 주간 하이퍼테이블 유지보수
- 스케줄: 매주 일요일 자정
- 기능: 메타데이터 완전 정리
- 효과: 성능 최적화 + 장기 안정성

---

## 📋 구현 체크리스트

### Phase 1: 즉시 조치 (오늘 1시간 내)

- [ ] 코드 수정 계획 검토
  - [ ] common_functions.py line 65 (KOSDAQ 추가)
  - [ ] common_functions.py line 198 (UPSERT 변경)

- [ ] 코드 수정 실행
  - [ ] 파일 백업 생성
  - [ ] 두 줄 변경 적용
  - [ ] 문법 검증

- [ ] Docker 재시작
  - [ ] `docker restart stock-airflow-scheduler`
  - [ ] 5분 대기

- [ ] 테스트 실행
  - [ ] `docker exec stock-airflow-scheduler airflow dags test daily_collection_dag 2025-10-28`
  - [ ] 결과 확인

### Phase 2: 검증 (1시간 소요)

- [ ] 데이터 수집 확인
  - [ ] 2,759개 모두 수집 여부
  - [ ] 오류 없음 확인

- [ ] 데이터 저장 확인
  - [ ] stock_prices에 데이터 저장됨
  - [ ] 0개에서 2,759개 이상으로 변경

- [ ] 컬렉션 로그 확인
  - [ ] collection_log 상태 = 'success'
  - [ ] price_count = 2,759개 이상

### Phase 3: 모니터링 (지속)

- [ ] 내일 19:25 자동 DAG 실행 확인
- [ ] 지표 계산 성공 여부 확인
- [ ] 오류 로그 모니터링

---

## 🔧 상세 수정 가이드

### 수정 1: KOSDAQ 추가

**파일**: `F:\hhstock\stock-trading-system\airflow\dags\common_functions.py`

**라인**: ~65

**변경**:
```python
# Before
tickers = pykrx_stock.get_market_ticker_list(date=date_str)

# After
kospi = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
kosdaq = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
tickers = list(set(kospi) | set(kosdaq))
```

---

### 수정 2: UPSERT 구현

**파일**: `F:\hhstock\stock-trading-system\airflow\dags\common_functions.py`

**라인**: ~198 (save_stock_prices 함수)

**변경**:
```python
# Before
cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))
for _, row in prices_df.iterrows():
    cursor.execute("INSERT INTO stock_prices ... VALUES ...", {...})

# After
insert_data = [
    (row['ticker'], row['date'], row['open_price'], row['high_price'],
     row['low_price'], row['close_price'], row['volume'], row['created_at'])
    for _, row in prices_df.iterrows()
]

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

---

## 📊 예상 결과

### 수정 전 (현재)
```
2025-10-28 수집 결과:
├─ KOSPI 종목: 958개 수집
├─ KOSDAQ 종목: 미수집 (누락)
├─ 합계: 958개
├─ 저장: 실패 (dimension_slice 제약)
└─ 상태: partial (부분 실패)
```

### 수정 후 (예상)
```
2025-10-28 수집 결과:
├─ KOSPI 종목: 958개 수집
├─ KOSDAQ 종목: 1,801개 수집
├─ 합계: 2,759개
├─ 저장: 성공 (UPSERT 사용)
└─ 상태: success (전체 성공)
```

### 데이터량 증가
```
현재:    958개
수정 후: 2,759개
증가율:  188% ↑

일일 데이터: ~22MB → ~59MB
월간 데이터: ~660MB → ~1.8GB
```

---

## ⚠️ 주의사항

1. **수집 시간 증가**
   - 현재: 약 5분
   - 수정 후: 약 10-15분
   → 19:25 시작 시 약 19:40 완료 예상

2. **API 호출 제한**
   - pykrx는 대량 호출 시 제한 있을 수 있음
   - 테스트 후 확인 권장

3. **메모리 사용**
   - 2,759개 × 8칼럼 ≈ 22,000행
   - 메모리 ~30MB 필요 (충분함)

4. **저장 공간**
   - 현재: 1,257일분 × 958개 ≈ 1.2GB
   - 수정 후: 1,257일분 × 2,759개 ≈ 3.3GB
   - 운영DB 여유공간 확인 필요

---

## 📞 지원 문서

자세한 내용은 다음 문서를 참고하세요:

- **전체 상황**: start_hsl.md
- **종목 수 확대 방법**: DAILY_COLLECTION_FIX_20251028.md
  - 5가지 방법 상세 분석
  - 코드 예제
  - 로드맵

- **5가지 해결 방안 비교**: SOLUTION_COMPARISON_5METHODS.md
  - 각 방법의 개념도
  - 장단점 분석
  - 상황별 추천

- **TimescaleDB 제약 조건 해결**: TIMESCALEDB_SOLUTION_3METHODS.md
  - 근본 원인 분석
  - 3가지 해결 방법
  - 구현 코드

---

## 🚀 다음 단계 (사용자 확인 대기 중)

**아래 중 하나를 선택해주세요:**

1. ✅ **지금 바로 수정 진행**
   - 위 체크리스트 실행
   - 1시간 내 완료

2. ⏸️ **먼저 문서 검토**
   - TIMESCALEDB_SOLUTION_3METHODS.md 정독
   - 3가지 방법 중 선택

3. ❓ **추가 질문**
   - 구현 과정에서 불명한 부분 질문

---

## 📝 작업 기록

**2025-10-28 22:30 KST**
- TimescaleDB 제약 조건 분석 완료
- 3가지 해결 방법 제시
- 최종 조치 계획 수립

**2025-10-28 22:00 KST**
- 955개 문제 원인 분석 완료
- 5가지 해결 방안 문서화

**2025-10-28 13:00 KST**
- 데이터베이스 연결 문제 해결
- 운영DB(192.168.219.103) 정상 연결 확인

**이전**
- Airflow DAG 구성 완료
- Docker 기본 설정 완료
