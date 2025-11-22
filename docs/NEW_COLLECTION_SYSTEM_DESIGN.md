# 새로운 주가 데이터 수집 시스템 설계

## 문제점 분석

### 기존 Airflow 시스템의 문제
1. **Executor 작동 불능**: queued 상태의 task가 실행되지 않음
2. **복잡한 설정**: DAG, Executor, Scheduler의 상호작용이 복잡
3. **디버깅 어려움**: 문제 원인 파악에 시간 소요
4. **의존성 많음**: Airflow, Celery, Redis, Flower 등 다양한 컴포넌트
5. **scale 문제**: 실패 재시도, 로깅, 모니터링이 분산됨

---

## 새로운 시스템 아키텍처

### 핵심 원칙
- **단순성**: 필요한 것만, 최소한의 컴포넌트
- **안정성**: 직접 제어, 문제 파악 용이
- **확장성**: 추가 기능 쉽게 적용
- **모니터링**: 수집 상태 명확하게 추적

### 아키텍처 구성

```
┌─────────────────────────────────────────────┐
│  Scheduler (Linux Cron 또는 Celery Beat)   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Collection Script    │
        │ (Python)             │
        ├──────────────────────┤
        │ 1. pykrx 데이터수집  │
        │ 2. DB 저장           │
        │ 3. 지표 계산         │
        │ 4. 로깅/모니터링     │
        └──────────────┬───────┘
                       │
                       ▼
        ┌──────────────────────┐
        │ PostgreSQL Database  │
        │ (TimescaleDB)        │
        └──────────────────────┘
```

---

## 구현 방식

### 방식 1: Linux Cron (추천 - 가장 단순)
**장점:**
- 시스템 표준 도구
- 설정 단순 (crontab)
- 디버깅 쉬움
- 오버헤드 최소

**구성:**
```
# /etc/crontab
0 17 * * 1-5  root  /app/scripts/collect_stock_data.sh
0 18 * * 1-5  root  /app/scripts/calculate_indicators.sh
```

### 방식 2: Celery Beat (중간 복잡도)
**장점:**
- 기존 Celery Worker 재사용 가능
- 분산 스케줄링 가능
- 재시도 기능 내장

**구성:**
- Celery Beat로 스케줄 관리
- Celery Worker에서 실행
- Redis로 상태 추적

### 방식 3: APScheduler (유연)
**장점:**
- 복잡한 스케줄 지원
- Python 네이티브
- 웹 대시보드 가능

---

## 권장: 방식 1 (Cron) + Celery Worker

### 이유:
1. **간단함**: Cron은 단순, 이해하기 쉬움
2. **기존 리소스 활용**: 이미 있는 Celery Worker 사용
3. **확장 가능**: 필요시 APScheduler나 더 복잡한 솔루션으로 마이그레이션 가능
4. **운영**: Airflow 제거로 관리 포인트 감소

---

## 수집 스크립트 구조

### 1. 주가 수집 (`collect_stock_data.py`)
```python
def main():
    target_date = date.today()

    # 1. pykrx로 데이터 수집
    prices = fetch_stock_prices(target_date)
    indices = fetch_market_indices(target_date)

    # 2. DB 저장
    save_prices(prices, target_date)
    save_indices(indices, target_date)

    # 3. 로깅
    log_collection_status(target_date, len(prices), len(indices))

    # 4. 이메일/슬랙 알림 (선택)
    notify_completion(target_date, True)
```

### 2. 지표 계산 (`calculate_indicators.py`)
```python
def main():
    target_date = date.today()

    # 1. 주가 데이터 로드
    prices = load_prices(target_date)

    # 2. 기술적 지표 계산
    indicators = compute_indicators(prices)

    # 3. DB 저장
    save_indicators(indicators, target_date)

    # 4. 로깅
    log_indicator_status(target_date, len(indicators))
```

### 3. 누락 데이터 복구 (`recover_missing_data.py`)
```python
def main(start_date, end_date):
    """특정 기간의 누락된 데이터 복구"""
    for target_date in date_range(start_date, end_date):
        if is_trading_day(target_date) and not has_data(target_date):
            collect_date(target_date)
            calculate_indicators_for_date(target_date)
```

---

## 로깅 및 모니터링

### 로그 파일 구조
```
/var/log/stock-collection/
├── collection_2025-10-20.log
├── indicators_2025-10-20.log
└── errors_2025-10-20.log
```

### 수집 상태 추적 테이블
```sql
CREATE TABLE collection_log (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    collection_status VARCHAR(50),
    prices_count INTEGER,
    indices_count INTEGER,
    indicators_count INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    UNIQUE(date)
);
```

---

## 구현 단계

### Phase 1: 기본 수집 스크립트 (1일)
- [x] `collect_stock_data.py` 작성
- [x] `calculate_indicators.py` 작성
- [x] pykrx 호출 및 DB 저장 검증

### Phase 2: Cron 스케줄 설정 (1일)
- [ ] crontab 설정
- [ ] 로그 로테이션 설정
- [ ] 실행 테스트

### Phase 3: 모니터링 및 알림 (1일)
- [ ] 수집 상태 로깅
- [ ] 실패 알림 (이메일/슬랙)
- [ ] 대시보드 구현

### Phase 4: 데이터 복구 유틸리티 (1일)
- [ ] 누락 데이터 자동 복구
- [ ] 수동 트리거 CLI 도구

---

## 마이그레이션 계획

### 1단계: 새 시스템 병행 실행 (1주)
- 새 수집 스크립트 실행
- 기존 Airflow 병행 유지
- 데이터 검증

### 2단계: Airflow 제거 (1일)
- Airflow 컨테이너 중지
- docker-compose에서 제거

### 3단계: 최적화 (지속)
- 성능 모니터링
- 에러 처리 개선

---

## 예상 효과

| 항목 | 기존 (Airflow) | 신규 (Cron) |
|------|----------------|-----------|
| 관리 포인트 | 8+ | 2 |
| 디버깅 시간 | 30분+ | 5분 |
| 메모리 사용 | 1GB+ | 200MB |
| 실패 복구 | 복잡 | 간단 |
| 모니터링 | Flower | 로그 파일 |

---

## 체크리스트

- [ ] `collect_stock_data.py` 작성
- [ ] `calculate_indicators.py` 작성
- [ ] `recover_missing_data.py` 작성
- [ ] Cron 스케줄 설정
- [ ] 로그 수집 및 모니터링
- [ ] Airflow 제거
- [ ] 2025-10-20 데이터 수집
- [ ] 검증 및 테스트

---

## 연락 / 질문
오늘 설계 문서 작성 시작. 내일부터 구현 예정.
