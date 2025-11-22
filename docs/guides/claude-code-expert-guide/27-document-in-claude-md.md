# Project Management #27: CLAUDE.md에 결정사항 문서화

## 원칙
프로젝트 관례, 결정사항, 세션 간 지속되는 컨텍스트를 CLAUDE.md에 보관하세요.

## 문서화할 내용
```markdown
# CLAUDE.md

## Architectural Decisions
- 2024-01-15: Redis를 세션 스토리지로 선택
  이유: 성능, TTL 지원

## Conventions
- API 버전: /api/v1/
- 날짜 형식: ISO 8601
- 오류 응답: {error, message, code}

## Gotchas
- PostgreSQL jsonb 필드는 null 체크 필수
- Celery task는 항상 idempotent하게
```

## 업데이트
```
"# CLAUDE.md에 Redis를 캐시로 사용한다고 추가해줘"
```

## 관련 항목
- [97-claude-md-best-practices.md](97-claude-md-best-practices.md)
- [100-hash-shortcut.md](100-hash-shortcut.md)
