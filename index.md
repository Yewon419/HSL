# 📚 hhstock 문서 인덱스

**마지막 업데이트**: 2025-11-22

## 📖 문서 목록

### 🔴 긴급/필독 문서

| 문서 | 작성일 | 용도 | 상태 |
|------|--------|------|------|
| [start_hsl.md](./start_hsl.md) | 2025-11-05 | **시작 가이드 (필독!)** | ✅ 최신 |
| [WORK_PROGRESS_20251105.md](./WORK_PROGRESS_20251105.md) | 2025-11-05 | **스크리닝 & 백테스팅 시스템 + 토큰 오류 수정** | ✅ 완료 |

### 📊 일일 작업 진행 현황

| 날짜 | 파일 | 주요 내용 |
|------|------|---------|
| 2025-11-22 | [WORK_PROGRESS_20251122.md](./WORK_PROGRESS_20251122.md) | ✅ **로컬 개발환경 구축** - 로컬 DB 구축, 1년치 데이터 이관, Git 저장소 초기화 |
| 2025-11-06 | [WORK_PROGRESS_20251106.md](./WORK_PROGRESS_20251106.md) | ✅ **시스템 기동 + 로그인 수정 + 날짜 필터 개선** - Airflow DB 분리, 로그인 비밀번호 수정, 동적 날짜 필터 적용 |
| 2025-11-05 | [WORK_PROGRESS_20251105.md](./WORK_PROGRESS_20251105.md) | ✅ **스크리닝 & 백테스팅 구현 파악 + Frontend 토큰 오류 수정** - 32개 지표, 기본 전략 3개, 사용자 전략 관리 |
| 2025-11-04 | [WORK_PROGRESS_20251104.md](./WORK_PROGRESS_20251104.md) | ✅ **UI 데이터 연동 완성** - DB 연결 문제 해결 |
| 2025-11-03 | [start_hsl.md](./start_hsl.md#2025-11-03-본일---완료-) | ✅ **November 3 주가/지표 수집 완료** |
| 2025-10-30 | [WORK_PROGRESS_20251030.md](./WORK_PROGRESS_20251030.md) | ✅ **KOSDAQ 누락 문제 해결** |

### 🔧 시스템 설정 가이드

| 문서 | 용도 | 읽어야 할 때 |
|------|------|-----------|
| [DATABASE_CONFIG.md](./DATABASE_CONFIG.md) | DB 연결 및 조회 | "데이터베이스를 조회하고 싶을 때" |
| [PYTHON_SAMPLE_CODE.md](./PYTHON_SAMPLE_CODE.md) | Python 스크립트 샘플 | "Python 코드를 작성할 때" |
| [MISSING_DATA_RECOVERY.md](./MISSING_DATA_RECOVERY.md) | 누락 데이터 복구 | "특정 날짜 데이터가 없을 때" |

### 📝 기능별 가이드

| 문서 | 기능 | 상태 |
|------|------|------|
| [SCREENING_BACKTESTING_IMPLEMENTATION_GUIDE.md](./SCREENING_BACKTESTING_IMPLEMENTATION_GUIDE.md) | **스크리닝 & 백테스팅 시스템** - 32개 지표, 다중 조건, 전략 관리 | ✅ 완성 |
| [MANUAL_DATA_COLLECTION_20251023.md](./MANUAL_DATA_COLLECTION_20251023.md) | 주가/지수 수동 수집 | ✅ 검증됨 |
| [MANUAL_INDICATOR_CALCULATION_20251023.md](./MANUAL_INDICATOR_CALCULATION_20251023.md) | 기술 지표 수동 계산 | ✅ 검증됨 |
| [NOTIFICATION_SETUP_GUIDE.md](./NOTIFICATION_SETUP_GUIDE.md) | 알림 설정 (Slack/Gmail) | ✅ 완성 |

### 🏗️ 아키텍처 및 분석 문서

| 문서 | 내용 |
|------|------|
| [docs/AIRFLOW_COMPLETE_DESIGN.md](./docs/AIRFLOW_COMPLETE_DESIGN.md) | Airflow DAG 완전 설계 |
| [KOSDAQ_COLLECTION_FIX.md](./KOSDAQ_COLLECTION_FIX.md) | KOSDAQ 수집 오류 분석 |
| [SOLUTION_COMPARISON_5METHODS.md](./SOLUTION_COMPARISON_5METHODS.md) | 5가지 해결 방안 비교 |

### ✅ 변경 사항 문서

| 문서 | 내용 | 날짜 |
|------|------|------|
| [CHANGES_20251023.md](./CHANGES_20251023.md) | 알림 기능 추가 | 2025-10-23 |
| [ANALYSIS_REPORT_20251028.md](./ANALYSIS_REPORT_20251028.md) | 트랜잭션 문제 분석 | 2025-10-28 |
| [IMPLEMENTATION_COMPLETE_20251028.md](./IMPLEMENTATION_COMPLETE_20251028.md) | 구현 완료 현황 | 2025-10-28 |

---

## 🚀 빠른 시작

### 처음 시작할 때
1. **[start_hsl.md](./start_hsl.md)** 읽기 (5분)
2. **Docker 실행**: `docker-compose up -d`
3. **로그인**: http://localhost:8000 에서 `testuser2` / `testpass123`

### 데이터를 조회하고 싶을 때
1. **[DATABASE_CONFIG.md](./DATABASE_CONFIG.md)** 읽기
2. Python 또는 psql로 직접 조회

### Python 스크립트를 작성할 때
1. **[PYTHON_SAMPLE_CODE.md](./PYTHON_SAMPLE_CODE.md)** 참고
2. 샘플 코드 복사해서 수정

### 데이터가 누락되었을 때
1. **[MISSING_DATA_RECOVERY.md](./MISSING_DATA_RECOVERY.md)** 읽기
2. 제시된 Python 스크립트 실행

---

## 📌 현재 시스템 상태 (2025-11-22)

### ✅ 운영 상태
```
상태: 🟢 모든 시스템 정상 작동
마지막 업데이트: 2025-11-05
마지막 작업: 스크리닝 & 백테스팅 시스템 구현 파악 + Frontend 토큰 오류 수정

🆕 새로 추가된 기능:
├─ 32개 기술지표를 활용한 다중 조건 스크리닝
├─ 사용자 정의 전략 저장/로드/삭제 기능
├─ 기본 제공 전략 3개 (모멘텈, 과매도, 안정추세)
└─ 포트폴리오 백테스팅 & 성과 분석
```

### 📊 데이터 현황
```
운영 DB (192.168.219.103:5432)
├─ 종목: 2,781개
├─ 주가: 3,093,142개 (1,275일)
├─ 지표: 3,005,232개 (1,262일)
└─ 최신: 2025-11-05
```

### 🔗 서비스 URL
| 서비스 | URL | 포트 |
|--------|-----|------|
| UI 프론트엔드 | http://localhost:8000 | 8000 |
| API 문서 | http://localhost:8000/docs | 8000 |
| Airflow | http://localhost:8080 | 8080 |
| Grafana | http://localhost:3000 | 3000 |
| InfluxDB | http://localhost:8086 | 8086 |

---

## 🎯 주요 변경 이력

### 2025-11-22 ✅
**로컬 개발환경 구축 및 Git 초기화**
- ✅ 로컬 DB 구축 (Docker 내부 postgres)
- ✅ 운영 DB → 로컬 DB 1년치 데이터 이관 (130만 레코드)
- ✅ Git 저장소 초기화 (685개 파일)
- ✅ 개발/운영 환경 분리 완료
- 📄 문서: [WORK_PROGRESS_20251122.md](./WORK_PROGRESS_20251122.md)

### 2025-11-05 ✅
**시스템 재기동 및 Frontend 버그 수정**
- ✅ Docker Compose 전체 컨테이너 재기동
- ✅ 2025-11-05 주가 데이터 수집 (2,760개)
- ✅ 기술 지표 계산 (2,757개)
- ✅ Frontend app.js 기술지표 선택 오류 수정
- 📄 문서: [WORK_PROGRESS_20251105.md](./WORK_PROGRESS_20251105.md)

### 2025-11-04 ✅
**UI 데이터 연동 완성**
- ✅ 로그인 정상화 (JWT 인증)
- ✅ API 데이터 조회 정상화
- ✅ DB 연결 문제 완전 해결
- 📄 문서: [WORK_PROGRESS_20251104.md](./WORK_PROGRESS_20251104.md)

### 2025-11-03 ✅
**November 3 데이터 수집 완료**
- ✅ 2,760개 종목 주가 수집
- ✅ 기술 지표 계산 완료
- 데이터: 3,087,622개 가격 + 2,999,698개 지표

### 2025-10-30 ✅
**KOSDAQ 누락 문제 해결**
- ✅ KOSPI 959개 → KOSPI+KOSDAQ 2,759개 (+188%)
- ✅ pykrx 의존성 추가
- 📄 문서: [WORK_PROGRESS_20251030.md](./WORK_PROGRESS_20251030.md)

---

## 📋 중요 공지

### ⚠️ 새로운 문서 작성 시 반드시 따를 것

새로운 작업을 완료하면 다음과 같은 순서로 진행하세요:

1. **WORK_PROGRESS_YYYYMMDD.md 작성**
   ```markdown
   # 작업 진행 현황 - YYYY년 MM월 DD일

   ## 📋 요약
   ## 🔍 문제 및 해결
   ## ✅ 결과
   ```

2. **start_hsl.md 업데이트**
   - 최신 상태 정보 추가
   - 새 문서 링크 추가
   - 완료된 작업 표시 (✅)

3. **index.md 업데이트**
   - 새 문서를 문서 목록에 추가
   - 날짜 및 상태 기입
   - 변경 이력에 추가

### 📝 작성 가이드
- 마크다운 형식 사용
- 코드 블록은 언어 명시 (예: ```python)
- 결과물은 스크린샷 또는 JSON으로 포함
- 문제의 근본 원인을 명확히 기술
- 재발 방지 방법 명시

---

## 🔄 자동화 설정

### 매일 자동으로 실행
```
16:30 KST (07:30 UTC) → daily_collection_dag (주가/지수 수집)
17:30 KST (08:30 UTC) → technical_indicator_dag (기술 지표 계산)
```

모니터링: http://localhost:8080 (Airflow Web UI)

---

## 📞 기술 지원

### 문제 발생 시 체크리스트

1. **로그인 문제**
   - [start_hsl.md - 로그인 섹션](./start_hsl.md#긴급-조치-20251028) 참고
   - DATABASE_URL 확인

2. **데이터 조회 문제**
   - [DATABASE_CONFIG.md](./DATABASE_CONFIG.md) 읽기
   - DB 연결 테스트 실행

3. **API 오류**
   - [WORK_PROGRESS_20251104.md - 테스트 결과](./WORK_PROGRESS_20251104.md#-테스트-결과) 참고
   - `docker logs stock-backend` 확인

4. **데이터 누락**
   - [MISSING_DATA_RECOVERY.md](./MISSING_DATA_RECOVERY.md) 읽기
   - 수동 수집 스크립트 실행

---

**마지막 수정**: 2025-11-04
**담당자**: Claude Code AI
**상태**: ✅ 완료 및 운영 중
