# 한국 주식 데이터 수동 수집 - 리소스 가이드

> **작성일**: 2025-10-22
> **최종 검증**: 주가 2,761개 ✅ / 지표 2,775개 ✅
> **목적**: 시스템 다운타임, 데이터 누락 시 복구용 완전한 매뉴얼

---

## 📦 제공되는 리소스

### 1. 📖 문서

| 파일명 | 설명 | 용도 |
|--------|------|------|
| **MANUAL_DATA_COLLECTION_GUIDE.md** | 종합 수동 수집 매뉴얼 (600줄) | 🎯 **필독** - 전체 프로세스 이해 |
| **README_MANUAL_COLLECTION.md** (본 파일) | 리소스 네비게이션 및 빠른 시작 | 📍 현재 위치 안내 |

### 2. 🐍 Python 수집 프로그램

| 파일명 | 설명 | 사용 시점 |
|--------|------|---------|
| **TEMPLATE_collect_stock_data.py** | 재사용 가능한 통합 템플릿 | 매일 사용 |
| **collect_stock_data_20251022.py** | 2025-10-22 테스트 완료 버전 | 레퍼런스 |
| **collect_missing_tickers_20251022.py** | 누락된 티커만 수집 | 긴급 복구 |
| **calculate_missing_indicators_20251022.py** | 누락된 지표만 계산 | 긴급 복구 |

### 3. 📊 데이터베이스 검증

| 파일명 | 설명 | 용도 |
|--------|------|------|
| **QUICK_VERIFICATION_QUERIES.sql** | 8가지 검증 쿼리 모음 | 수집 후 검증 |

---

## 🚀 빠른 시작 (5분)

### Step 1: 기본 정보 확인 (1분)

```bash
# 현재 날짜 확인 (반드시 시스템 명령어 사용!)
powershell -Command "Get-Date -Format 'yyyy-MM-dd dddd HH:mm:ss'"

# 결과: 2025-10-22 수요일 20:31:45
```

✅ **확인 사항**:
- [ ] 평일(월~금)인가?
- [ ] 15:30 이후인가?
- [ ] 공휴일이 아닌가?

### Step 2: Docker 상태 확인 (1분)

```bash
cd stock-trading-system
docker-compose ps
```

✅ **필수 컨테이너** (모두 `Up` 상태):
- [ ] stock-db
- [ ] stock-backend
- [ ] stock-redis
- [ ] stock-airflow-scheduler

### Step 3: 데이터 수집 (3분)

```bash
# 방법 A: 자동으로 오늘 날짜 사용
docker cp TEMPLATE_collect_stock_data.py stock-backend:/app/
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py

# 방법 B: 특정 날짜 지정
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py --date 2025-10-22

# 방법 C: 주가만 수집 (지표 제외)
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py --skip-indicators

# 방법 D: 지표만 계산 (주가 제외)
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py --skip-prices
```

### Step 4: 검증 (1분)

```bash
# 결과 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    (SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-22'::date) as prices,
    (SELECT COUNT(*) FROM technical_indicators WHERE date = '2025-10-22'::date) as indicators;
"

# 결과 예시:
#  prices | indicators
# --------+------------
#    2761 |       2775
```

✅ **완료 기준**:
- [ ] 주가: 2,700개 이상
- [ ] 지표: 2,700개 이상

---

## 📚 상세 가이드

### 1️⃣ 완전한 프로세스 이해가 필요하다면

→ **MANUAL_DATA_COLLECTION_GUIDE.md** 읽기 (추천순서):

1. **1. 사전 확인 체크리스트** (필수)
   - 날짜/시간 확인
   - 평일/공휴일 확인
   - 장 시간 확인

2. **2. 데이터베이스 현황 확인** (필수)
   - Docker 상태 확인
   - 테이블 구조 확인
   - 대상 날짜 데이터 조회

3. **3. 수집 프로그램 준비** (필수)
   - 테이블 구조 검증
   - Python 환경 확인

4. **4. 수집 프로세스** (실행)
   - Step 1: 주가 수집
   - Step 2: 지표 계산

5. **5. 검증 및 완료** (필수)
   - 최종 데이터 확인
   - 어제와 동기화 검증

6. **6. 문제 해결** (필요시)
   - 수집 실패 시 원인 분석
   - 데이터베이스 연결 실패 대응

