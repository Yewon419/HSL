# Context Management #97: CLAUDE.md 작성 모범 사례

## 원칙

계층적 CLAUDE.md 파일을 사용하여 프로젝트별, 디렉토리별 컨텍스트를 제공하세요.

## CLAUDE.md란?

- 프로젝트 루트나 하위 디렉토리에 위치
- Claude에게 프로젝트 정보 제공
- 세션 간 지속되는 메모리
- 자동으로 모든 세션에 포함

## 파일 위치와 우선순위

```
my-project/
├── CLAUDE.md              # 프로젝트 전체 컨텍스트
├── backend/
│   └── CLAUDE.md          # 백엔드 특화 컨텍스트 (상위 파일 오버라이드)
└── frontend/
    └── CLAUDE.md          # 프론트엔드 특화 컨텍스트
```

**우선순위**: 더 구체적인 파일이 상위 파일을 오버라이드

## 구조 템플릿

```markdown
# Project Name

## Tech Stack
- Language: Python 3.11
- Framework: FastAPI
- Database: PostgreSQL 15
- ORM: SQLAlchemy 2.0
- Testing: pytest

## Project Structure
```
src/
├── api/          # REST API endpoints
├── models/       # Database models
├── services/     # Business logic
└── utils/        # Helper functions
```

## Development Commands
- Run: `uvicorn main:app --reload`
- Test: `pytest tests/ -v`
- Lint: `ruff check .`
- Format: `black .`
- Type check: `mypy .`

## Code Style
- Use type hints everywhere
- Follow PEP 8
- Max line length: 100
- Use async/await for I/O operations
- Docstrings: Google style

## Important Patterns
### Error Handling
Always use custom exceptions from `exceptions.py`:
```python
from exceptions import ResourceNotFound, ValidationError

def get_user(id: int) -> User:
    user = db.query(User).get(id)
    if not user:
        raise ResourceNotFound(f"User {id} not found")
    return user
```

### Database Transactions
Always use context manager:
```python
async with db.transaction():
    user = await create_user(data)
    await send_welcome_email(user)
```

## Anti-Patterns
❌ Don't use `SELECT *`
❌ Don't commit directly to main
❌ Don't skip migrations
❌ Don't use print() for logging (use logger)

## Git Workflow
- Branch naming: `feature/`, `fix/`, `refactor/`
- Commit format: Conventional Commits
- Always run tests before commit
- Never use `--no-verify`

## Testing Guidelines
- Minimum 80% coverage
- Use fixtures from `conftest.py`
- Mock external services
- Test both success and error cases

## Forbidden Directories
Do not read or modify:
- `node_modules/`
- `venv/`
- `.git/`
- `__pycache__/`
- `*.pyc`

## Environment
- Dev: Uses `.env.dev`
- Prod: Uses environment variables
- Required vars: DATABASE_URL, SECRET_KEY, API_KEY

## Notes
- User authentication uses JWT
- All datetimes are UTC
- API uses snake_case
- Frontend expects camelCase
```

## 크기 제한

**5,000 토큰 이하 유지**

❌ 너무 큼:
```markdown
# 전체 API 문서 복사
# 모든 함수 시그니처 나열
# 전체 의존성 목록
# ...10,000 토큰
```

✅ 적절함:
```markdown
# 핵심 패턴과 규칙만
# "자세한 내용은 docs/api.md 참조"
# ...3,000 토큰
```

## 유기적 성장: # 단축키

작업 중 자연스럽게 업데이트:

```
사용자: "# 앞으로 logging에는 structlog를 사용한다고 추가해줘"

Claude: [CLAUDE.md에 자동 추가]
```

## 카테고리별 예시

### 백엔드 (backend/CLAUDE.md)

```markdown
# Backend

## API Design
- RESTful endpoints
- Versioning: `/api/v1/`
- Response format: `{data, error, meta}`

## Database
- Migrations: Alembic
- Always use indexes for foreign keys
- Soft delete pattern for user data

## Authentication
- JWT in Authorization header
- Refresh token in httpOnly cookie
- Token expiry: 1h (access), 7d (refresh)
```

### 프론트엔드 (frontend/CLAUDE.md)

```markdown
# Frontend

## Framework
- React 18 + TypeScript
- State: Zustand
- Routing: React Router v6
- Styling: TailwindCSS

## Component Patterns
- Use function components only
- Custom hooks in `hooks/`
- Shared components in `components/common/`

## API Integration
- Use `api/client.ts` wrapper
- All API calls go through React Query
- Error handling with ErrorBoundary
```

## 계층적 컨텍스트 예시

