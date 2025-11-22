# Error Prevention #30: 복잡한 변경 시 Plan Mode 사용

## 원칙

복잡하거나 큰 변경 작업 전에 **Plan Mode**를 사용하여 코드 수정 없이 분석하고 계획을 세우세요.

## Plan Mode란?

- **Shift+Tab 두 번** 눌러 활성화
- 읽기 전용 모드 (파일 수정 안 함)
- 아키텍처 분석 및 계획 수립에 집중
- 코드를 이해하고 접근 방식을 결정

## 언제 사용할까?

### 1. 대규모 리팩토링
```
사용자: [Shift+Tab x2]
"전체 인증 시스템을 JWT에서 OAuth2로 마이그레이션하려고 해.
영향을 받는 파일과 단계별 계획을 알려줘"
```

### 2. 레거시 코드 이해
```
사용자: [Shift+Tab x2]
"이 10년 된 코드베이스에서 결제 처리 흐름을 분석해줘.
어떤 파일들이 관여하고 있고, 어떻게 개선할 수 있을까?"
```

### 3. 새로운 기능 설계
```
사용자: [Shift+Tab x2]
"실시간 채팅 기능을 추가하려고 해.
현재 아키텍처와 잘 맞는 구현 방식을 제안해줘"
```

### 4. 버그 원인 분석
```
사용자: [Shift+Tab x2]
"프로덕션에서 메모리 누수가 발생하고 있어.
코드를 분석해서 가능한 원인들을 찾아줘"
```

## 실전 예시

### Before: 계획 없이 시작

```
사용자: "마이크로서비스 아키텍처로 전환해줘"
Claude: [모놀리스 코드를 막 수정하기 시작]
→ 중간에 의존성 문제 발견
→ 접근 방식 변경 필요
→ 이미 변경한 코드 되돌려야 함
```

### After: Plan Mode 사용

```
사용자: [Shift+Tab x2]
"현재 모놀리스 애플리케이션을 마이크로서비스로 전환하고 싶어.
먼저 분석해줘"

Claude (Plan Mode):
## 현재 아키텍처 분석

### 주요 도메인
1. User Management (app/users/)
2. Product Catalog (app/products/)
3. Order Processing (app/orders/)
4. Payment (app/payments/)

### 의존성 관계
- Orders → Users (인증)
- Orders → Products (재고)
- Orders → Payments (결제)

### 제안 마이그레이션 전략

**Phase 1**: Payment 서비스 분리
- 가장 독립적
- API 경계 명확
- 롤백 용이

**Phase 2**: Product Catalog 분리
- Orders와의 인터페이스 정의 필요
- 이벤트 기반 재고 업데이트

**Phase 3**: User Management 분리
- 인증/인가 중앙화 필요

**Phase 4**: Order Processing 분리
- 마지막 (다른 서비스 의존)

각 단계에 3-4주 소요 예상.

사용자: "좋아, Phase 1의 상세 구현 계획을 세워줘"
[Plan Mode 종료, 일반 모드로 구현 시작]
```

## Plan Mode의 장점

1. **안전함**: 파일을 수정하지 않음
2. **빠른 반복**: 여러 접근 방식을 빠르게 탐색
3. **완전한 분석**: 전체 코드베이스 이해
4. **비용 효율적**: 실수로 인한 재작업 방지

## Plan Mode 활용 패턴

### Pattern 1: Analyze → Plan → Exit → Implement

```
1. [Shift+Tab x2] Plan Mode 진입
2. 문제 분석 및 계획 수립
3. 계획을 파일로 저장 요청
4. Plan Mode 종료
5. 계획 파일 참조하며 구현
```

### Pattern 2: Multiple Approaches

```
사용자: [Plan Mode]
"이 문제를 해결하는 3가지 다른 방법을 제안해줘.
각각의 장단점을 비교해줘"

Claude:
## Approach 1: Redis Cache
장점: 빠름, 구현 쉬움
단점: 메모리 사용, 일관성 이슈

## Approach 2: Database Index
장점: 데이터 일관성, 영구 보존
단점: 초기 구축 비용

## Approach 3: Materialized View
장점: 쿼리 성능 최고
단점: 복잡한 갱신 로직

사용자: "Approach 2로 가자"
```

### Pattern 3: Impact Analysis

```
사용자: [Plan Mode]
"이 API 엔드포인트를 변경하면 어떤 영향이 있을까?
모든 의존하는 코드를 찾아줘"

Claude:
영향 받는 부분:
1. Frontend: 3개 컴포넌트
2. Mobile App: 2개 화면
3. 내부 서비스: CronJob 1개
4. 테스트: 12개 테스트 케이스

마이그레이션 계획:
...
```

## Plan Mode + Other Tools

### Ultrathink + Plan Mode

```
사용자: "ultrathink [Shift+Tab x2]
이 복잡한 동시성 문제를 분석하고
안전한 해결 방법을 제안해줘"
```

### Plan Mode → Markdown → Slash Command

```
1. [Plan Mode] 계획 수립
2. docs/implementation-plan.md에 저장
3. /clear로 컨텍스트 정리
4. @docs/implementation-plan.md 참조하며 구현
```

## 팁

- **복잡할 때 항상 사용**: "이거 복잡한데?" → Plan Mode
- **시간 절약**: 5분 계획으로 2시간 재작업 방지
- **Escape로 중단 가능**: 언제든 Plan Mode 나갈 수 있음
- **계획 저장**: 중요한 계획은 마크다운 파일로 저장

## 관련 항목

- [16-ask-for-plan-first.md](16-ask-for-plan-first.md) - 계획 먼저 요청하기
- [130-plan-mode.md](130-plan-mode.md) - Plan Mode 상세 가이드
- [132-ultrathink-plan-mode.md](132-ultrathink-plan-mode.md) - 고급 조합 기법
