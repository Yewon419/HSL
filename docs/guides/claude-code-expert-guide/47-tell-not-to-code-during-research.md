# Communication Patterns #47: 조사 단계에서 코딩 금지 명시

## 원칙

계획/조사 단계에서 Claude에게 "아직 코드를 작성하지 마"라고 명시적으로 지시하세요.

## 이유

- 잘못된 방향으로 구현 방지
- 계획 먼저, 구현은 나중에
- 재작업 방지
- 승인 기회 제공

## 실전 예시

### ❌ 명시하지 않음

```
사용자: "GraphQL을 REST API에 추가하는 방법을 알려줘"

Claude: [바로 코드 작성 시작]
import { GraphQLSchema, GraphQLObjectType } from 'graphql';

const schema = new GraphQLSchema({...});
// ...
→ 계획 없이 구현 시작
→ 사용자가 원한 건 설명이었는데...
```

### ✅ 명시적 금지

```
사용자: "GraphQL을 우리 REST API에 추가하는 방법을 조사해줘.
⚠️ 중요: 아직 코드를 작성하지 마. 먼저 어떻게 할지 계획만 설명해줘"

Claude: "GraphQL 통합 방법을 조사하겠습니다.

## 현재 아키텍처 분석
- REST API: FastAPI (Python)
- 데이터베이스: PostgreSQL
- 인증: JWT

## GraphQL 통합 옵션

### Option 1: Strawberry (추천)
장점:
- FastAPI와 네이티브 통합
- Type hints 지원
- 현대적 API

단점:
- 커뮤니티 작음

### Option 2: Graphene
장점:
- 성숙한 라이브러리
- 큰 커뮤니티

단점:
- FastAPI 통합이 덜 자연스러움

## 추천 접근 방식
1. Strawberry GraphQL 사용
2. 기존 REST와 병행 (/graphql endpoint)
3. 단계적 마이그레이션

어떤 옵션으로 진행할까요?"

사용자: "Option 1으로 가자. 이제 구현해줘"
```

## 명시적 금지 문구

### 강력함
```
"⚠️ 절대 코드를 작성하지 마"
"⚠️ 구현하지 말고 조사만"
"⚠️ 코딩은 아직 하지 마"
```

### 정중함
```
"아직 코드는 작성하지 말아줘"
"먼저 계획만 보여줘"
"구현 전에 승인받고 싶어"
```

### 명확함
```
"코드를 작성하지 말고, 어떻게 할지만 설명해줘"
"Read-only 모드로 분석만 해줘"
"Plan Mode로 접근 방법만 제안해줘"
```

## 단계별 워크플로우

### Phase 1: 조사 (코드 X)
```
사용자: "캐싱 레이어를 추가하는 방법을 조사해줘.
⚠️ 코드는 작성하지 마"

Claude:
## 캐싱 옵션 분석
1. Redis
2. Memcached
3. In-memory (functools.lru_cache)

각 옵션의 장단점:
[상세 분석]

추천: Redis
이유: [설명]
```

### Phase 2: 계획 (코드 X)
```
사용자: "좋아, Redis로 가자. 구현 계획을 세워줘.
⚠️ 아직 구현은 하지 마"

Claude:
## Redis 캐싱 구현 계획

Step 1: 환경 설정
- docker-compose에 Redis 추가
- redis-py 설치

Step 2: 캐시 유틸리티
- cache decorator 작성
- TTL 설정

Step 3: API 통합
- 조회 API에 적용
- 캐시 무효화 로직

각 단계 약 2시간 예상
```

### Phase 3: 승인
```
사용자: "계획 좋아. Step 1부터 구현 시작해줘"
```

### Phase 4: 구현 (코드 O)
```
Claude: [이제 코드 작성 시작]
```

## Plan Mode와 함께 사용

```
사용자: [Shift+Tab x2로 Plan Mode 진입]

"전체 프론트엔드를 React에서 Vue로 마이그레이션하는 방법을 분석해줘"

Claude: [Plan Mode - 코드 수정 없이 분석만]
```

## CLAUDE.md 설정

```markdown
## Working Phases

### Phase 1: Research/Planning
- NO code changes
- Analysis only
- Propose approaches
- Wait for approval

### Phase 2: Implementation
- Code changes allowed
- Follow approved plan
- Small incremental changes

I will ALWAYS ask "Should I start implementing?" before writing code.
```

## 신호어

Claude가 코드 작성을 시작하려는 신호:

```
"이제 구현하겠습니다..."
"코드를 작성하겠습니다..."
"파일을 수정하겠습니다..."

→ 이때 멈추고 "잠깐, 계획만 보여줘"
```

## 예방적 지시

세션 시작 시:

```
사용자: "오늘 우리는 인증 시스템을 개선할 거야.
기본 규칙: 모든 구현 전에 계획을 먼저 보여주고 승인을 받아"

Claude: "알겠습니다. 구현 전에 항상 계획을 제시하고 승인을 기다리겠습니다."
```

## 실수 방지

### Claude가 코드를 작성했다면

```
사용자: "잠깐! 아직 코드 작성 말라고 했는데?
/rewind로 되돌리고, 계획만 보여줘"

Claude: "죄송합니다. 되돌리고 계획만 제시하겠습니다."
```

## 장점

1. **통제**: 구현 방향 제어
2. **학습**: 왜 그렇게 하는지 이해
3. **승인**: 잘못된 방향 조기 발견
4. **재작업 방지**: 계획 검토로 시간 절약

## 언제 사용?

```
✅ 새로운 기술 도입 시
✅ 대규모 리팩토링
✅ 아키텍처 변경
✅ 불확실한 요구사항
✅ 여러 옵션 검토 필요

❌ 간단한 버그 수정
❌ 명확한 작은 기능
❌ 반복적인 작업
```

## 관련 항목

- [30-plan-mode-for-complex-changes.md](30-plan-mode-for-complex-changes.md) - Plan Mode
- [16-ask-for-plan-first.md](16-ask-for-plan-first.md) - 계획 우선
- [45-explicit-direct-instructions.md](45-explicit-direct-instructions.md) - 명시적 지시
