# Project Management #24: 마크다운 체크리스트 활용

## 원칙
큰 작업은 마크다운 파일에 체크리스트로 만들어 진행 상황을 추적하세요.

## 예시
```markdown
# Migration Plan: REST to GraphQL

## Phase 1: Setup (Week 1)
- [x] GraphQL 서버 설정
- [x] Schema 정의
- [→] Resolver 기본 구조

## Phase 2: Migration (Week 2-3)
- [ ] User queries
- [ ] Product queries
- [ ] Order mutations
- [ ] Payment integration

## Phase 3: Testing (Week 4)
- [ ] Integration tests
- [ ] Performance tests
- [ ] Security audit
```

## 사용법
```
"@docs/migration-plan.md의 다음 항목을 진행해줘"
```

## 관련 항목
- [17-break-large-tasks.md](17-break-large-tasks.md)
