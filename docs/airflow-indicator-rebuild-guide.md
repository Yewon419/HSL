# Airflow 지표 재계산 가이드

## 개요

지표 계산이 hang 걸리는 문제를 해결하기 위해 Airflow DAG를 사용한 chunked 방식의 재계산 시스템을 구축했습니다.

## 주요 기능

### 1. **자동 Chunk 분할**
- 전체 종목을 50개씩 chunk로 분할하여 처리
- 각 chunk는 독립적인 task로 실행되어 hang 방지
- 실패한 chunk만 재실행 가능

### 2. **실시간 진행 상황 모니터링**
- Airflow UI에서 각 chunk의 진행 상황 확인
- 로그를 통한 상세 진행률 추적
- XCom을 통한 중간 결과 저장

### 3. **데이터 삭제 및 재적재**
- 특정 날짜(2025-09-29)부터 기존 지표 삭제
- 삭제 전 상태 확인 및 로깅
- 안전한 트랜잭션 처리

## DAG 구조

```
rebuild_indicators_from_date
├── check_status          # 1. 현재 데이터 상태 확인
├── delete_indicators     # 2. 기존 지표 데이터 삭제
├── get_ticker_list       # 3. 대상 종목 리스트 생성
├── calculate_chunk_0     # 4-1. Chunk 0 처리 (종목 1~50)
├── calculate_chunk_1     # 4-2. Chunk 1 처리 (종목 51~100)
├── calculate_chunk_2     # 4-3. Chunk 2 처리 (종목 101~150)
├── ...                   # ...
├── calculate_chunk_N     # 4-N. Chunk N 처리
└── final_report          # 5. 최종 결과 리포트
```

## 사용 방법

### 1. Airflow 접속

```bash
# 로컬 환경
http://localhost:8080

# 운영 서버
http://<server-ip>:8080

# 로그인
Username: admin
Password: admin123
```

### 2. DAG 실행

#### 방법 A: UI에서 실행 (권장)

1. Airflow UI 접속
2. DAGs 메뉴에서 `rebuild_indicators_from_date` 검색
3. DAG 활성화 (토글 스위치 ON)
4. 우측 "Play" 버튼 클릭 → "Trigger DAG w/ config" 선택
5. Configuration 입력:
   ```json
   {
     "start_date": "2025-09-29"
   }
   ```
6. "Trigger" 버튼 클릭

#### 방법 B: CLI에서 실행

```bash
# Docker 컨테이너 접속
docker exec -it stock-trading-system-airflow-webserver-1 bash

# DAG 트리거
airflow dags trigger rebuild_indicators_from_date \
  --conf '{"start_date": "2025-09-29"}'
```

### 3. 진행 상황 모니터링

#### 3.1 Airflow UI에서 모니터링

1. **Graph View**
   - DAG 이름 클릭 → "Graph" 탭
   - 각 task의 상태를 색상으로 표시
     - 🟢 초록색: 성공
     - 🔵 파란색: 실행 중
     - 🔴 빨간색: 실패
     - ⚪ 회색: 대기 중

2. **Task 로그 확인**
   - Graph View에서 task 클릭
   - "Log" 버튼 클릭
   - 실시간 로그 확인

3. **XCom 확인** (중간 결과)
   - Task 클릭 → "XCom" 탭
   - 저장된 중간 결과 확인
     - `start_date`: 시작 날짜
     - `total_tickers`: 총 종목 수
     - `deleted_count`: 삭제된 레코드 수
     - `chunk_N_success`: Chunk N의 성공 종목 수
     - `chunk_N_saved`: Chunk N의 저장된 지표 수

#### 3.2 로그를 통한 상세 모니터링

각 task의 로그에서 다음 정보를 확인할 수 있습니다:

**check_status 로그 예시:**
```
================================================================================
지표 재계산 작업 시작
삭제 시작 날짜: 2025-09-29
================================================================================
삭제 대상 데이터:
  - 종목 수: 2,345
  - 총 레코드: 123,456
  - 기간: 2025-09-29 ~ 2025-10-11
```

