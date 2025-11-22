# Project Management #26: 커스텀 Slash 명령어 생성

## 원칙
반복되는 워크플로우를 `.claude/commands/`에 마크다운 파일로 저장하세요.

## 생성 방법
```bash
mkdir -p .claude/commands
```

```markdown
<!-- .claude/commands/test.md -->
Run all tests and show coverage:

1. pytest tests/ -v --cov=src --cov-report=term
2. Show failed tests
3. Suggest fixes if any failures
```

## 사용
```
/test
```

## 유용한 명령어 예시
- `/deploy` - 배포 체크리스트
- `/review` - 코드 리뷰 수행
- `/security` - 보안 검사
- `/docs` - 문서 업데이트

## 관련 항목
- [97-claude-md-best-practices.md](97-claude-md-best-practices.md)
