# 2025-11-10 작업 진행 보고서

**작성일**: 2025-11-10
**카테고리**: Development / Operations
**상태**: ✅ 완료
**담당자**: Claude Code

---

## 📋 요약

**주제**: 배치 스케줄 최적화 및 운영 체계 확립

**주요 성과**:
1. ✅ 배치 스케줄 변경: 16:30 KST (07:30 UTC) 평일 실행
2. ✅ DAG 의존성 관리 개선: ExternalTaskSensor → TriggerDagRunOperator
3. ✅ 운영 환경 분리: 운영서버(101)에서만 실행
4. ✅ 운영 가이드 작성: 일일 배치 운영 매뉴얼 완성
5. ✅ 문서 체계 확립: DOCUMENTATION_RULES.md 작성 및 적용

---

## 🔄 작업 진행 내용

### 1. 기술 지표 차트 검색 수정

**파일**: `stock-trading-system/frontend/app.js`

**문제**: 기술 지표 차트의 종목 자동완성 기능이 작동하지 않음
- API 엔드포인트에서 `limit=1000` 검증
- 프론트엔드가 `limit=3000` 요청 → 검증 실패

**해결방법**:
```javascript
// 변경 전 (Line 186)
const response = await fetch(`/api/stocks/?limit=3000&offset=0`);

// 변경 후
const response = await fetch(`/api/stocks/?limit=1000&offset=0`);
```

**결과**: ✅ 검색 자동완성 정상 작동

---

### 2. 배치 스케줄 변경

#### 2.1 daily_collection_dag.py 수정

**파일**: `stock-trading-system/airflow/dags/daily_collection_dag.py`

**변경 사항**:

| 항목 | 변경 전 | 변경 후 |
|------|--------|--------|
| schedule_interval | `'30 9 * * 1-5'` | `'30 7 * * 1-5'` |
| 실행 시간 (KST) | 18:30 KST | **16:30 KST** |
| 실행 시간 (UTC) | 09:30 UTC | **07:30 UTC** |
| 시간 체크 로직 | 18:30 확인 | **16:30 확인** |
| start_date | 2025-10-20 | **2025-11-10** |
| 의존성 트리거 | - | **TriggerDagRunOperator 추가** |

**주요 코드 변경** (lines 50-51, 82-83, 291):
```python
# 스케줄 변경
schedule_interval='30 7 * * 1-5',  # 한국시간 16:30 (UTC 07:30)

# 시간 체크 로직 수정
collection_time_minutes = 16 * 60 + 30  # 16:30 KST

# TriggerDagRunOperator 추가
trigger_indicator_dag = TriggerDagRunOperator(
    task_id='trigger_technical_indicator_dag',
    trigger_dag_id='technical_indicator_dag',
    dag=dag
)

# 의존성 연결
check_task >> [price_group, indices_group] >> trigger_indicator_dag
```

#### 2.2 technical_indicator_dag.py 수정

**파일**: `stock-trading-system/airflow/dags/technical_indicator_dag.py`

**변경 사항**:

| 항목 | 변경 전 | 변경 후 |
|------|--------|--------|
| schedule_interval | 자동 스케줄 | **None (수동 트리거)** |
| 의존성 관리 | ExternalTaskSensor | **TriggerDagRunOperator으로 인한 자동 호출** |
| start_date | 2025-10-20 | **2025-11-10** |

**주요 코드 변경** (lines 63, 28-29):
```python
# schedule_interval 제거 (수동 트리거로 변경)
schedule_interval=None,

# ExternalTaskSensor import 제거
# (이제 daily_collection_dag에서 TriggerDagRunOperator로 호출)
```

---

### 3. 운영 환경 분리

**상태**: ✅ 완료

**구성**:
- **운영서버 (101, 192.168.219.101)**: Airflow 스케줄러 실행 중
  - daily_collection_dag: 매일 16:30 KST 실행
  - technical_indicator_dag: 수집 완료 후 자동 실행