```
프로젝트 루트 CLAUDE.md:
"전체 프로젝트는 마이크로서비스 아키텍처"

services/payment/CLAUDE.md:
"결제 서비스는 Stripe SDK 사용
민감한 데이터는 절대 로그에 기록 금지"

services/auth/CLAUDE.md:
"인증 서비스는 OAuth2 + JWT
보안이 최우선, 모든 변경은 보안 리뷰 필수"
```

## 무엇을 포함할까?

### ✅ 포함해야 할 것

- 기술 스택과 버전
- 빌드/실행 명령어
- 코드 스타일 규칙
- 중요한 패턴과 관례
- 안티패턴과 주의사항
- 프로젝트별 특이사항
- 도메인 지식

### ❌ 포함하지 말아야 할 것

- 전체 API 문서 (→ 별도 파일로 참조)
- 상세한 구현 코드 (→ 코드베이스 참조)
- 자주 변경되는 정보 (→ 다른 파일로)
- 일반적인 프로그래밍 지식
- 너무 자세한 설정 (→ README.md로)

## 업데이트 시점

다음 경우에 CLAUDE.md 업데이트:

1. **새로운 패턴 도입**
   ```
   "# Redux를 Zustand로 교체했다고 업데이트해줘"
   ```

2. **중요한 결정**
   ```
   "# 이제 모든 날짜는 ISO 8601 형식으로 반환한다고 추가해줘"
   ```

3. **안티패턴 발견**
   ```
   "# useState의 객체를 직접 수정하지 말고 새 객체 생성이라고 추가해줘"
   ```

4. **도구 변경**
   ```
   "# Jest를 Vitest로 마이그레이션했다고 업데이트해줘"
   ```

## 팁

### 1. 반복 줄이기

❌ Before:
```
"PostgreSQL 사용하고, SQLAlchemy로 ORM하고,
Alembic으로 마이그레이션하고..."
```

✅ After (CLAUDE.md에 한 번만):
```markdown
## Database Stack
PostgreSQL + SQLAlchemy + Alembic
```

### 2. 참조 활용

```markdown
## Documentation
- API: @docs/api.md
- Architecture: @docs/architecture.md
- Deployment: @docs/deploy.md
```

### 3. 도메인 지식

```markdown
## Business Logic
- Subscription billing cycle: Monthly on signup date
- Trial period: 14 days
- Cancellation: Immediate, refund prorated amount
- Upgrades: Immediate, downgrade at period end
```

### 4. 팀 컨벤션

```markdown
## Team Conventions
- PR requires 2 approvals
- Commit to main only via PR
- Breaking changes need RFC
- Deploy window: Weekdays 10am-4pm UTC
```

## 예시: 완성된 CLAUDE.md

```markdown
# Stock Trading System

## Tech Stack
- Backend: Python 3.11 + FastAPI
- Database: PostgreSQL 15 + TimescaleDB
- Frontend: Vanilla JS + Bootstrap 5
- Cache: Redis
- Message Queue: RabbitMQ

## Architecture
Microservices with shared PostgreSQL database.
Services: `user_service`, `stock_service`, `trading_service`

## Commands
- Start: `docker-compose up -d`
- Test: `pytest backend/tests/ -v`
- Lint: `ruff check backend/`
- Format: `black backend/`

## Code Style
- Type hints required
- Async for all I/O
- Max line length: 100
- Docstrings: Google style

## Important Patterns
### API Response Format
```python
{
    "data": {...},
    "error": null,
    "meta": {"timestamp": "..."}
}
```

### Error Handling
Use custom exceptions from `exceptions.py`

### Database Access
Always use service layer, never direct DB access from routes

## Git Workflow
- Feature branches from `develop`
- Conventional commits
- Squash merge to `develop`
- Never commit secrets

## Testing
- Minimum 80% coverage
- Integration tests for all APIs
- Use fixtures in `conftest.py`

## Forbidden
- Never modify `migrations/` manually
- Never commit `.env` files
- Never use `print()` (use `logger`)
- Never skip pre-commit hooks

## Domain Knowledge
- Stock prices updated every 5 minutes during market hours
- Technical indicators calculated nightly
- User timezone stored in profile, display in local time
- Historical data retention: 5 years

## Security
- All passwords hashed with bcrypt
- JWT expiry: 1 hour
- API rate limit: 100 req/min
- Sensitive data encrypted at rest

---
Last updated: 2025-01-15
```

## 관련 항목

- [98-hierarchical-claude-md.md](98-hierarchical-claude-md.md) - 계층적 구조
- [99-claude-md-under-5k.md](99-claude-md-under-5k.md) - 토큰 제한 관리
- [100-hash-shortcut.md](100-hash-shortcut.md) - # 단축키 활용
