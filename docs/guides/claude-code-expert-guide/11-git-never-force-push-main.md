# Git Best Practice #11: main/master에 Force Push 금지

## 원칙

main 또는 master 브랜치에 `git push --force`를 절대 사용하지 마세요.

## 이유

- 팀원의 작업 손실
- CI/CD 파이프라인 파괴
- 프로덕션 배포 이력 손상
- 복구 불가능한 손실 가능

## ❌ 절대 하지 말 것

```bash
git checkout main
git push --force  # 💥 재앙!
git push -f       # 💥 동일하게 위험!
```

## ✅ 대안

### Feature 브랜치에서는 가능
```bash
git checkout feature/my-work
git push --force  # ✅ 자신의 브랜치에서만
```

### Main 수정이 필요하면
```bash
# 1. Revert 커밋 생성
git revert <commit-hash>

# 2. 또는 새 커밋으로 수정
git commit --fixup <commit-hash>

# 3. 절대 force push 하지 않기
git push
```

## Claude 설정

CLAUDE.md에 명시:
```markdown
## Git Rules
- **NEVER** force push to main/master
- **ALWAYS** warn user if they request it
```

## 예외 상황

정말 force push가 필요한 경우:
```
1. 민감한 정보가 커밋됨 (API 키 등)
2. 팀 전체 동의
3. 백업 완료
4. 팀원에게 공지
```

## 관련 항목
- [12-git-check-authorship.md](12-git-check-authorship.md)