- **개발 PC (로컬)**: Docker 중지 상태
  - 운영 환경과의 충돌 제거
  - 필요 시에만 로컬 테스트용으로 실행

**배포 방식**:
- SCP로 DAG 파일 전송: `/home/yunsang/stock-trading-system/airflow/dags/`
- Docker 컨테이너 재시작: `docker restart stock-airflow-scheduler`

---

### 4. 문서 작성

#### 4.1 DOCUMENTATION_RULES.md (새 파일)

**생성**: `docs/DOCUMENTATION_RULES.md`

**내용**:
- 📁 디렉토리 구조 정의 (8개 카테고리)
- 📝 파일 명명 규칙 (카테고리별)
- 📄 파일 헤더 템플릿
- 📑 index.md 업데이트 규칙
- 🗂️ start_hsl.md 기록 규칙

**디렉토리 구조**:
```
docs/
├── architecture/          # 시스템 아키텍처
├── deployment/            # 배포 및 운영
├── development-logs/      # 개발 로그
├── guides/                # 사용 가이드
├── operations/            # 운영 가이드 (신규)
├── troubleshooting/       # 문제 해결 (신규)
├── planning/              # 계획 문서
└── airflow_backup/        # Airflow 백업
```

**명명 규칙**:
- **배포**: `{서버}_{유형}_YYYYMMDD.md`
- **개발 로그**: `WORK_PROGRESS_YYYYMMDD.md`
- **운영**: `{주제}_operations.md`
- **가이드**: `{주제}_guide.md`

#### 4.2 daily_batch_operations.md (새 파일)

**생성**: `docs/operations/daily_batch_operations.md`

**내용** (338줄):
- 📊 배치 스케줄 정의
- 🔄 배치 실행 흐름도
- 📊 모니터링 방법 (Airflow WebUI, CLI, 로그)
- ✅ 수집 데이터 검증 SQL
- ⚠️ 주의사항 (시간대, DB 연결 등)
- 🛠️ 배치 재시작 절차
- 📈 성능 최적화 방법
- 🔄 정기 점검 사항 (일일/주간/월간)
- 📞 문제 해결 Q&A

#### 4.3 docs/index.md 업데이트

**변경 사항**:
```markdown
## 📋 운영 가이드 (Operations) - NEW
- [일일 배치 운영 매뉴얼](operations/daily_batch_operations.md)

## 📚 문서 정리 규칙 (Documentation Standards) - NEW
- [문서 정리 규칙](DOCUMENTATION_RULES.md)
```

#### 4.4 start_hsl.md 업데이트

**변경 사항**:
- 상단 요약: 배치 운영 체계 확립 완료
- 스케줄 테이블: 16:30 KST (07:30 UTC) 명확화
- 주요 개선사항: TriggerDagRunOperator 설명
- 문서 링크: 운영 가이드 추가

---

## 🔍 기술 분석

### DAG 의존성 변경 분석

#### 변경 전 (ExternalTaskSensor 사용)
```
daily_collection_dag 실행
        ↓
        ↓ (센서로 완료 확인 - 최대 60초 대기)
        ↓
technical_indicator_dag 시작
```

**문제점**:
- ExternalTaskSensor가 "up_for_reschedule" 상태로 무한 재시도 (매 60초)
- DAG 간 시간 오프셋 관계 추적 필요
- 불필요한 대기 시간 발생

#### 변경 후 (TriggerDagRunOperator 사용)
```
daily_collection_dag 실행
        ↓
        ↓ (완료 직후)
        ↓
TriggerDagRunOperator 호출
        ↓
technical_indicator_dag 즉시 시작
```

**개선 효과**:
- ✅ 즉각적인 실행 (대기 시간 제거)
- ✅ DAG 간 명확한 의존성
- ✅ 완료 기반 트리거링으로 안정성 향상
- ✅ 센서 오버헤드 제거

---

## ✅ 테스트 결과

### 1. 배치 스케줄 테스트
- **환경**: 운영서버 101 (192.168.219.101)
- **DAG 목록 확인**: ✅ daily_collection_dag, technical_indicator_dag 로드됨
- **스케줄 확인**: ✅ 30 7 * * 1-5 (16:30 KST, 평일만)