**calculate_chunk_0 로그 예시:**
```
================================================================================
Chunk 0 처리 시작
종목: 1~50 / 2345
처리 대상: 50개 종목
================================================================================
[1/50] 005930 (삼성전자) 처리 중...
  ✅ 005930 완료 (저장: 13개)
[2/50] 000660 (SK하이닉스) 처리 중...
  ✅ 000660 완료 (저장: 26개)
...
================================================================================
Chunk 0 처리 완료
성공: 48/50
실패: 2/50
저장된 지표: 650개
================================================================================
```

**final_report 로그 예시:**
```
================================================================================
지표 재계산 작업 완료
================================================================================
시작 날짜: 2025-09-29
대상 종목: 2,345개
삭제된 레코드: 123,456개
새로 저장된 지표: 150,000개
================================================================================
```

#### 3.3 데이터베이스에서 직접 확인

```sql
-- 진행률 확인
SELECT
    COUNT(DISTINCT ticker) as completed_tickers,
    COUNT(*) as total_indicators,
    MIN(date) as min_date,
    MAX(date) as max_date
FROM technical_indicators
WHERE date >= '2025-09-29'
  AND created_at >= NOW() - INTERVAL '1 hour';  -- 최근 1시간 내 생성

-- 날짜별 진행 상황
SELECT
    date,
    COUNT(DISTINCT ticker) as ticker_count,
    COUNT(*) as indicator_count
FROM technical_indicators
WHERE date >= '2025-09-29'
GROUP BY date
ORDER BY date DESC;
```

### 4. 실패한 Task 재실행

특정 chunk가 실패한 경우:

1. Graph View에서 실패한 task (빨간색) 클릭
2. "Clear" 버튼 클릭
3. 해당 task만 재실행됨

전체 DAG 재실행:
1. Graph View 우측 상단 "Clear" 버튼
2. "Clear" 옵션 선택
3. 전체 DAG 재실행

### 5. 성능 튜닝

#### Chunk 크기 조정

현재 기본값: 50개 종목/chunk

더 빠르게 처리하려면 (메모리가 충분한 경우):
```python
# rebuild_indicators_from_date.py 수정
chunk_size = 100  # 50 → 100으로 변경
```

더 안정적으로 처리하려면 (메모리가 부족한 경우):
```python
chunk_size = 25  # 50 → 25로 변경
```

#### 병렬 처리 증가

Airflow 설정 수정:
```bash
# airflow.cfg 또는 환경변수
AIRFLOW__CORE__PARALLELISM=32           # 기본 16 → 32
AIRFLOW__CORE__DAG_CONCURRENCY=16       # 기본 8 → 16
```

### 6. 알려진 이슈 및 해결 방법

#### 이슈 1: "Max Active Runs Reached"
**원인:** DAG의 최대 실행 횟수 제한
**해결:**
```python
# DAG 정의에서
max_active_runs=3  # 기본 1 → 3으로 증가
```

#### 이슈 2: Task가 "Queued" 상태에 머무름
**원인:** Worker가 부족
**해결:**
```bash
# Worker 수 증가
docker-compose up -d --scale airflow-worker=3
```

#### 이슈 3: 메모리 부족 (OOM)
**원인:** Chunk 크기가 너무 큼
**해결:**
- Chunk 크기를 25로 감소
- Docker 메모리 제한 증가: `docker-compose.yml`에서 `mem_limit: 4g`

#### 이슈 4: DB 연결 타임아웃
**원인:** 장시간 처리로 인한 연결 끊김
**해결:**
```python
# 이미 적용됨
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # 연결 전 ping 테스트
    pool_recycle=3600        # 1시간마다 연결 재생성
)
```

## 운영 DB에 적용하기

### 주의사항

1. **백업 필수**
```bash
# 운영 DB 백업
pg_dump -h <db-host> -U admin -d stocktrading > backup_before_rebuild.sql
```

2. **테스트 환경에서 먼저 검증**
```bash
# 테스트용 작은 날짜 범위로 시작
{
  "start_date": "2025-10-10"  # 최근 1일만
}
```

3. **피크 시간 회피**
- 장 마감 후 (오후 4시 이후)
- 주말 또는 새벽 시간 권장

### 운영 적용 절차

1. **백업 수행**
```bash
docker exec -it stock-trading-system-postgres-1 \
  pg_dump -U admin stocktrading > backup_$(date +%Y%m%d_%H%M%S).sql
```

