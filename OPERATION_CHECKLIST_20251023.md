# 운영 체크리스트 - 2025-10-23 검증 완료

**작성일**: 2025-10-23 21:00 KST
**상태**: ✅ 모든 항목 완료

---

## ✅ 완료된 항목

### 1. 기술 지표 계산 최적화
- ✅ 컬럼명 매핑 수정 (sma_20 → ma_20 등)
- ✅ 200일 역사 데이터 로드 구현
- ✅ 2,775개 지표 저장 성공 검증
- ✅ common_functions.py 업데이트
  - Backend 버전
  - Airflow 버전

### 2. DAG 업데이트
- ✅ technical_indicator_dag.py 개선
  - 오류 처리 강화
  - 컬럼명 매핑 문서화
  - 재시도 로직 추가
- ✅ DAG를 Airflow 컨테이너로 배포

### 3. 문서 작성
- ✅ start_hsl.md (운영 가이드 - 간결 버전)
- ✅ MANUAL_DATA_COLLECTION_20251023.md (당일 검증 수동 수집)
- ✅ MANUAL_INDICATOR_CALCULATION_20251023.md (당일 검증 수동 계산)
- ✅ 이 문서 (운영 체크리스트)

---

## 📋 내일 기동 시나리오

### 시나리오 1: 정상 운영 (Best Case)
```
18:30 KST
└─ daily_collection_dag 실행
   └─ ✅ 주가 2,760개 수집
   └─ ✅ 지수 2개 수집
   └─ ✅ collection_log 저장
        
19:50 KST
└─ technical_indicator_dag 실행
   └─ ✅ 200일 데이터 로드
   └─ ✅ 2,775개 지표 계산
   └─ ✅ indicator_log 저장
```
**결과**: 모든 데이터 자동 저장 완료

### 시나리오 2: 장 수집 실패 (장 마감 불가 등)
```
18:30 KST
└─ daily_collection_dag 실행
   └─ ❌ 첫 시도 실패
   └─ 🔄 재시도 1회
   └─ 🔄 재시도 2회
   └─ 🔄 재시도 3회 (모두 실패)
   
👤 수동 개입 필요!
└─ MANUAL_DATA_COLLECTION_20251023.md 참조
└─ 아래 명령어 실행:
```

**수동 실행 명령어**:
```bash
# start_hsl.md의 "빠른 명령어" 섹션 복사 후 실행
# 또는 MANUAL_DATA_COLLECTION_20251023.md의 전체 스크립트 사용
```

### 시나리오 3: 지표 계산 실패
```
19:50 KST
└─ technical_indicator_dag 실행
   └─ ❌ 첫 시도 실패
   └─ 🔄 재시도 1회
   └─ 🔄 재시도 2회
   └─ 🔄 재시도 3회 (모두 실패)

👤 수동 개입 필요!
└─ MANUAL_INDICATOR_CALCULATION_20251023.md 참조
└─ 아래 명령어 실행:
```

**수동 실행 명령어**:
```bash
# MANUAL_INDICATOR_CALCULATION_20251023.md의 전체 스크립트 사용
```

---

## 🚀 빠른 대응 가이드

### IF 장 수집 실패 THEN
```bash
# 1. 상태 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT collection_date, overall_status, price_retry_count, indices_retry_count
FROM collection_log WHERE collection_date = CURRENT_DATE;
"

# 2. 수동 수집 실행 (start_hsl.md의 "빠른 명령어" 섹션)
# 또는 아래 파일의 전체 스크립트 사용:
# → MANUAL_DATA_COLLECTION_20251023.md

# 3. 완료 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(*) FROM stock_prices WHERE date = CURRENT_DATE;
"
```

### IF 지표 계산 실패 THEN
```bash
# 1. 상태 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT indicator_date, status, retry_count
FROM indicator_log WHERE indicator_date = CURRENT_DATE;
"

# 2. 수동 계산 실행
# → MANUAL_INDICATOR_CALCULATION_20251023.md의 전체 스크립트 사용

# 3. 완료 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(*) FROM technical_indicators WHERE date = CURRENT_DATE;
"
```

---

## 📁 문서 구조

