# 작업 요약 - 2025-10-20

**작업 일시**: 2025-10-20
**주요 완료**: 2025-10-20 전체 주가 데이터 수집 및 지표 계산

---

## 📋 작업 개요

2025-10-20 주가 데이터 수집 시 발생한 여러 버그를 파악하고 수정하였으며, 17일차 데이터와의 비교를 통해 누락된 데이터까지 모두 수집 완료했습니다.

---

## 🔍 발견된 문제점

### 1. **common_functions.py의 SQL 버그**

**문제**: `updated_at` 컬럼 존재하지 않음
```python
# 잘못된 코드
ON CONFLICT (ticker, date) DO UPDATE SET
    open_price = EXCLUDED.open_price,
    ...
    updated_at = NOW()  # ❌ stock_prices 테이블에 없는 컬럼
```

**해결**: `updated_at` 관련 코드 제거

---

### 2. **pykrx 지수 조회 코드 오류**

**문제**: 지수명 문자열로 조회 실패
```python
# 잘못된 코드
kospi = pykrx_stock.get_index_ohlcv(date_str, date_str, "KOSPI")  # ❌ 실패
kosdaq = pykrx_stock.get_index_ohlcv(date_str, date_str, "KOSDAQ")  # ❌ 실패
```

**해결**: 지수 코드 사용
```python
# 올바른 코드
kospi = pykrx_stock.get_index_ohlcv(date_str, date_str, "1001")  # ✅ KOSPI
kosdaq = pykrx_stock.get_index_ohlcv(date_str, date_str, "1002")  # ✅ KOSDAQ
```

---

### 3. **market_indices 테이블 스키마 불일치**

**문제**: 저장 함수가 잘못된 컬럼명 사용
```sql
-- 존재하지 않는 컬럼들
INSERT INTO market_indices (
    date, index_name,
    open_value, high_value, low_value, close_value, volume  -- ❌
)
```

**실제 테이블 구조**:
```sql
CREATE TABLE market_indices (
    id INTEGER PRIMARY KEY,
    index_name VARCHAR,
    date DATE,
    index_value NUMERIC,        -- 있음
    stock_count INTEGER,
    total_volume BIGINT,        -- 있음
    total_market_cap BIGINT,
    created_at TIMESTAMP
);
```

**해결**: 스키마에 맞게 정규화
```python
normalized_df = pd.DataFrame({
    'date': target_date,
    'index_name': indices_df['index_name'],
    'index_value': indices_df['종가'].astype(float),  # close_price 매핑
    'total_volume': indices_df['거래량'].astype(int),
    'created_at': datetime.now()
})
```

---

### 4. **stocks 테이블 FK 제약 위반**

**문제**: pykrx의 신규 티커(예: 317450)가 stocks 테이블에 없음
```
ERROR: Key (ticker)=(317450) is not present in table "stocks"
```

**해결**: pykrx 티커로 stocks 테이블 동기화
- 2025-10-20 pykrx 티커: 959개
- 신규 추가: 1개 (총 2779개)

---

### 5. **누락된 주가 데이터**

**문제**: 첫 수집에서 959개만 수집됨 (활성 티커만)
- 17일자: 2,760개 주가
- 20일차 초기: 959개 (1,801개 누락)

**해결**: 17일차와 비교하여 누락된 티커 모두 수집
- 누락된 티커: 1,802개
- 추가 수집: 1,802개 모두 성공
- 최종: 2,761개 (17일차보다 1개 추가)

---

## ✅ 최종 결과

| 데이터 | 17일차 | 20일차 | 상태 |
|--------|--------|--------|------|
| **주가 (stock_prices)** | 2,760 | 2,761 | ✅ |
| **기술적 지표 (technical_indicators)** | 2,760 | 2,761 | ✅ |
| **시장 지수 (market_indices)** | - | 2 (KOSPI, KOSDAQ) | ✅ |

---

## 🛠️ 수정된 파일

### 1. `stock-trading-system/airflow/dags/common_functions.py`

**변경사항**:
- Line 211: `updated_at = NOW()` 제거 (stock_prices)
- Line 132: `"KOSPI"` → `"1001"` 변경
- Line 142: `"KOSDAQ"` → `"1002"` 변경
- Line 263-282: market_indices INSERT 로직 재작성

**커밋**: `050338d` - "fix: 2025-10-20 데이터 수집 버그 수정"

### 2. `stock-trading-system/backend/common_functions.py`

**변경사항**:
- 위의 common_functions.py를 backend 디렉토리에 복사
- 스크립트에서 import 가능하도록 배치

**커밋**: `050338d` - 동일

### 3. `collect_missing_20251020.py` (신규)

**기능**:
- 17일차와 20일차 티커 비교
- 누락된 1,802개 티커 식별
- pykrx에서 모든 누락된 주가 조회
- 데이터베이스에 일괄 저장
- TimescaleDB 제약 회피 (TRIGGER 비활성화 불가능하므로 제거)

**커밋**: `841e982` - "feat: 2025-10-20 누락된 주가 데이터 수집 완료"

---

## 🔧 기술적 상세

### TimescaleDB와 pykrx 통합

**TimescaleDB 특성**:
- Hypertable 기반 시계열 데이터 저장소
- TRIGGER 비활성화 미지원 (일반 PostgreSQL과 다름)
- 청크(Chunk) 단위로 데이터 파티셔닝
- 2025-10-16 ~ 2025-10-23 범위의 청크 존재

**pykrx API 호출**:
```python
# 개별 주식 데이터
get_market_ohlcv('20251020', '20251020', ticker)

# 지수 데이터
get_index_ohlcv('20251020', '20251020', '1001')  # KOSPI
get_index_ohlcv('20251020', '20251020', '1002')  # KOSDAQ
```

---

## 📊 수집 성능

| 항목 | 수량 | 소요 시간 |
|------|------|---------|
| pykrx 조회 | 2,761개 | ~3분 |
| 데이터 정규화 | 2,761개 | ~30초 |
| 데이터베이스 저장 | 2,761개 | ~2분 |
| **총 소요 시간** | - | **~5-6분** |

---

## 🚀 향후 개선 방안

### 1. **Airflow DAG 자동화**
- `daily_collection_dag.py` 완성
- `technical_indicator_dag.py` 완성
- 자동 스케줄링으로 일일 수집 자동화

### 2. **에러 핸들링 강화**
- pykrx API 호출 실패 시 재시도 로직
- 부분 실패 시 성공한 데이터만 저장하도록 개선
- 에러 로깅 및 알림

### 3. **성능 최적화**
- 배치 INSERT 활용 (현재는 개별 INSERT)
- 병렬 처리 (멀티프로세싱)
- 네트워크 타임아웃 최적화

### 4. **데이터 검증**
- 수집 전후 데이터 무결성 검사
- 기술적 지표 계산 자동화
- 예상치 못한 값에 대한 경고

---

## 📚 참고 문서

- `/docs/AIRFLOW_COMPLETE_DESIGN.md` - 전체 Airflow 설계
- `/docs/AIRFLOW_NEW_DESIGN_DETAILED.md` - 상세 DAG 구조
- `/docs/DEPLOYMENT_CHECKLIST.md` - 배포 체크리스트
- `/IMPLEMENTATION_SUMMARY.md` - 구현 완료 요약

---

## 💾 커밋 로그

```
841e982 feat: 2025-10-20 누락된 주가 데이터 수집 완료
050338d fix: 2025-10-20 데이터 수집 버그 수정
```

---

**작성자**: Claude
**작성일**: 2025-10-20
**상태**: ✅ 완료