2. **DAG 파일 배포**
```bash
# 로컬 → 운영 서버
scp F:/hhstock/stock-trading-system/airflow/dags/rebuild_indicators_from_date.py \
  user@server:/path/to/airflow/dags/

# 또는 Git을 통해
cd /path/to/stock-trading-system
git pull origin main
```

3. **Airflow DAG 새로고침**
```bash
# Airflow 웹서버 재시작 (DAG 자동 로드)
docker restart stock-trading-system-airflow-webserver-1

# 또는 DAG 수동 새로고침
# UI에서 DAGs 메뉴 → 새로고침 버튼
```

4. **테스트 실행**
```json
{
  "start_date": "2025-10-11"  # 오늘만
}
```

5. **전체 실행**
```json
{
  "start_date": "2025-09-29"
}
```

6. **모니터링 및 검증**
```sql
-- 결과 검증
SELECT
    date,
    COUNT(DISTINCT ticker) as ticker_count,
    COUNT(*) as indicator_count
FROM technical_indicators
WHERE date >= '2025-09-29'
GROUP BY date
ORDER BY date;

-- 예상 결과와 비교
-- 각 날짜마다 약 2,000~2,500개 종목의 지표가 있어야 함
```

## 예상 처리 시간

- **종목 수:** 2,500개
- **날짜 범위:** 2025-09-29 ~ 2025-10-11 (13일)
- **총 처리:** 32,500 (2,500 × 13)
- **Chunk 크기:** 50개
- **총 Chunk 수:** 50개

**예상 시간:**
- Chunk당 처리 시간: 약 5~10분
- 병렬 처리 (4 workers): 약 1~2시간
- 단일 처리: 약 4~8시간

## 트러블슈팅

### 로그 확인 위치

1. **Airflow UI 로그**
   - 가장 직관적이고 권장
   - 실시간 업데이트

2. **Docker 로그**
```bash
# Scheduler 로그
docker logs -f stock-trading-system-airflow-scheduler-1

# Worker 로그
docker logs -f stock-trading-system-airflow-worker-1
```

3. **파일 시스템 로그**
```bash
# Airflow 로그 디렉토리
cd /opt/airflow/logs/dag_id=rebuild_indicators_from_date/
ls -la
```

### 긴급 중단

```bash
# DAG 실행 중단
airflow dags pause rebuild_indicators_from_date

# 실행 중인 task 모두 종료
# UI에서 Graph View → 우측 상단 "Mark Failed"
```

## 추가 개선 사항

### 1. Dynamic Task Mapping (Airflow 2.3+)

현재는 최대 50개 chunk로 고정되어 있지만, Dynamic Task Mapping을 사용하면 종목 수에 따라 자동으로 chunk 생성 가능:

```python
# 향후 개선 버전
@task
def split_tickers(ticker_list):
    chunk_size = 50
    return [ticker_list[i:i+chunk_size]
            for i in range(0, len(ticker_list), chunk_size)]

calculate_tasks = calculate_indicators_chunk.expand(
    ticker_chunk=split_tickers(ticker_list)
)
```

### 2. 알림 시스템

```python
# 완료 시 Slack/Email 알림
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator

slack_alert = SlackWebhookOperator(
    task_id='slack_notification',
    http_conn_id='slack_webhook',
    message=f"지표 재계산 완료: {total_saved:,}개 저장",
)
```

### 3. 체크포인트 기능

```python
# 중단 시 이어서 재개할 수 있도록
# Variable에 진행 상황 저장
from airflow.models import Variable

Variable.set(
    f"rebuild_checkpoint_{start_date}",
    json.dumps({'completed_chunks': [0, 1, 2, ...]})
)
```

## 참고 문서

- [Airflow Documentation](https://airflow.apache.org/docs/)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- 프로젝트 내 관련 파일:
  - `stock-trading-system/airflow/dags/rebuild_indicators_from_date.py`
  - `stock-trading-system/backend/recalculate_by_date.py`
  - `stock-trading-system/backend/recalculate_missing_indicators.py`

## 문의 및 지원

문제 발생 시:
1. Airflow UI의 로그 확인
2. 데이터베이스 상태 확인
3. Docker 컨테이너 상태 확인 (`docker ps`)
4. 관리자에게 로그 공유
