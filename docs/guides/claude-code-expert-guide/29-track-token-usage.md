# Project Management #29: 토큰 사용량 추적

## 원칙
토큰 소비를 모니터링하여 사용 한도 내에 머물고 워크플로우를 조정하세요.

## 토큰 절약 방법
```
1. /clear 자주 사용
2. CLAUDE.md를 5000 토큰 이하로
3. 큰 파일은 별도 문서로 참조
4. 불필요한 파일 읽기 방지
```

## 확인 방법
- Claude Code는 자동으로 표시
- 50% 도달 시 /clear 고려
- 80% 도달 시 반드시 /clear

## 최적화
```markdown
# CLAUDE.md

## Forbidden Directories
- node_modules/
- venv/
- .git/
- dist/
- build/
```

## 관련 항목
- [103-clear-frequently.md](103-clear-frequently.md)
- [99-claude-md-under-5k.md](99-claude-md-under-5k.md)