### 2. 시간대 검증
- **한국 시간대**: 16:30 KST = 07:30 UTC (UTC+9) ✅
- **시간 체크 로직**: 16:30 이전일 시 스킵 (정상 작동)

### 3. 운영 환경 분리
- **운영서버**: Airflow 정상 실행 ✅
- **개발 PC**: Docker 중지 상태 ✅
- **충돌 제거**: 양쪽에서 동시 실행 불가능 ✅

---

## 📊 코드 변경 통계

| 파일 | 변경 유형 | 라인 수 |
|------|---------|--------|
| `app.js` | 수정 | 1줄 |
| `daily_collection_dag.py` | 수정 | 6줄 (스케줄, 시간 체크, 트리거) |
| `technical_indicator_dag.py` | 수정 | 4줄 (제거: ExternalTaskSensor, schedule) |
| `DOCUMENTATION_RULES.md` | 신규 | 224줄 |
| `daily_batch_operations.md` | 신규 | 338줄 |
| `docs/index.md` | 수정 | 추가 5줄 |
| `start_hsl.md` | 수정 | 수정 15줄 |

**총 신규 추가**: 567줄 (문서)

---

## 📚 관련 문서

### 참고 문서
- `docs/DOCUMENTATION_RULES.md` - 문서 정리 규칙
- `docs/operations/daily_batch_operations.md` - 운영 매뉴얼
- `docs/index.md` - 문서 목차

### 운영 문서
- `start_hsl.md` - 빠른 시작 가이드

---

## ⚠️ 주의사항

### 1. 스케줄 시간 확인
- **정확한 시간**: 16:30 KST = 07:30 UTC
- **실행 조건**: 평일만 (월-금)
- **변경 시**: Airflow 스케줄러 재시작 필수

### 2. DAG 업데이트 시
- 양쪽 DAG 파일 모두 배포 필수
- 한쪽만 수정하면 의존성 깨짐
- Docker 컨테이너 재시작 필수: `docker restart stock-airflow-scheduler`

### 3. 운영 환경 분리
- 개발 PC에서 Docker 실행 금지
- 배포는 deployment 패키지에서만 진행
- 운영서버(101)에서만 스케줄 실행

### 4. 시간대 설정
- 모든 시간값은 UTC로 저장됨 (Airflow 내부)
- 사용자 표시는 KST로 변환
- 시간 변경 시 사용자 혼동 주의

---

## 🔄 다음 단계

### 즉시 실행 (필수)
1. ✅ DAG 파일 배포 (이미 완료)
2. ✅ Docker 스케줄러 재시작 (이미 완료)
3. ✅ 문서 작성 및 업데이트 (이미 완료)

### 모니터링 (필수)
1. 2025-11-11 16:30 KST에 배치 실행 확인
2. 일일 배치 운영 매뉴얼 참고 (daily_batch_operations.md)
3. Airflow WebUI에서 DAG 상태 확인

### 선택사항
1. 배치 성능 최적화 (문서의 "성능 최적화" 섹션 참고)
2. 모니터링 대시보드 구성
3. 알림 설정 (실패 시 이메일/Slack)

---

## 📝 최종 상태

**작업 완료도**: 100% ✅

**배포 상태**:
- ✅ 코드 변경 완료
- ✅ 운영서버 배포 완료
- ✅ 문서 작성 완료

**운영 준비도**:
- ✅ 스케줄 설정 완료
- ✅ 의존성 구성 완료
- ✅ 운영 가이드 완성
- ✅ 모니터링 방법 문서화

**기대 효과**:
- 배치 실행 시간 최적화 (16:30 KST로 표준화)
- DAG 간 의존성 개선 (즉시 트리거링)
- 운영 체계 확립 (가이드 완성)
- 새로운 팀원 온보딩 용이 (문서 정리)

---

**작성자**: Claude Code
**작성일**: 2025-11-10
**상태**: ✅ 완료
