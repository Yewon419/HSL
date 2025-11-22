# Git Best Practice #10: Merge 후 /clear 사용하기

## 원칙

각 merge 완료 후 `/clear`로 Claude의 컨텍스트를 정리하여 모든 이슈를 독립적으로 유지하세요.

## 이유

- 이전 작업의 컨텍스트 오염 방지
- 토큰 사용 최적화
- 각 작업에 집중
- Git history와 scratchpad가 외부 메모리 역할

## 워크플로우

```
Issue #1 작업
→ Merge
→ /clear ✨
→ Issue #2 시작 (@CLAUDE.md 참조)
→ Merge
→ /clear ✨
→ Issue #3 시작
```

## 실전 예시

```
# Issue #42 완료
사용자: "PR이 merge되었어"

Claude: [축하 메시지]

사용자: "/clear"

# 새 작업 시작
사용자: "Issue #43을 시작할 거야. @CLAUDE.md를 참조해서
이전 작업 내용은 git log에서 확인할 수 있어"
```

## /clear의 장점

- **신선한 시작**: 이전 컨텍스트 방해 없음
- **토큰 절약**: 불필요한 히스토리 제거
- **명확한 경계**: 각 이슈가 독립적
- **성능 향상**: 컨텍스트 윈도우 최적화

## 언제 /clear 할까?

```
✅ PR merge 후
✅ 큰 기능 완료 후
✅ 디버깅 세션 종료 후
✅ 다른 프로젝트로 전환 시
✅ 컨텍스트가 혼란스러울 때
```

## 관련 항목
- [09-git-github-flow.md](09-git-github-flow.md)
- [103-clear-frequently.md](103-clear-frequently.md)