---

### 2️⃣ 프로그램 사용법

#### TEMPLATE_collect_stock_data.py (권장)

**장점**:
- 명령줄 인자로 날짜 지정 가능
- 시장 상태 자동 확인 (주말/공휴일)
- 모듈화된 함수 구조
- 상세한 로깅

**사용법**:

```bash
# 기본 사용 (오늘 날짜)
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py

# 특정 날짜 지정
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py --date 2025-10-22

# 옵션 조합
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py \
  --date 2025-10-22 \
  --skip-indicators      # 주가만 수집

docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py \
  --date 2025-10-22 \
  --skip-prices          # 지표만 계산
```

**내부 변수 확인**:

```python
# 스크립트 내부에서 자동으로 설정됨:
if args.date:
    TARGET_DATE = datetime.strptime(args.date, '%Y-%m-%d').date()
else:
    TARGET_DATE = date.today()  # 자동으로 오늘 날짜 사용

DATE_STR = TARGET_DATE.strftime('%Y%m%d')  # "20251022"
```

---

#### 기존 프로그램 수정 방법

기존의 `collect_stock_data_20251022.py` 같은 파일을 다른 날짜로 사용하려면:

```python
# ❌ 잘못된 방법: 파일명 복사만 함
# collect_stock_data_20251023.py

# ✅ 올바른 방법: 다음 2줄을 수정
from datetime import date

TARGET_DATE = date(2025, 10, 23)  # ← 여기를 변경! (년, 월, 일)
DATE_STR = TARGET_DATE.strftime('%Y%m%d')  # 자동으로 "20251023"
```

---

### 3️⃣ 데이터베이스 검증

#### 빠른 확인 (1줄)

```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
    (SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-22'::date) as prices,
    (SELECT COUNT(DISTINCT ticker) FROM stock_prices WHERE date = '2025-10-22'::date) as price_tickers,
    (SELECT COUNT(*) FROM technical_indicators WHERE date = '2025-10-22'::date) as indicators,
    (SELECT COUNT(DISTINCT ticker) FROM technical_indicators WHERE date = '2025-10-22'::date) as indicator_tickers;
"
```

#### 상세 검증 (SQL 파일)

```bash
docker cp QUICK_VERIFICATION_QUERIES.sql stock-db:/tmp/
docker exec stock-db psql -U admin -d stocktrading -f /tmp/QUICK_VERIFICATION_QUERIES.sql
```

**포함된 검증 종류**:
- 기본 현황 확인 (3개 쿼리)
- 어제와 비교 (4개 쿼리)
- 데이터 품질 (5개 쿼리)
- 테이블 구조 (3개 쿼리)
- 수집 로그 (2개 쿼리)
- 문제 진단 (4개 쿼리)
- 통계 분석 (3개 쿼리)
- 완전 수집 확인 (1개 쿼리)

---

## 🔧 문제 해결 가이드

### 현상: 주가 수집 실패

```
❌ "No stock prices fetched"
```

**확인 사항** (MANUAL_DATA_COLLECTION_GUIDE.md의 6.1 참고):

```bash
# 1. 날짜 다시 확인
powershell -Command "Get-Date -Format 'yyyy-MM-dd dddd'"

# 2. 요일 확인 (토/일이면 안됨)
# 3. 공휴일 확인
# 4. 시간 확인 (15:30 이후여야 함)
```

---

### 현상: "Column undefined error"

```
❌ psycopg2.errors.UndefinedColumn: column "sma_20" does not exist
```

**원인**: 컬럼명 불일치

**수정 방법**:

```python
# ❌ 잘못된 컬럼명
'sma_20', 'sma_50', 'sma_200'
'bb_upper', 'bb_lower'

# ✅ 올바른 컬럼명
'ma_20', 'ma_50', 'ma_200'
'bollinger_upper', 'bollinger_lower'
```

**해결**: TEMPLATE_collect_stock_data.py 사용 (이미 수정됨)

---

### 현상: 누락된 데이터 감지

```bash
# 어제: 2761개
# 오늘: 1802개 (959개 누락)
```

**복구 방법**:

```bash
# 1단계: 누락된 티커만 수집
docker exec stock-backend python /app/collect_missing_tickers_20251022.py

# 2단계: 누락된 지표 계산
docker exec stock-backend python /app/calculate_missing_indicators_20251022.py

# 3단계: 검증
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(DISTINCT ticker) FROM stock_prices WHERE date = '2025-10-22'::date;"
# 결과: 2761 (복구됨!)
```

---

## 📋 체크리스트

### 수집 전

- [ ] 현재 날짜/시간 확인 (시스템 명령어)
- [ ] 평일인가? (월~금)
- [ ] 15:30 이후인가?
- [ ] 공휴일이 아닌가?
- [ ] Docker 컨테이너 모두 Up 상태?
- [ ] 데이터베이스 접속 가능?

### 수집 중

- [ ] 주가 수집 시작 메시지 확인
- [ ] 진행 상황 모니터링 (200개마다 로그)
- [ ] 오류율 5% 이하
- [ ] 완료 메시지 확인

### 수집 후

- [ ] 주가 2,700개 이상?
- [ ] 지표 2,700개 이상?
- [ ] 어제와 동일한 티커 수?
- [ ] NULL 값 최소?
- [ ] OHLC 데이터 정상 범위?

---

## 📞 핵심 명령어 치트시트

```bash
# 날짜 확인
powershell -Command "Get-Date -Format 'yyyy-MM-dd dddd HH:mm:ss'"

# Docker 상태
cd stock-trading-system && docker-compose ps

# 데이터 수집 (TEMPLATE 사용)
docker cp TEMPLATE_collect_stock_data.py stock-backend:/app/
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py --date 2025-10-22

# 검증 (빠른 확인)
docker exec stock-db psql -U admin -d stocktrading -c \
  "SELECT (SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-22'::date) as prices,
          (SELECT COUNT(*) FROM technical_indicators WHERE date = '2025-10-22'::date) as indicators;"

# 검증 (상세 확인)
docker cp QUICK_VERIFICATION_QUERIES.sql stock-db:/tmp/
docker exec stock-db psql -U admin -d stocktrading -f /tmp/QUICK_VERIFICATION_QUERIES.sql

# 누락 데이터 수집 (응급)
docker exec stock-backend python /app/collect_missing_tickers_20251022.py
docker exec stock-backend python /app/calculate_missing_indicators_20251022.py
```

---

## 🎯 다음 단계

### 처음 사용하는 경우

1. **MANUAL_DATA_COLLECTION_GUIDE.md** 읽기 (20분)
2. **TEMPLATE_collect_stock_data.py** 테스트 (5분)
3. **QUICK_VERIFICATION_QUERIES.sql** 실행 (2분)

### 반복 사용하는 경우

```bash
# 매일 실행할 수 있는 한 줄 명령어
docker exec stock-backend python /app/TEMPLATE_collect_stock_data.py --date $(date +%Y-%m-%d)
```

### 자동화하는 경우

Airflow DAG에 위 명령어를 통합하면 자동 수집 가능.

---

## 📊 수집 기록

| 날짜 | 주가 | 지표 | 상태 | 비고 |
|------|------|------|------|------|
| 2025-10-21 | 2,761 | 2,761 | ✅ | - |
| 2025-10-22 | 2,761 | 2,775 | ✅ | 초기 959개 → 누락 1,802개 추가 복구 |

---

## ⚠️ 매우 중요한 주의사항

1. **날짜는 반드시 시스템 명령어로 확인**
   - Claude의 추론 금지
   - `Get-Date` 또는 `date` 사용

2. **컬럼명 정확히 확인**
   - `sma_20` ❌ → `ma_20` ✅
   - `bb_upper` ❌ → `bollinger_upper` ✅

3. **변수 설정 재확인**
   ```python
   TARGET_DATE = date(2025, 10, 22)  # 정확한 년월일
   DATE_STR = "20251022"              # 8자리 형식
   ```

4. **실행 전 Docker 확인**
   - 모든 컨테이너 Up
   - 데이터베이스 접속 성공

---

## 📞 기술 지원

**문제 발생 시**:
1. MANUAL_DATA_COLLECTION_GUIDE.md의 "6. 문제 해결" 확인
2. QUICK_VERIFICATION_QUERIES.sql로 현황 진단
3. 로그 메시지 정확히 읽기

---

**버전**: v1.0
**마지막 검증**: 2025-10-22 20:31
**다음 업데이트**: 필요 시