```
/f/hhstock/
├── start_hsl.md (👈 시작 점 - 먼저 읽기)
│
├── MANUAL_DATA_COLLECTION_20251023.md
│   └─ 장 수집 실패 시 사용
│   └─ 완전한 스크립트 포함 (복사 & 붙여넣기)
│
├── MANUAL_INDICATOR_CALCULATION_20251023.md
│   └─ 지표 계산 실패 시 사용
│   └─ 완전한 스크립트 포함 (복사 & 붙여넣기)
│
└── docs/
    └─ AIRFLOW_COMPLETE_DESIGN.md (아키텍처 참고용)
```

### 문서 읽기 순서
1. **첫 기동**: start_hsl.md
2. **장 수집 실패**: MANUAL_DATA_COLLECTION_20251023.md
3. **지표 계산 실패**: MANUAL_INDICATOR_CALCULATION_20251023.md
4. **심화 학습**: docs/AIRFLOW_COMPLETE_DESIGN.md

---

## 🔑 핵심 명령어 모음

### 상태 확인
```bash
# 전체 상태
docker ps

# 수집 상태
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT collection_date, overall_status FROM collection_log 
WHERE collection_date = CURRENT_DATE ORDER BY updated_at DESC LIMIT 1;"

# 지표 상태
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT indicator_date, status, indicators_count FROM indicator_log
WHERE indicator_date = CURRENT_DATE ORDER BY updated_at DESC LIMIT 1;"

# 데이터 개수
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT
  (SELECT COUNT(*) FROM stock_prices WHERE date = CURRENT_DATE) as prices,
  (SELECT COUNT(*) FROM technical_indicators WHERE date = CURRENT_DATE) as indicators,
  (SELECT COUNT(*) FROM market_indices WHERE date = CURRENT_DATE) as indices;"
```

### 로그 확인
```bash
# Airflow 로그
docker logs stock-airflow-scheduler | tail -50

# 특정 DAG 로그
docker exec stock-airflow-scheduler \
  airflow dags list-runs --dag-id daily_collection_dag

docker exec stock-airflow-scheduler \
  airflow dags list-runs --dag-id technical_indicator_dag
```

### 수동 실행 (당일 스크립트)
```bash
# 데이터 수집
→ MANUAL_DATA_COLLECTION_20251023.md 복사 & 실행

# 지표 계산
→ MANUAL_INDICATOR_CALCULATION_20251023.md 복사 & 실행
```

---

## 🟢 상태 요약

| 항목 | 상태 | 비고 |
|------|------|------|
| 자동 수집 DAG | ✅ 정상 | 매일 18:30 실행 |
| 자동 지표 DAG | ✅ 정상 | 매일 19:50 실행 (2025-10-23 수정) |
| 수동 수집 스크립트 | ✅ 준비됨 | MANUAL_DATA_COLLECTION_20251023.md |
| 수동 지표 스크립트 | ✅ 준비됨 | MANUAL_INDICATOR_CALCULATION_20251023.md (검증 완료) |
| 문서 | ✅ 완료 | start_hsl.md에서 시작 |
| **전체 상태** | **🟢 운영 준비 완료** | **내일 즉시 기동 가능** |

---

## 📞 트러블슈팅 빠른 링크

**문제**: DAG 실행 확인 불가
→ [start_hsl.md - 트러블슈팅](#트러블슈팅)

**문제**: 장 수집 데이터가 없음
→ [MANUAL_DATA_COLLECTION_20251023.md](#오류-해결)

**문제**: "column ma_20 does not exist"
→ [MANUAL_INDICATOR_CALCULATION_20251023.md - 오류 해결](#오류-해결)

---

**최종 검증일**: 2025-10-23 21:00 KST
**다음 자동 실행**: 2025-10-24 18:30 KST (예정)

---

## 체크리스트 (내일 아침 확인용)

- [ ] Docker 컨테이너 모두 running 상태 확인
- [ ] Airflow Web UI (http://localhost:8080) 접속 가능 확인
- [ ] 18:30 데이터 수집 완료 확인
- [ ] 19:50 지표 계산 완료 확인
- [ ] 모든 데이터 DB에 저장되었는지 확인

수집 실패 시: MANUAL_DATA_COLLECTION_20251023.md 실행
계산 실패 시: MANUAL_INDICATOR_CALCULATION_20251023.md 실행
