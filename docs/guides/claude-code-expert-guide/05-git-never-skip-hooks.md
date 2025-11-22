# Git Best Practice #5: Git Hook을 절대 스킵하지 않기

## 원칙

`--no-verify`, `--no-gpg-sign` 등의 플래그를 사용하여 Git hook을 건너뛰지 마세요.

## 이유

Git hook은 다음을 보장합니다:
- 코드 품질 (lint, format)
- 테스트 통과
- 커밋 메시지 규칙
- 보안 검사
- 시크릿 유출 방지

Hook을 건너뛰면:
- 깨진 코드가 커밋됨
- 팀 규칙 위반
- CI/CD 실패
- 보안 문제 발생 가능

## 실전 예시

### ❌ 절대 하지 말 것

```bash
git commit --no-verify -m "quick fix"
git push --no-verify
```

### ✅ 올바른 방법

```bash
# Hook이 실패하면
git commit -m "fix: update validation"
# → pre-commit hook 실행 → 실패

# Hook이 지적한 문제 수정
# 다시 커밋
git add .
git commit -m "fix: update validation"
# → 성공
```

## Pre-commit Hook 예시

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run tests
npm test
if [ $? -ne 0 ]; then
    echo "Tests failed. Commit rejected."
    exit 1
fi

# Run linter
npm run lint
if [ $? -ne 0 ]; then
    echo "Linting failed. Commit rejected."
    exit 1
fi

# Check for secrets
git diff --cached | grep -i "api[_-]key\|secret\|password"
if [ $? -eq 0 ]; then
    echo "Possible secret detected. Commit rejected."
    exit 1
fi
```

## Hook 실패 시 대응 방법

### 1. 문제 파악
```bash
# Hook이 무엇을 검사하는지 확인
cat .git/hooks/pre-commit
```

### 2. 문제 수정
```bash
# Lint 오류 수정
npm run lint:fix

# 테스트 수정
npm test

# Format 수정
npm run format
```

### 3. 재시도
```bash
git add .
git commit -m "fix: ..."
```

## 예외 상황

**정말로 hook을 건너뛰어야 하는 경우만:**
- Hook 자체에 버그가 있을 때
- 긴급 핫픽스 (단, 나중에 반드시 수정)
- 사용자가 명시적으로 요청할 때

이 경우에도:
```bash
# 이유를 명확히 기록
git commit --no-verify -m "hotfix: critical security issue

Bypassing hooks due to production emergency.
TODO: Fix lint issues in follow-up commit"
```

## Claude에게 요청하는 방법

```
"Git hook을 절대 건너뛰지 말고,
hook이 실패하면 문제를 수정한 후 다시 커밋해줘"
```

## 팁

- CLAUDE.md에 명시: "Never use --no-verify"
- Pre-commit hook 설정: husky, pre-commit 등
- Hook 실패 시 자동으로 수정하도록 설정

## 관련 항목

- [38-pre-commit-hooks.md](38-pre-commit-hooks.md) - Pre-commit hook 설정
- [85-lint-type-check.md](85-lint-type-check.md) - Lint 및 타입 체크
