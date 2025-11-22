# 한국 주식 거래 데이터 수동 수집 매뉴얼

> **작성일**: 2025-10-22
> **최종 검증**: 2025-10-22 (주가 2,761개, 지표 2,775개 완전 수집)
> **용도**: 시스템 다운타임, 데이터 누락 시 수동 복구

---

## 📋 목차

1. [사전 확인 체크리스트](#1-사전-확인-체크리스트)
2. [데이터베이스 현황 확인](#2-데이터베이스-현황-확인)
3. [수집 프로그램 준비](#3-수집-프로그램-준비)
4. [수집 프로세스](#4-수집-프로세스)
5. [검증 및 완료](#5-검증-및-완료)
6. [문제 해결](#6-문제-해결)

---

## 1. 사전 확인 체크리스트

### 1.1 현재 날짜 및 시간 확인

**⚠️ 중요**: Claude는 절대로 날짜를 추론해서는 안 됩니다. 시스템 명령어로 확인하세요.

```bash
# Windows PowerShell
powershell -Command "Get-Date -Format 'yyyy-MM-dd dddd HH:mm:ss'"

# 예상 출력:
# 2025-10-22 수요일 20:31:45
```

**확인할 정보**:
- ✅ 현재 날짜: `__________`
- ✅ 현재 요일: `__________` (월/화/수/목/금/토/일)
- ✅ 현재 시간: `__________` (HH:mm:ss)
- ✅ 시간대: 한국 시간 (KST, UTC+9)

### 1.2 한국 주식 시장 운영 상태 확인

#### 평일/주말 구분

| 요일 | 장 상태 | 수집 필요 |
|------|--------|---------|
| 월~금 | 개장 | ✅ 필요 |
| 토 | 휴장 | ❌ 불필요 |
| 일 | 휴장 | ❌ 불필요 |

**현재 요일**: `__________` → 장 상태: `__________`

#### 공휴일 확인

```
2025년 한국 주식시장 공휴일:
- 01-01: 신정
- 02-10~12: 설 연휴
- 03-01: 삼일절
- 04-10: 국회의원 선거일
- 05-05: 어린이날
- 05-15: 부처님 오신 날
- 06-06: 현충일
- 08-15: 광복절
- 09-16~18: 추석 연휴
- 10-03: 개천절
- 10-09: 한글날
- 12-25: 크리스마스
```

**현재 날짜가 공휴일인가?**: ☐ Yes / ☐ No

### 1.3 장 종료 시간 확인

```
한국 주식시장 거래 시간:
- 개장 시간: 09:00 KST
- 장 마감 시간: 15:30 KST (오후 3시 30분)
- 데이터 수집 권장 시간: 15:30 이후 (장 마감 후)
```

**현재 시간이 15:30 이후인가?**: ☐ Yes / ☐ No

### 1.4 사전 확인 결과

```
✅ 평일 && 15:30 이후 → 진행하기
❌ 주말 또는 공휴일 → 수집 중단
❌ 15:30 이전 → 시간 대기
```

**수집 진행 여부**: ☐ 진행 / ☐ 중단

---

## 2. 데이터베이스 현황 확인

### 2.1 Docker 컨테이너 상태 확인

```bash
cd stock-trading-system
docker-compose ps
```

**필수 컨테이너** (모두 `Up` 상태여야 함):
- ☐ stock-db (PostgreSQL/TimescaleDB)
- ☐ stock-backend (FastAPI)
- ☐ stock-redis
- ☐ stock-airflow-scheduler
- ☐ stock-airflow-webserver

### 2.2 데이터베이스 접속 확인

```bash
docker exec stock-db psql -U admin -d stocktrading -c "SELECT version();"
```

**예상 출력**:
```
PostgreSQL 15.x on x86_64-pc-linux-gnu, ...
(1 row)
```

### 2.3 대상 날짜의 데이터 현황 조회

**변수 설정** (중요!):
```bash
TARGET_DATE="2025-10-22"  # 수집하려는 날짜 (YYYY-MM-DD 형식)
```

**현황 확인 쿼리**:
```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    '$TARGET_DATE' as target_date,
    (SELECT COUNT(*) FROM stock_prices WHERE date = '$TARGET_DATE'::date) as price_count,
    (SELECT COUNT(DISTINCT ticker) FROM stock_prices WHERE date = '$TARGET_DATE'::date) as price_tickers,
    (SELECT COUNT(*) FROM technical_indicators WHERE date = '$TARGET_DATE'::date) as indicator_count,
    (SELECT COUNT(DISTINCT ticker) FROM technical_indicators WHERE date = '$TARGET_DATE'::date) as indicator_tickers,
    (SELECT COUNT(*) FROM market_indices WHERE date = '$TARGET_DATE'::date) as indices_count;
"
```

**예상 출력** (완전 수집된 경우):
```
 target_date |  price_count | price_tickers | indicator_count | indicator_tickers | indices_count
-----------+-----------+-----------+-----------+-----------+-----------
 2025-10-22 |      2761 |      2761 |      2775 |      2775 |         2
(1 row)
```

### 2.4 어제 데이터와 비교 (누락 확인)

```bash
TARGET_DATE="2025-10-22"
YESTERDAY=$(date -d "$TARGET_DATE -1 day" +%Y-%m-%d)

docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    'Yesterday' as day, COUNT(DISTINCT ticker) as tickers
FROM stock_prices
WHERE date = '$YESTERDAY'::date
UNION ALL
SELECT
    'Today' as day, COUNT(DISTINCT ticker) as tickers
FROM stock_prices
WHERE date = '$TARGET_DATE'::date
ORDER BY day;
"
```

**결과 해석**:
- Yesterday = Today → 완벽 동기화 ✅
- Yesterday > Today → **누락 발생** ⚠️ (아래의 Step 4 실행)

### 2.5 누락된 티커 조회 (문제 발생 시)

```bash
TARGET_DATE="2025-10-22"
YESTERDAY=$(date -d "$TARGET_DATE -1 day" +%Y-%m-%d)

docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(*) as missing_tickers
FROM (
    SELECT t1.ticker
    FROM (SELECT DISTINCT ticker FROM stock_prices WHERE date = '$YESTERDAY'::date) t1
    LEFT JOIN (SELECT DISTINCT ticker FROM stock_prices WHERE date = '$TARGET_DATE'::date) t2
    ON t1.ticker = t2.ticker
    WHERE t2.ticker IS NULL
) sub;
"
```

**결과 기록**:
- 누락된 티커 수: `__________` 개

---

## 3. 수집 프로그램 준비

### 3.1 필수 테이블 구조 확인

#### stock_prices 테이블

```bash
docker exec stock-db psql -U admin -d stocktrading -c "\d stock_prices"
```

**필수 컬럼**:
- ☐ ticker (varchar, PK)
- ☐ date (date, PK)
- ☐ open_price (numeric)
- ☐ high_price (numeric)
- ☐ low_price (numeric)
- ☐ close_price (numeric)
- ☐ volume (bigint)
- ☐ created_at (timestamp)

#### technical_indicators 테이블

```bash
docker exec stock-db psql -U admin -d stocktrading -c "\d technical_indicators"
```

**필수 컬럼** (컬럼명 정확히 확인):
- ☐ ticker (varchar, PK)
- ☐ date (date, PK)
- ☐ rsi (numeric)
- ☐ macd (numeric)
- ☐ macd_signal (numeric)
- ☐ **ma_20** ⚠️ (NOT sma_20)
- ☐ **ma_50** ⚠️ (NOT sma_50)
- ☐ **ma_200** ⚠️ (NOT sma_200)
- ☐ **bollinger_upper** ⚠️ (NOT bb_upper)
- ☐ **bollinger_lower** ⚠️ (NOT bb_lower)
- ☐ created_at (timestamp)

#### market_indices 테이블

```bash
docker exec stock-db psql -U admin -d stocktrading -c "\d market_indices"
```

**필수 컬럼**:
- ☐ index_name (varchar, PK)
- ☐ date (date, PK)
- ☐ open_value (numeric)
- ☐ high_value (numeric)
- ☐ low_value (numeric)
- ☐ close_value (numeric)
- ☐ volume (bigint)
- ☐ created_at (timestamp)

### 3.2 Python 환경 확인

```bash
docker exec stock-backend python -c "import pykrx; print('pykrx version:', pykrx.__version__)"
```

**필수 라이브러리**:
- ☐ pykrx (한국 주식 데이터 API)
- ☐ pandas
- ☐ numpy
- ☐ sqlalchemy
- ☐ psycopg2

### 3.3 Backend 컨테이너 상태 확인

```bash
docker exec stock-backend python -c "from database import SessionLocal; db = SessionLocal(); print('✅ Database connection OK'); db.close()"
```

**예상 결과**: `✅ Database connection OK`

---

## 4. 수집 프로세스

### 4.1 Step 1: 주가 데이터 수집

#### 프로그램 다운로드 및 실행

**경로**: `F:\hhstock\collect_stock_data_YYYYMMDD.py`

```bash
# 변수 설정 (매우 중요!)
TARGET_DATE="2025-10-22"

# 스크립트 생성 및 복사
pwsh -c "
\$date = '$TARGET_DATE'.Replace('-', '')
Copy-Item 'F:\hhstock\collect_stock_data_20251022.py' -Destination "F:\hhstock\collect_stock_data_\${date}.py"
"

# 컨테이너로 복사
docker cp "F:\hhstock\collect_stock_data_YYYYMMDD.py" stock-backend:/app/

# 수집 실행
docker exec stock-backend python /app/collect_stock_data_YYYYMMDD.py
```

#### 변수 확인 (중요!)

수집 스크립트 내 다음 변수가 **정확한 날짜**로 설정되어 있어야 합니다:

```python
TARGET_DATE = date(2025, 10, 22)  # 년, 월, 일 정확히 설정
DATE_STR = TARGET_DATE.strftime('%Y%m%d')  # "20251022"
```

#### 수집 프로세스 모니터링

```
진행 상황 확인:
[200/959] 진행 중... (성공: 200, 오류: 0)
[400/959] 진행 중... (성공: 400, 오류: 0)
...
✅ 주가 수집 완료: 949 종목 저장됨
데이터베이스 확인: 959 개의 주가 레코드
```

**성공 기준**:
- ✅ 최소 2,500개 이상의 주가 저장
- ✅ 오류율 < 5%
- ✅ "주가 수집 완료" 메시지 표시

### 4.2 Step 2: 기술적 지표 계산

#### 프로그램 구조

**포함된 함수**:
- `calculate_rsi()` - RSI (14-period)
- `calculate_macd()` - MACD (12, 26, 9)
- `calculate_sma()` - Simple Moving Average (20, 50, 200)
- `calculate_bollinger_bands()` - Bollinger Bands (20-period, 2 std dev)

#### 실행

```bash
docker exec stock-backend python /app/collect_stock_data_YYYYMMDD.py
```

**프로세스 흐름**:
```
1. 주가 데이터 수집 (위 Step 1과 동일)
2. 기술적 지표 계산 시작
   └─ 로드된 주가 데이터: ~3,070,000 행
   └─ 처리할 티커: ~2,779 개
3. 각 티커별 지표 계산
   └─ RSI, MACD, SMA 20/50/200, Bollinger Bands
4. 지표 DB 저장
   └─ ma_20, ma_50, ma_200 (주의: sma_* 아님!)
   └─ bollinger_upper, bollinger_lower
```

#### 예상 출력

```
[200/2779] 진행 중... (처리: 200)
[400/2779] 진행 중... (처리: 398)
...
[2600/2779] 진행 중... (처리: 2597)

[200/2775] 저장 중...
[400/2775] 저장 중...
...

✅ 기술적 지표 계산 완료: 2775 종목 저장됨
```

**성공 기준**:
- ✅ 최소 2,500개 이상의 지표 저장
- ✅ "기술적 지표 계산 완료" 메시지 표시

### 4.3 Step 3: 시장 지수 수집 (선택사항)

**상태**: 현재 pykrx API 이슈로 인해 스킵됨

```python
# 수집 예정 지수
KOSPI  - 한국종합주가지수
KOSDAQ - 코스닥 지수
```

---

## 5. 검증 및 완료

### 5.1 최종 데이터 확인

```bash
TARGET_DATE="2025-10-22"

docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    '$TARGET_DATE' as date,
    (SELECT COUNT(*) FROM stock_prices WHERE date = '$TARGET_DATE'::date) as prices,
    (SELECT COUNT(DISTINCT ticker) FROM stock_prices WHERE date = '$TARGET_DATE'::date) as price_tickers,
    (SELECT COUNT(*) FROM technical_indicators WHERE date = '$TARGET_DATE'::date) as indicators,
    (SELECT COUNT(DISTINCT ticker) FROM technical_indicators WHERE date = '$TARGET_DATE'::date) as indicator_tickers;
"
```

### 5.2 어제와의 동기화 검증

```bash
TARGET_DATE="2025-10-22"
YESTERDAY=$(date -d "$TARGET_DATE -1 day" +%Y-%m-%d)

docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    '$YESTERDAY' as yesterday, COUNT(DISTINCT ticker) as tickers FROM stock_prices WHERE date = '$YESTERDAY'::date
UNION ALL
SELECT
    '$TARGET_DATE' as today, COUNT(DISTINCT ticker) as tickers FROM stock_prices WHERE date = '$TARGET_DATE'::date
ORDER BY 1 DESC;
"
```

**결과 해석**:
- 동일한 수 → ✅ 완벽 동기화
- 어제 > 오늘 → ❌ 누락 존재 (Step 4 반복)

### 5.3 품질 검증

#### 개별 티커 샘플 확인

```bash
TARGET_DATE="2025-10-22"

docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    sp.ticker,
    sp.date,
    sp.close_price,
    ti.rsi,
    ti.ma_20,
    ti.ma_50,
    ti.ma_200,
    ti.bollinger_upper,
    ti.bollinger_lower
FROM stock_prices sp
LEFT JOIN technical_indicators ti ON sp.ticker = ti.ticker AND sp.date = ti.date
WHERE sp.date = '$TARGET_DATE'::date
LIMIT 10;
"
```

**확인 항목**:
- ☐ close_price 값이 0이 아닌가?
- ☐ RSI가 0~100 범위인가?
- ☐ MA 값들이 정상인가?
- ☐ Bollinger 밴드가 제대로 계산되었는가?

#### NULL 값 확인

```bash
TARGET_DATE="2025-10-22"

docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    COUNT(*) as null_count
FROM technical_indicators
WHERE date = '$TARGET_DATE'::date
AND (rsi IS NULL OR ma_20 IS NULL OR ma_50 IS NULL OR ma_200 IS NULL);
"
```

**결과**:
- 0 또는 매우 적은 수 → ✅ 정상
- 많은 수 → ⚠️ 추가 확인 필요

### 5.4 최종 체크리스트

```
✅ 주가 데이터 완성도
   └─ 어제와 동일한 수의 티커 수집
   └─ 최소 2,700개 이상의 주가 데이터

✅ 지표 데이터 완성도
   └─ 최소 2,750개 이상의 지표 데이터
   └─ NULL 값 최소화

✅ 데이터 품질
   └─ 정상적인 OHLCV 값 범위
   └─ 정상적인 지표 값 범위

✅ 시스템 정상성
   └─ 모든 Docker 컨테이너 운영 중
   └─ 데이터베이스 접속 성공
```

---

## 6. 문제 해결

### 6.1 주가 데이터 수집 실패

#### 증상: "No stock prices fetched"

**원인 분석**:
```bash
# 1. 날짜 확인
date '+%Y-%m-%d'  # 실제 오늘 날짜

# 2. 주말/공휴일 확인
# 토요일 또는 일요일이거나 공휴일인가?

# 3. 장 시간 확인
date '+%H:%M'  # 현재 시간이 15:30 이후인가?
```

**해결 방법**:
1. 평일 15:30 이후에 다시 시도
2. 날짜가 정확하게 설정되었는지 확인
3. pykrx API 상태 확인

#### 증상: "Column undefined error"

**원인**: 데이터베이스 테이블 컬럼명 불일치

```python
# ❌ 잘못된 컬럼명
'sma_20', 'sma_50', 'sma_200'
'bb_upper', 'bb_lower'

# ✅ 올바른 컬럼명
'ma_20', 'ma_50', 'ma_200'
'bollinger_upper', 'bollinger_lower'
```

**해결 방법**: 스크립트에서 컬럼명 수정 (위의 3.1 참고)

### 6.2 지표 계산 실패

#### 증상: "No indicators calculated"

**원인 분석**:
```bash
# 주가 데이터 확인
TARGET_DATE="2025-10-22"
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(*) FROM stock_prices WHERE date = '$TARGET_DATE'::date;
"
```

**결과가 0이면**: Step 1부터 다시 실행
**결과가 > 0이면**: 지표 계산 로그 확인

### 6.3 데이터베이스 연결 실패

#### 증상: "Could not connect to database"

```bash
# 1. 컨테이너 상태 확인
docker-compose ps | grep stock-db

# 2. 강제 재시작
docker-compose restart stock-db
docker-compose restart stock-backend

# 3. 네트워크 확인
docker network ls
```

### 6.4 누락된 데이터 탐지

```bash
TARGET_DATE="2025-10-22"
YESTERDAY=$(date -d "$TARGET_DATE -1 day" +%Y-%m-%d)

# 누락된 티커 목록 (상위 20개)
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT t1.ticker
FROM (SELECT DISTINCT ticker FROM stock_prices WHERE date = '$YESTERDAY'::date) t1
LEFT JOIN (SELECT DISTINCT ticker FROM stock_prices WHERE date = '$TARGET_DATE'::date) t2
ON t1.ticker = t2.ticker
WHERE t2.ticker IS NULL
ORDER BY t1.ticker
LIMIT 20;
"

# 누락된 티커 총 개수
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(*) as missing_tickers
FROM (
    SELECT t1.ticker FROM (SELECT DISTINCT ticker FROM stock_prices WHERE date = '$YESTERDAY'::date) t1
    LEFT JOIN (SELECT DISTINCT ticker FROM stock_prices WHERE date = '$TARGET_DATE'::date) t2
    ON t1.ticker = t2.ticker
    WHERE t2.ticker IS NULL
) sub;
"
```

**누락이 발생했다면**:
1. `collect_missing_tickers_20251022.py` 실행
2. `calculate_missing_indicators_20251022.py` 실행

---

## 📝 수집 기록 양식

각 수집 시마다 다음 정보를 기록하세요:

```
수집 일자: ____________________
수집 대상 날짜: ____________________
수집 시작 시간: ____________________

[Step 1: 주가 데이터]
수집된 티커: __________ 개
저장된 주가: __________ 개
오류율: __________ %
완료 시간: __________________

[Step 2: 기술지표]
계산된 티커: __________ 개
저장된 지표: __________ 개
완료 시간: __________________

[Step 3: 검증]
어제 티커 수: __________ 개
오늘 티커 수: __________ 개
동기화 상태: ☐ 완벽 / ☐ 부분 / ☐ 누락

[특이사항]
- _______________
- _______________

[최종 상태]
✅ 수집 완료 / ❌ 수집 실패 / ⚠️ 부분 수집
```

---

## 🔗 참고 자료

### 관련 파일

| 파일명 | 용도 |
|--------|------|
| `collect_stock_data_20251022.py` | 주가 + 지표 종합 수집 |
| `collect_missing_tickers_20251022.py` | 누락된 티커만 수집 |
| `calculate_missing_indicators_20251022.py` | 누락된 지표만 계산 |

### 스크립트 변수 설정 가이드

모든 스크립트에서 다음 변수를 정확하게 설정해야 합니다:

```python
# Python 스크립트
from datetime import date

TARGET_DATE = date(2025, 10, 22)  # 년, 월, 일 정확히
DATE_STR = TARGET_DATE.strftime('%Y%m%d')  # "20251022" 형식
```

```bash
# Bash 스크립트
TARGET_DATE="2025-10-22"  # YYYY-MM-DD 형식
DATE_STR=$(echo $TARGET_DATE | tr -d '-')  # "20251022"
```

### API 정보

**pykrx 라이브러리**:
- 한국 주식시장 데이터 제공
- 사용 함수:
  - `get_market_ticker_list(date)` - 거래소 전체 티커
  - `get_market_ohlcv(from_date, to_date, ticker)` - OHLCV 데이터

**지표 계산**:
- RSI: 상대강도지수 (0~100)
- MACD: 이동평균 수렴산산 (추세 추종)
- SMA: 단순이동평균 (20, 50, 200일)
- Bollinger Bands: 변동성 지표

---

## ⚠️ 주의사항

1. **날짜는 반드시 시스템 명령어로 확인**
   - Claude의 추론 금지
   - `Get-Date` 또는 `date` 명령어 사용

2. **테이블 컬럼명 정확히 확인**
   - `sma_20` ❌ → `ma_20` ✅
   - `bb_upper` ❌ → `bollinger_upper` ✅

3. **변수 설정 재확인**
   - TARGET_DATE = date(2025, 10, 22)
   - DATE_STR = "20251022"

4. **실행 전 Docker 상태 확인**
   - 모든 컨테이너가 Up 상태
   - 데이터베이스 접속 확인

5. **정상 수집 기준**
   - 주가: 2,700개 이상
   - 지표: 2,750개 이상
   - 어제와 동일한 티커 수

---

**최종 검증 일자**: 2025-10-22
**검증된 결과**: 주가 2,761개 ✅ / 지표 2,775개 ✅
**매뉴얼 버전**: v1.0
