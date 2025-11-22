# Git Best Practice #7: 각 기능마다 커밋하기

## 원칙

완성된 각 기능을 별도의 커밋으로 분리하세요. 한 번에 큰 작업을 커밋하지 마세요.

## 이유

- 명확한 히스토리
- 쉬운 롤백
- 효과적인 코드 리뷰
- Cherry-pick 가능
- 버그 추적 용이

## 실전 예시

### ❌ 한 번에 모든 것
```bash
# 5개 기능을 하루 종일 작업
git add .
git commit -m "various updates"
# → 3000 lines 변경, 리뷰 불가능
```

### ✅ 기능별 커밋
```bash
# Feature 1
git add auth/login.py
git commit -m "feat(auth): Add login endpoint"

# Feature 2
git add auth/logout.py
git commit -m "feat(auth): Add logout endpoint"

# Feature 3
git add auth/middleware.py
git commit -m "feat(auth): Add authentication middleware"

# Feature 4
git add tests/test_auth.py
git commit -m "test(auth): Add auth integration tests"
```

## 좋은 커밋 크기

```
✅ 이상적: 50-200 lines
✅ 적절함: 200-500 lines
⚠️ 주의: 500-1000 lines
❌ 너무 큼: 1000+ lines
```

## 관련 항목
- [22-keep-diffs-small.md](22-keep-diffs-small.md)
- [69-small-changes-philosophy.md](69-small-changes-philosophy.md)
