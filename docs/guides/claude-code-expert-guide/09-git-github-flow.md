# Git Best Practice #9: GitHub Flow 사용하기

## 원칙

모든 기능을 개별 이슈로 만들고, 브랜치-구현-테스트-PR 사이클을 반복하세요.

## GitHub Flow

```
1. Issue 생성
2. Feature 브랜치 생성
3. 작은 커밋들로 구현
4. PR 생성
5. 리뷰 및 테스트
6. Merge
7. 브랜치 삭제
8. /clear (컨텍스트 정리)
```

## 실전 워크플로우

```bash
# 1. Issue에서 브랜치 생성
git checkout -b feature/add-user-auth

# 2. 작업
# [Claude와 함께 구현]

# 3. 커밋
git commit -m "feat: Add user authentication"

# 4. Push
git push -u origin feature/add-user-auth

# 5. PR 생성
gh pr create --title "Add user authentication" --body "..."

# 6. Merge 후 정리
git checkout main
git pull
git branch -d feature/add-user-auth
```

## Claude에게 요청

```
"GitHub issue #123을 해결하려고 해.
1. 브랜치 생성
2. 구현
3. 테스트
4. PR 생성까지 도와줘"
```

## /clear 타이밍

```
✅ Merge 완료 후 → /clear
✅ 다음 Issue 시작 전 → /clear
```

## 관련 항목
- [10-git-clear-after-merge.md](10-git-clear-after-merge.md)
