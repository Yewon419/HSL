# Git Best Practice #6: Push 전에 항상 리뷰하기

## 원칙

원격 저장소에 push하기 전에 `git diff`로 모든 변경사항을 리뷰하세요.

## 이유

- 실수로 추가된 코드 발견
- 디버그 코드, console.log 제거
- 민감한 정보 유출 방지
- 불필요한 변경 제거
- 코드 품질 최종 확인

## 실전 예시

### ❌ 리뷰 없이 바로 Push
```bash
git add .
git commit -m "fix bugs"
git push
# → 디버그 코드, API 키가 함께 push됨
```

### ✅ 리뷰 후 Push
```bash
# 변경사항 확인
git diff main

# 스테이징된 내용 확인
git diff --staged

# 문제 발견 시 수정
git reset HEAD debug_file.py
git checkout -- temp_test.js

# 최종 확인 후 push
git push
```

## 확인 체크리스트

```
[ ] console.log, print() 제거
[ ] TODO, FIXME 주석 확인
[ ] 주석 처리된 코드 제거
[ ] API 키, 비밀번호 없음
[ ] 테스트 파일 제외
[ ] 불필요한 공백 제거
[ ] 의도하지 않은 파일 제외
```

## 관련 항목
- [05-git-never-skip-hooks.md](05-git-never-skip-hooks.md)
- [07-git-commit-after-feature.md](07-git-commit-after-feature.md)
