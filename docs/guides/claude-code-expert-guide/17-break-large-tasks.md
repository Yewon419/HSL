# Project Management #17: 큰 작업을 작은 단위로 나누기

## 원칙

작업이 너무 크면 Claude에게 프로젝트 계획으로 나누어 달라고 요청하세요.

## 이유

- 한 번에 소화 가능한 크기
- 진행 상황 추적 가능
- 리스크 감소
- 점진적 가치 전달

## 작업 크기 기준

```
너무 큼: "전자상거래 사이트 만들기" (수주)
적절함: "장바구니 API 구현" (수일)
이상적: "장바구니에 상품 추가 API" (수시간)
```

## 실전 예시

```
사용자: "전체 인증 시스템을 구현하려고 해. 너무 큰 것 같아"

Claude: "10개의 작은 태스크로 나누겠습니다:

## Phase 1: 기초 (Week 1)
1. User 모델 설계 및 마이그레이션 (2h)
2. Password hashing 유틸리티 (1h)
3. JWT 토큰 생성/검증 (2h)

## Phase 2: API (Week 1-2)
4. 회원가입 endpoint (3h)
5. 로그인 endpoint (2h)
6. 로그아웃 endpoint (1h)
7. 토큰 refresh endpoint (2h)

## Phase 3: 보안 (Week 2)
8. Rate limiting (2h)
9. 인증 middleware (2h)
10. 보안 테스트 (3h)

총 20시간, 2주 예상"

사용자: "좋아, Task 1부터 시작하자"
```

## 나누기 원칙

### 수평 분할 (기능별)
```
큰 기능 → 작은 기능들
예: "사용자 관리" →
  - 등록
  - 로그인
  - 프로필 수정
  - 비밀번호 재설정
```

### 수직 분할 (레이어별)
```
전체 스택 → 레이어별
예: "장바구니 기능" →
  - DB 스키마
  - API endpoint
  - Business logic
  - 프론트엔드
  - 테스트
```

## Markdown 체크리스트 활용

```
사용자: "이 계획을 docs/tasks.md로 저장해줘"

docs/tasks.md:
# Authentication Implementation

## Week 1
- [ ] User model & migration
- [ ] Password hashing
- [ ] JWT utilities
- [ ] Register endpoint
- [ ] Login endpoint

## Week 2
- [ ] Logout endpoint
- [ ] Token refresh
- [ ] Rate limiting
- [ ] Auth middleware
- [ ] Security tests
```

## 진행 추적

```
사용자: "@docs/tasks.md에서 완료한 항목을 체크해줘"

docs/tasks.md:
- [x] User model & migration ✅
- [x] Password hashing ✅
- [→] JWT utilities (진행중)
- [ ] Register endpoint
```

## 관련 항목
- [22-keep-diffs-small.md](22-keep-diffs-small.md)
- [24-markdown-checklist.md](24-markdown-checklist.md)
