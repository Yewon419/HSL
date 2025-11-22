# Error Prevention #39: 큰 변경 전 Checkpoint

## 원칙
위험한 작업 전에 checkpoint를 생성하여 상태를 캡처하세요.

## 자동 Checkpoint
Claude Code는 자동으로 checkpoint 생성하지만, 명시적으로 요청 가능:

```
사용자: "전체 인증 시스템을 리팩토링할 거야.
시작 전에 현재 상태를 저장해줘"

Claude:
1. git commit -m "wip: Before auth refactoring"
2. [Checkpoint 자동 생성됨]
3. 리팩토링 시작
```

## 되돌리기
```
# Checkpoint로 되돌리기
Esc Esc → Rewind 메뉴

# Git으로 되돌리기
git reset --hard HEAD
```

## 이중 안전
```
큰 변경 전:
1. Git commit (영구)
2. Checkpoint (빠른 복구)
```

## 관련 항목
- [04-git-checkpoints-vs-commits.md](04-git-checkpoints-vs-commits.md)
- [89-rewind-command.md](89-rewind-command.md)
