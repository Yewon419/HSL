# Git Best Practice #8: Cherry-pick으로 Hotfix 관리

## 원칙

긴급 버그 수정 시 작은 diff를 만들고, 안전성을 확인한 후 cherry-pick으로 hotfix 브랜치에 적용하세요.

## 워크플로우

```bash
# 1. develop에서 버그 수정
git checkout develop
git checkout -b fix/critical-bug

# 2. 최소한의 수정
# [작은 diff 생성]

# 3. 테스트
pytest tests/

# 4. 커밋
git commit -m "fix: critical security issue"

# 5. main/hotfix 브랜치로 cherry-pick
git checkout main
git cherry-pick <commit-hash>

# 6. 배포
git tag v1.2.1
git push --tags
```

## Claude에게 요청하는 방법

```
"이 버그를 수정하는 최소한의 diff를 만들어줘.
- 50 lines 이하
- 테스트 포함
- 왜 안전한지 설명
그리고 hotfix 브랜치에 cherry-pick 할 수 있게"
```

## 안전성 확인

```
[ ] Diff가 50 lines 이하
[ ] 단일 목적 (버그 수정만)
[ ] 테스트 통과
[ ] 부작용 없음
[ ] 리뷰 완료
```

## 관련 항목
- [07-git-commit-after-feature.md](07-git-commit-after-feature.md)
