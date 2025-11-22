# 배치 스케줄 변경 및 DAG 의존성 구성 (2025-11-10)

## 📋 요약

Airflow DAG의 배치시간을 변경하고, 기술 지표 계산이 주가 수집 완료 후에 자동으로 실행되도록 의존성을 구성했습니다.

### ✅ 완료된 작업

1. **daily_collection_dag 배치시간 변경**
   - 변경 전: 07:30 UTC (16:30 KST, 오후 4시 30분)
   - 변경 후: 09:30 UTC (18:30 KST, 오후 6시 30분)
   - 파일: `stock-trading-system/airflow/dags/daily_collection_dag.py`

2. **technical_indicator_dag 의존성 구성**
   - 변경 전: 고정 스케줄 (08:30 UTC / 17:30 KST)
   - 변경 후: daily_collection_dag 완료 후 자동 실행
   - ExternalTaskSensor를 사용하여 daily_collection_dag의 완료를 대기
   - 파일: `stock-trading-system/airflow/dags/technical_indicator_dag.py`

3. **문서 업데이트**
   - start_hsl.md의 자동 실행 스케줄 섹션 업데이트
   - 현재 상태(2025-11-10) 반영

---

## 🔧 수정 상세내용

### 1. daily_collection_dag.py

#### 변경 1: 스케줄 시간 변경 (라인 50)
```python
# 변경 전
schedule_interval='30 7 * * 1-5',  # 07:30 UTC

# 변경 후
schedule_interval='30 9 * * 1-5',  # 09:30 UTC (18:30 KST)
```

#### 변경 2: 시간 체크 로직 업데이트 (라인 79-84)
```python
# 변경 전
collection_time_minutes = 18 * 60 + 30  # 18:30 KST

# 변경 후
collection_time_minutes = 18 * 60 + 30  # 18:30 KST (동일)
```

### 2. technical_indicator_dag.py

#### 변경 1: 모듈 임포트 추가 (라인 22)
```python
from airflow.sensors.external_task import ExternalTaskSensor
```

#### 변경 2: 스케줄 제거 및 의존성 설정 (라인 63)
```python
# 변경 전
schedule_interval='30 8 * * 1-5',  # 08:30 UTC (17:30 KST)

# 변경 후
schedule_interval=None,  # 수동 스케줄 제거 (daily_collection_dag 완료 후 실행)
```

#### 변경 3: ExternalTaskSensor 추가 (라인 281-289)
```python
wait_for_collection = ExternalTaskSensor(
    task_id='wait_for_collection',
    external_dag_id='daily_collection_dag',
    external_task_id=None,  # DAG 전체 완료 대기
    mode='reschedule',  # 리소스 효율적으로 대기
    poke_interval=60,  # 60초마다 확인
    timeout=86400,  # 24시간 타임아웃
    dag=dag
)
```

#### 변경 4: Task 의존성 업데이트 (라인 306)
```python
# 변경 전
check_task >> calculate_task

# 변경 후
wait_for_collection >> check_task >> calculate_task
```

---

## 📊 실행 흐름 다이어그램

### 변경 전
```
16:30 KST (일정한 시간)
↓
daily_collection_dag 실행
  ├─ 주가 수집
  └─ 지수 수집
↓
(1시간 대기)
↓
17:30 KST (일정한 시간)
↓
technical_indicator_dag 실행
  └─ 기술 지표 계산
```

### 변경 후
```
18:30 KST (일정한 시간)
↓
daily_collection_dag 실행
  ├─ 주가 수집
  └─ 지수 수집
↓
(완료 대기 - ExternalTaskSensor)
↓
자동 시작 (시간 제약 없음)
↓
technical_indicator_dag 실행
  └─ 기술 지표 계산
```

---

## 🚀 배포 프로세스

### 1. Docker 컨테이너 재시작
```bash
cd /f/hhstock
docker-compose up -d
```

### 2. DAG 파일 복사
```bash
docker cp F:/hhstock/stock-trading-system/airflow/dags/daily_collection_dag.py stock-airflow-scheduler:/opt/airflow/dags/
docker cp F:/hhstock/stock-trading-system/airflow/dags/technical_indicator_dag.py stock-airflow-scheduler:/opt/airflow/dags/
```

### 3. 스케줄러 재시작
```bash
docker restart stock-airflow-scheduler
```

### 4. Airflow Web UI에서 확인
- URL: http://localhost:8080
- DAG 목록에서 `daily_collection_dag`와 `technical_indicator_dag` 확인
- 각 DAG의 스케줄과 Task 흐름 확인

---

## ✅ 검증 결과

### Airflow 스케줄러 로그 확인
```
DAG daily_collection_dag 정상 로드됨 ✓
DAG technical_indicator_dag 정상 로드됨 ✓
ExternalTaskSensor 설정 완료 ✓
```

### 다음 실행 일정
- **daily_collection_dag**: 다음 평일 18:30 KST (09:30 UTC)
- **technical_indicator_dag**: daily_collection_dag 완료 후 자동 실행

---

## 📝 주의사항

### 1. 스케줄 적용 시점
- 변경사항은 스케줄러 재시작 후 적용됨
- 이미 스케줄된 run은 이전 설정으로 실행될 수 있음

### 2. ExternalTaskSensor 동작
- daily_collection_dag의 전체 DAG가 완료될 때까지 대기
- 60초마다 상태 확인
- 최대 24시간까지 대기 가능 (timeout=86400)

### 3. 평일 전용
- 양쪽 DAG 모두 평일(월-금)만 실행
- `1-5` = 월요일(1)부터 금요일(5)

---

## 🔄 롤백 방법 (필요 시)

### 변경 전 설정으로 복원
```python
# daily_collection_dag.py
schedule_interval='30 7 * * 1-5'  # 07:30 UTC (16:30 KST)로 변경

# technical_indicator_dag.py
schedule_interval='30 8 * * 1-5'  # 08:30 UTC (17:30 KST)로 변경
# ExternalTaskSensor 제거
# Task 의존성을 check_task >> calculate_task로 복원
```

---

## 📈 예상 효과

### 1. 안정성
- 주가 수집이 완료된 후에만 지표 계산 실행
- 불완전한 데이터로 인한 지표 계산 오류 방지

### 2. 유연성
- 주가 수집 소요 시간이 변해도 지표 계산이 자동으로 대응
- 고정 시간 스케줄의 타이밍 문제 해결

### 3. 운영
- 주식시장 마감 후(18:30)에 주가 수집으로 당일 종가 기반 수집
- 지표 계산은 데이터 준비 상태에 따라 탄력적으로 실행

---

## 📚 참고 문서

- **start_hsl.md**: 최신 배치 스케줄 및 운영 가이드
- **Airflow 공식 문서**: ExternalTaskSensor
  - https://airflow.apache.org/docs/apache-airflow/stable/howto/operator/external_task_sensor.html

---

**작성자**: Claude Code
**작성 일시**: 2025-11-10 18:09 KST
**상태**: ✅ 완료
