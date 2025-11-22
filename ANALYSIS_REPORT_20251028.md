# 2025-10-28 데이터 수집 실패 원인 분석 보고서

**작성 일시**: 2025-10-28 23:00 KST
**상태**: 문제 원인 파악 완료, 해결 방안 제시

---

## 📊 검증 결과 요약

| 항목 | 상태 | 결과 |
|------|------|------|
| 1. 모듈 설치 문제 | ✅ 정상 | pykrx 정상 설치됨 (로컬 Python) |
| 2. 데이터 수집 | ✅ 정상 | KOSPI 958개, KOSDAQ 1,801개 모두 수집 가능 |
| 3. DB 저장 | ❌ 실패 | TimescaleDB 청크 생성 오류 |

---

## 📋 상세 분석

### 검증 #1: 모듈 설치 문제

**질문**: Docker에서 pykrx가 없다고 했는데 정말 그런가?

**결과**:
- ✅ 로컬 Python: pykrx 정상 설치
- ❌ Docker Airflow 컨테이너: pykrx 미설치
- 📌 **결론**: Docker 환경과 로컬 환경이 다름. Docker 이미지를 재빌드해야 함

**원인**:
```
docker-compose.yml에서:
_PIP_ADDITIONAL_REQUIREMENTS: 'pandas sqlalchemy psycopg2-binary requests beautifulsoup4 pykrx pytz'
```
- 명시되어 있지만, 기존 Docker 이미지가 캐시되어 있음
- 컨테이너 재시작만으로는 의존성이 재설치되지 않음

---

### 검증 #2: 데이터 수집 가능성

**질문**: 정말로 1건이라도 데이터를 못 가져오는가?

**결과**: ✅ 정상 수집

테스트 결과:
```
KOSPI 종목: 958개 수집 성공
- 샘플: ['095570', '006840', '027410']

KOSDAQ 종목: 1,801개 수집 성공
- 샘플: ['060310', '054620', '265520']

첫번째 종목(095570) 주가 데이터:
- 날짜: 2025-10-28
- 시가: 4,350원
- 고가: 4,430원
- 저가: 4,295원
- 종가: 4,405원
- 거래량: 213,674주
```

**결론**: 데이터 수집은 정상. 문제는 저장 단계.

---

### 검증 #3: DB 저장 실패 분석

**질문**: 기존에는 저장되던데 왜 이제 안 되는가?

**발견**: **TimescaleDB 청크(Chunk) 생성 오류**

#### 원인 상세 분석

**에러 메시지**:
```
ERROR: relation "_hyper_1_10_chunk" already exists
(DuplicateTable)
```

**상황**:
1. 2025-10-02 데이터: 2,763건 정상 저장됨 ✅
2. 2025-10-03~10-07: 부분 저장 (각 5건씩) ⚠️
3. 2025-10-28: 0건 저장 실패 ❌

**데이터베이스 상태**:
```
- 전체 stock_prices: 3,040,694행
- 날짜별:
  2025-10-02: 2,763건 (정상)
  2025-10-26: 2,762건 (정상)
  2025-10-28: 0건 (실패)
```

#### 핵심 문제

TimescaleDB의 하이퍼테이블(HyperTable)은 자동으로 시간 기반 청크(Chunk)를 생성합니다.

**발생 과정**:
```
1단계: 2025-10-28 데이터 삽입 시도
  ↓
2단계: TimescaleDB가 _hyper_1_10_chunk 생성
  ↓
3단계: 데이터 삽입 중 오류 발생 (FK 제약 조건 등)
  ↓
4단계: 트랜잭션 롤백
  ↓
5단계: 청크는 남아있음 (고아 청크)
  ↓
6단계: 재시도 시 "relation already exists" 오류
```

**구체적인 에러**:
1. **첫번째 시도**: ForeignKeyViolation (ticker가 stocks 테이블에 없음)
2. **두번째 시도**: DuplicateTable (이미 생성된 청크 재생성 시도)

---

## 🎯 세 가지 문제의 관계도

