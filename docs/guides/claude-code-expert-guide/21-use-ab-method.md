# Project Management #21: AB Method - 스펙 기반 워크플로우

## 원칙
큰 문제를 명세 기반의 집중적이고 점진적인 미션으로 변환하세요.

## AB Method 단계
1. **A단계**: 상세 스펙 작성
2. **B단계**: 스펙에 따라 구현
3. 서브에이전트로 검증
4. 반복

## 예시
```
[A] 스펙 작성: docs/auth-spec.md
  - API endpoints
  - Request/Response 형식
  - 인증 플로우
  - 오류 처리

[B] 구현: @docs/auth-spec.md 기반
  - Step 1: Models
  - Step 2: API
  - Step 3: Tests
```

## 장점
- 명확한 목표
- 검증 가능
- 반복 용이
