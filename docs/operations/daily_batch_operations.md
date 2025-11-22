# 📊 일일 배치 운영 매뉴얼

**작성일**: 2025-11-10
**카테고리**: Operations
**상태**: ✅ 완료
**담당자**: Claude Code

---

## 📋 개요

운영서버 101(192.168.219.101)에서 실행되는 일일 배치 작업의 운영 및 모니터링 매뉴얼입니다.

- **대상 서버**: 192.168.219.101 (운영서버 101)
- **실행 환경**: Docker + Airflow 2.7.2
- **데이터베이스**: PostgreSQL (192.168.219.103:5432)

---

## ⏰ 배치 스케줄

### 1. 주가수집 배치 (daily_collection_dag)

| 항목 | 설정값 |
|------|--------|
| **실행 시간** | 한국시간 **16:30** (UTC 07:30) |
| **실행 주기** | 평일만 (월-금) |
| **처리 내용** | KOSPI, KOSDAQ 주가 및 시장 지수 수집 |
| **대상 DB** | stocktrading (192.168.219.103:5432) |
| **예상 소요시간** | 약 5-10분 |

**스케줄 표현식**: `30 7 * * 1-5` (Cron 형식)

### 2. 기술적 지표 계산 (technical_indicator_dag)

| 항목 | 설정값 |
|------|--------|
| **실행 타이밍** | daily_collection_dag 완료 후 **즉시** |
| **실행 주기** | daily_collection_dag 실행 시에만 |
| **처리 내용** | 200일 역사 데이터 기반 기술적 지표 계산 |
| **계산 지표** | RSI, MACD, SMA(20/50/200), Bollinger Bands 등 |
| **예상 소요시간** | 약 3-5분 (1,000개 종목 기준) |

---

## 🔄 배치 실행 흐름

```
16:30 KST
    ↓
┌─────────────────────────────────────┐
│  daily_collection_dag 시작           │
├─────────────────────────────────────┤
│ 1. 수집 상태 확인                    │
│ 2. KOSPI 주가 수집 (병렬)            │
│ 3. KOSDAQ 주가 수집 (병렬)           │
│ 4. 시장 지수 수집 (병렬)             │
│ 5. DB 저장                          │
│ 6. 수집 로그 기록                    │
└─────────────────────────────────────┘
        ↓ (완료)
  trigger
        ↓
┌─────────────────────────────────────┐
│ technical_indicator_dag 자동 시작    │
├─────────────────────────────────────┤
│ 1. 수집 완료 확인                    │
│ 2. 200일 가격 데이터 로드 (병렬)     │
│ 3. 기술적 지표 계산 (병렬)           │
│ 4. DB 저장                          │
│ 5. 계산 로그 기록                    │
└─────────────────────────────────────┘
        ↓ (완료)
   배치 완료
```

---

## 📊 모니터링

### Airflow Webui 접속

```bash
# 브라우저 접속
http://192.168.219.101:8080

# 로그인
계정: admin
비밀번호: admin123
```

### DAG 상태 확인

**CLI 명령어**:
```bash
# 운영서버 101에서 실행
ssh yunsang@192.168.219.101

# DAG 목록 확인
docker exec stock-airflow-scheduler airflow dags list

# 최근 실행 기록 확인
docker exec stock-airflow-scheduler airflow dags list-runs --dag-id daily_collection_dag

# 다음 실행 예정 시간 확인
docker exec stock-airflow-scheduler airflow dags next-execution daily_collection_dag
```

### 로그 확인

```bash
# 스케줄러 로그 (실시간)
docker logs -f stock-airflow-scheduler

# 특정 DAG 로그 검색
docker logs stock-airflow-scheduler | grep "daily_collection_dag"

# 최근 N줄만 확인
docker logs --tail=100 stock-airflow-scheduler
```

### 수집 데이터 검증

```bash
# 운영 DB 접속
psql -h 192.168.219.103 -U admin -d stocktrading

# 오늘 수집 통계 확인
SELECT
  date,
  COUNT(*) as stock_count,
  status
FROM stock_prices
WHERE date = CURRENT_DATE
GROUP BY date, status;

# 지표 계산 통계 확인
SELECT
  date,
  COUNT(*) as indicator_count,
  status
FROM technical_indicators
WHERE date = CURRENT_DATE
GROUP BY date, status;
```

