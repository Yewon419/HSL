# Git Best Practice #13: Git을 영구 히스토리로 사용

## 원칙

Checkpoint는 로컬 undo용, Git은 영구 버전 관리용으로 구분하세요.

## 역할 구분

### Checkpoint (세션 레벨)
- 실험적 변경 전
- 빠른 undo
- 세션 내에서만 유효
- `/rewind`로 복구

### Git (프로젝트 레벨)
- 영구 보존
- 팀 협업
- 브랜치, 태그
- 언제든 복구 가능

## 실전 사용

```bash
# 1. 안전한 상태를 Git에 저장
git commit -m "feat: Working state before refactoring"

# 2. Checkpoint 자동 생성 (Claude Code)
# [리팩토링 시도]

# 3. 성공 시
git commit -m "refactor: Improve performance"

# 4. 실패 시
/rewind  # Checkpoint로 복구
# 또는
git reset --hard HEAD  # Git으로 복구
```

## 장기 보관

```bash
# 중요한 마일스톤
git tag v1.0.0
git tag v2.0.0-beta

# 언제든 복구
git checkout v1.0.0
```

## 관련 항목
- [04-git-checkpoints-vs-commits.md](04-git-checkpoints-vs-commits.md)
