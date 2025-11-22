# Project Management #19: 초반에 충분한 컨텍스트 제공

## 원칙
프레임워크, 코딩 스타일, 제약사항을 CLAUDE.md에 명시하세요.

## 컨텍스트 포함 사항
```markdown
# CLAUDE.md

## Tech Stack
- Python 3.11, FastAPI, PostgreSQL

## Code Style
- Type hints 필수
- Google docstring
- Max line length: 100

## Constraints
- No external API calls in tests
- All dates in UTC
- Database transactions required
```

## 효과
- 반복 설명 불필요
- 일관된 코드 생성
- 시간 절약

## 관련 항목
- [97-claude-md-best-practices.md](97-claude-md-best-practices.md)