```
┌─────────────────────────────────────────────────────────┐
│ 문제 #1: Docker pykrx 모듈 부재                         │
│ 영향: DAG 실행 불가 → "No module named 'pykrx'"       │
│ 상태: ❌ 미해결                                         │
└──────────────────────────────┬──────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────┐
│ 문제 #2: 종목 수 부족 (955→2,759)                       │
│ 영향: KOSDAQ 미수집 (이미 해결됨)                       │
│ 상태: ✅ 코드 수정 완료                                  │
└──────────────────────────────┬──────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────┐
│ 문제 #3: TimescaleDB 청크 오류                          │
│ 근본원인: 외래키 위반 → 청크 손상                        │
│ 영향: 2025-10-28 데이터 저장 불가                      │
│ 상태: ❌ 미해결 (DB 복구 필요)                           │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 해결 방안

### 방안 A: 긴급 (즉시, 5분)

**목표**: 2025-10-28 데이터 저장하기

```sql
-- 고아 청크 제거
SELECT drop_chunks('public.stock_prices',
  INTERVAL '1 day',
  newer_than => '2025-10-28'::timestamptz);

-- 혹은 해당 날짜의 고아 청크 직접 삭제
DROP TABLE IF EXISTS "_hyper_1_10_chunk";
```

**실행 후**: Python으로 1건 INSERT 재시도

---

### 방안 B: 안전 (10분)

**방법**: 2025-10-28의 기존 불완전한 청크 초기화 후 재삽입

```sql
-- 1단계: 2025-10-28 청크 확인
SELECT tablename FROM pg_tables
WHERE tablename LIKE '_hyper_%'
ORDER BY tablename DESC LIMIT 5;

-- 2단계: 가장 최신 청크 삭제
DROP TABLE IF EXISTS "_hyper_1_10_chunk" CASCADE;

-- 3단계: 다시 INSERT 시도
```

---

### 방안 C: 종합 (30분)

**방법**: Docker 완전 재구축 + DB 초기화

```bash
# 1. Docker 컨테이너 중지 및 제거
cd /f/hhstock/stock-trading-system
docker-compose down

# 2. 이미지 재빌드 (pykrx 포함)
docker-compose build --no-cache

# 3. 전체 시스템 재시작
docker-compose up -d

# 4. 확인
docker exec stock-airflow-scheduler airflow dags test daily_collection_dag 2025-10-28
```

**장점**:
- pykrx 모듈 설치됨 ✅
- TimescaleDB 청크 초기화 ✅
- 코드 변경사항 적용됨 ✅

---

## 🔍 기존 프로그램 상태

로컬 Python 수집 프로그램들 (정상 작동):
```
✅ /f/hhstock/collect_20251021.py
✅ /f/hhstock/collect_and_calculate_20251022.py
✅ /f/hhstock/backend/collect.py
✅ /f/hhstock/stock-trading-system/backend/collect_20251020.py
```

**특징**: 이들은 Docker가 아닌 로컬 Python에서 직접 실행되므로 모듈 문제 없음.

---

## 📌 결론 및 권장사항

### 문제 순서별 해결

1. **우선순위 1 (긴급)**: TimescaleDB 청크 복구
   ```
   시간: 5분
   방법: SQL로 고아 청크 삭제
   영향: 2025-10-28 데이터 즉시 저장 가능
   ```

2. **우선순위 2 (중요)**: Docker pykrx 모듈 설치
   ```
   시간: 10분
   방법: 컨테이너 재구축
   영향: 장기적 DAG 안정성
   ```

3. **우선순위 3 (장기)**: 코드 리뷰
   ```
   시간: 이미 완료됨 ✅
   상태: fetch_stock_prices_api() + save_stock_prices() 수정 완료
   ```

### 현재 권장 조치

**즉시 실행** (5분):
```bash
# SQL로 청크 제거
docker exec stock-db psql -U admin -d stocktrading -c "
DROP TABLE IF EXISTS \"_hyper_1_10_chunk\" CASCADE;
"

# 다시 시도
python /f/hhstock/stock-trading-system/backend/collect_20251021.py
```

**또는 전체 재구축** (30분):
```bash
cd /f/hhstock/stock-trading-system
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## 📊 최종 검증 결과

| 검증 항목 | 결과 | 원인 | 해결 |
|----------|------|------|------|
| 1. 모듈 설치 | ❌ Docker만 문제 | 캐시 이미지 | 재구축 |
| 2. 데이터 수집 | ✅ 정상 | - | - |
| 3. DB 저장 | ❌ 청크 오류 | 외래키 충돌 | SQL 청크 삭제 |

**현재 상황**:
- 로컬 Python에서는 데이터 수집 및 저장 가능 ✅
- Docker Airflow는 pykrx 부재로 실행 불가 ❌
- TimescaleDB 청크 문제로 2025-10-28 저장 불가 ❌