---

## ⚠️ 주의사항

### 1. 개발 PC Docker 상태
- ✅ **반드시 중지 상태 유지**
- 개발 PC에서 Docker 실행 시 운영서버와 충돌 가능
- 개발용 테스트는 `docker-compose down` 후 진행

### 2. 스케줄러 시간대
- UTC 기준으로 설정되어 있음
- 한국시간 16:30 = UTC 07:30
- 시간 변경 시 Airflow 스케줄러 재시작 필수

### 3. 데이터베이스 연결
- 운영 DB: 192.168.219.103:5432
- 연결 끊김 시 자동 재시도 (최대 3회)
- 지속적인 연결 실패 시 알림

### 4. 배치 실패 처리
- 배치 실패 시 자동 재시도 안 함
- Airflow Webui에서 수동 재실행 필요
- 실패 원인은 로그 확인

---

## 🛠️ 배치 재시작

### 정상 재시작 (권장)

```bash
ssh yunsang@192.168.219.101
cd /home/yunsang/stock-trading-system

# 스케줄러 재시작
docker restart stock-airflow-scheduler

# 재시작 확인
docker ps | grep airflow
```

### 전체 컨테이너 재시작

```bash
# 전체 중지 및 시작
docker compose down
docker compose up -d

# 상태 확인
docker ps
```

---

## 📈 성능 최적화

### 배치 성능 지표

| 항목 | 목표값 | 경고값 |
|------|--------|--------|
| daily_collection_dag 소요시간 | < 10분 | > 15분 |
| technical_indicator_dag 소요시간 | < 5분 | > 10분 |
| 수집 종목 수 | 2,700+ | < 2,500 |
| 지표 계산 성공률 | 100% | < 95% |

### 최적화 방법

1. **병렬 처리 확인**
   - KOSPI, KOSDAQ, 지수 수집은 병렬 처리
   - 종목별 지표 계산도 병렬 처리

2. **DB 쿼리 최적화**
   - 인덱스 확인: `SELECT * FROM pg_indexes WHERE tablename = 'stock_prices';`
   - 쿼리 플랜 분석: `EXPLAIN ANALYZE {쿼리}`

3. **리소스 모니터링**
   - CPU 사용률 확인: `docker stats`
   - 메모리 사용률 확인: `docker stats`

---

## 🔄 정기 점검 사항

### 일일 (매일 17:30 KST 이후)
- [ ] Airflow Webui 접속 확인
- [ ] 배치 실행 완료 여부 확인
- [ ] 에러 로그 확인
- [ ] 수집 데이터 샘플 검증

### 주간 (매주 금요일)
- [ ] 배치 성능 지표 리뷰
- [ ] DB 용량 확인
- [ ] 로그 파일 크기 확인
- [ ] 스케줄러 메모리 누수 확인

### 월간
- [ ] 배치 설정 리뷰
- [ ] 데이터 품질 리포트
- [ ] 성능 개선안 검토
- [ ] 백업 상태 확인

---

## 📞 문제 해결

### Q: 배치가 실행되지 않음
**확인 사항**:
1. 스케줄러 상태 확인: `docker ps | grep scheduler`
2. Airflow DB 상태 확인: `docker logs stock-airflow-scheduler`
3. 스케줄 설정 확인: `airflow dags list`

### Q: 배치 실행 시간이 너무 오래 걸림
**확인 사항**:
1. 네트워크 연결 상태 (pykrx API 응답 시간)
2. DB 성능 (쿼리 실행 시간)
3. 리소스 사용률 (CPU, 메모리)

### Q: 데이터가 수집되지 않음
**확인 사항**:
1. 데이터베이스 연결 확인
2. 수집 권한 확인
3. API 응답 상태 확인 (pykrx)

---

## 📚 관련 문서

- [배포 가이드](../deployment/101_scheduler_deployment_20251110.md)
- [Airflow DAG 가이드](../guides/airflow_dag_guide.md)
- [문서 정리 규칙](../DOCUMENTATION_RULES.md)
- [운영 가이드](../../start_hsl.md)

---

**마지막 업데이트**: 2025-11-10
**버전**: v1.0
**상태**: ✅ 운영 중
