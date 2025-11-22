# Claude Code 빠른 시작 가이드

**목표**: 5분 안에 안전하게 Claude Code 사용 시작하기

## Step 1: Git 저장소 생성 (1분)

```bash
# 프로젝트 디렉토리로 이동
cd your-project

# Git 초기화
git init

# Git 사용자 정보 설정
git config user.name "Your Name"
git config user.email "your.email@example.com"

# 현재 상태 커밋
git add .
git commit -m "Initial commit: Baseline before Claude Code"
```

## Step 2: CLAUDE.md 생성 (2분)

```bash
# CLAUDE.md 파일 생성
cat > CLAUDE.md << 'EOF'
# [프로젝트명]

## Tech Stack
- 언어:
- 프레임워크:
- 데이터베이스:

## Commands
- 실행:
- 테스트:
- 린트:

## Code Style
-

## Rules for Claude
- **NEVER** use --no-verify
- **ALWAYS** create feature branch first
- **ALWAYS** write tests before implementation
- **ALWAYS** keep diffs under 200 lines
- **ALWAYS** ask for plan approval before large changes

## Forbidden
- Never commit .env files
- Never modify tests to match wrong implementation
- Never skip pre-commit hooks
EOF

# 커밋
git add CLAUDE.md
git commit -m "docs: Add CLAUDE.md"
```

## Step 3: Feature 브랜치 생성 (30초)

```bash
# 작업할 기능에 맞게 브랜치 이름 변경
git checkout -b feature/your-feature-name
```

## Step 4: Claude에게 작업 요청 (1분)

```
"[기능명]을 구현하려고 해. 3단계 계획을 세워줘.
각 단계는:
- 200 lines 이하
- 테스트 포함
- 독립적으로 작동

계획만 먼저 보여주고, 승인을 기다려줘"
```

## Step 5: 한 단계씩 진행 (30초)

```
"Step 1만 구현해줘.
테스트 먼저 작성하고, 구현 후, 모든 테스트가 통과하면 커밋해줘"
```

## 완료! 🎉

이제 안전하게 Claude Code를 사용할 준비가 되었습니다.

---

## 기억할 것

### ✅ 항상 하기

- Git 커밋 먼저
- 브랜치 만들기
- 계획 승인
- 테스트 작성
- 작게 나누기

### ❌ 절대 하지 않기

- 계획 없이 큰 작업
- 테스트 생략
- Git hook 스킵
- 한 번에 많은 변경

---

## 문제 발생 시

### 잘못된 변경이 되었을 때
```bash
# Rewind 사용
# Claude에게: "/rewind를 사용해서 이전 상태로 돌아가줘"

# 또는 Git으로 되돌리기
git reset --hard HEAD
```

### 계획이 잘못되었을 때
```
"계획을 다시 세워줘. Step 2가 너무 큰 것 같아"
```

### 테스트가 실패할 때
```
"테스트를 수정하지 말고, 구현을 고쳐서 테스트를 통과시켜줘"
```

---

## 다음 단계

- [README.md](README.md) - 전체 가이드 개요
- [01-git-create-branches-first.md](01-git-create-branches-first.md) - Git 워크플로우 상세
- [16-ask-for-plan-first.md](16-ask-for-plan-first.md) - 계획 수립 상세
- [31-write-tests-first-tdd.md](31-write-tests-first-tdd.md) - TDD 상세
- [69-small-changes-philosophy.md](69-small-changes-philosophy.md) - 점진적 개발 상세

**이 5개 파일만 읽어도 80%는 안전합니다.**
