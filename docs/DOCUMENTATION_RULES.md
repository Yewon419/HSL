# 📋 문서 정리 규칙

## 📁 디렉토리 구조

```
docs/
├── index.md                          # 문서 목차
├── DOCUMENTATION_RULES.md            # 이 파일
├── architecture/                     # 시스템 아키텍처 및 설계
│   └── {component}_architecture.md
├── deployment/                       # 배포 및 운영
│   └── {target}_{type}_YYYYMMDD.md
├── development-logs/                 # 개발 로그 및 진행 상황
│   └── WORK_PROGRESS_{YYYYMMDD}.md
├── guides/                           # 사용 가이드 및 튜토리얼
│   └── {topic}_guide.md
├── operations/                       # 운영 가이드 (신규)
│   └── {topic}_operations.md
└── troubleshooting/                  # 문제 해결 가이드 (신규)
    └── {issue}_troubleshooting.md
```

---

## 📝 파일 명명 규칙

### 1. 일반 규칙
- **패턴**: `{descriptor}_{type}_{date}.md` 또는 `{descriptor}_{type}.md`
- **사용**: 소문자 + 언더스코어 조합
- **날짜**: `YYYYMMDD` 형식 (2025-11-10 → 20251110)

### 2. 카테고리별 명명

#### **배포 (deployment/)**
```
{서버명/환경}_{유형}_YYYYMMDD.md

예시:
- 101_scheduler_deployment_20251110.md
- production_setup_guide_20251110.md
- 101_airflow_config_20251110.md
```

#### **개발 로그 (development-logs/)**
```
WORK_PROGRESS_YYYYMMDD.md
CHANGELOG_YYYYMMDD.md
HOTFIX_{issue}_YYYYMMDD.md

예시:
- WORK_PROGRESS_20251110.md
- CHANGELOG_20251110.md
- HOTFIX_airflow_schedule_20251110.md
```

#### **가이드 (guides/)**
```
{topic}_guide.md
{topic}_tutorial.md

예시:
- airflow_dag_guide.md
- database_user_manual.md
- api_integration_guide.md
```

#### **운영 (operations/)**
```
{topic}_operations.md
{topic}_checklist.md
{topic}_monitoring.md

예시:
- daily_batch_operations.md
- airflow_monitoring.md
- database_maintenance_checklist.md
```

#### **트러블슈팅 (troubleshooting/)**
```
{issue}_troubleshooting.md

예시:
- airflow_dag_failed_troubleshooting.md
- database_connection_troubleshooting.md
```

---

## 📄 파일 내용 구조

### 기본 템플릿
```markdown
# {제목}

## 📋 개요
- 목적
- 작성 일시
- 담당자

## 🎯 내용

### 섹션 1
내용

### 섹션 2
내용

## ⚠️ 주의사항

## 📞 참고 자료 및 링크

---
**작성자**: Claude Code
**작성일**: YYYY-MM-DD
**상태**: ✅ 완료 / 🔄 진행중 / ⏳ 대기중
```

---

## 🏷️ 파일 헤더 규칙

모든 MD 파일의 상단에 다음 정보 기록:

```markdown
# {제목}

**작성일**: YYYY-MM-DD
**카테고리**: {카테고리}
**상태**: ✅ 완료 / 🔄 진행중
**담당자**: Claude Code

---
```

---

## 📑 index.md 업데이트 규칙

### 추가 순서
1. **날짜순 (최신순)**: 작성/수정 날짜 기준
2. **카테고리별 정렬**: 같은 날짜 내에서 카테고리 순서
3. **링크 형식**:
```markdown
- [파일 설명](path/to/file.md) - YYYY-MM-DD
```

### 예시
```markdown
## 📅 최근 작업 (2025-11-10)

### 배포
- [101 스케줄러 배포 가이드](deployment/101_scheduler_deployment_20251110.md)

### 운영
- [일일 배치 운영 매뉴얼](operations/daily_batch_operations.md)

### 개발 로그
- [작업 진행 보고서](development-logs/WORK_PROGRESS_20251110.md)
```

---

## 🗂️ 자동 생성 규칙

### start_hsl.md 기록 규칙

**운영 관련 내용만** 기록:
- ✅ 스케줄 변경
- ✅ 배포 완료
- ✅ 주요 버그 수정
- ✅ 시스템 설정 변경
- ❌ 개발 단계별 상세 과정 (→ development-logs/ 사용)

**형식**:
```markdown
## 2025-11-10 (수요일)

### 배치 스케줄 설정
- **daily_collection_dag**: 한국시간 16:30 (UTC 07:30)
- **technical_indicator_dag**: daily_collection_dag 완료 후 자동 실행

### 배포
- 운영서버 101 (192.168.219.101)에 배포 완료
```

---

## ✨ 주요 포인트

### DO ✅
- 날짜 정보 항상 포함
- 상태 표시 명확하게
- 링크는 상대 경로 사용
- 변경 사항은 CHANGELOG에 기록

### DON'T ❌
- 파일명에 특수문자 사용 (공백, 슬래시 등)
- 절대 경로 링크 사용
- 날짜 형식 혼용 (YYYYMMDD 통일)
- 한글과 영문 혼용 in 파일명

---

## 📊 문서 생명주기

```
작성 (신규)
  ↓
개발-로그 기록 (development-logs/)
  ↓
완료 (index.md 등록)
  ↓
운영 (start_hsl.md 요약)
  ↓
보관 (자동 아카이빙)
```

---

**문서 정리 규칙 v1.0**
2025-11-10 작성
지속적으로 개선될 예정
