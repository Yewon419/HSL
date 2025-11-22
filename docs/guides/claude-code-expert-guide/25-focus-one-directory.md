# Project Management #25: 한 번에 한 디렉토리에 집중

## 원칙
대형 프로젝트 작업 시 특정 디렉토리에 집중하세요.

## 예시
```
"backend/auth/ 디렉토리의 인증 로직만 리팩토링해줘.
다른 디렉토리는 건드리지 마"
```

## CLAUDE.md 활용
```
backend/auth/CLAUDE.md:
# Auth Service

## Scope
Only files in backend/auth/

## Dependencies
- backend/models/user.py (read-only)
- backend/utils/crypto.py (read-only)
```

## 장점
- 집중력 향상
- 부작용 감소
- 리뷰 용이
