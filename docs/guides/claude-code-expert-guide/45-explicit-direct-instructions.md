# Communication Patterns #45: 명시적이고 직접적인 지시

## 원칙

첫 시도에서 더 구체적인 지시를 할수록 Claude의 성공률이 크게 향상됩니다.

## 이유

- 모호함 제거
- 의도 명확화
- 재작업 감소
- 시간 절약
- 정확한 결과

## 실전 예시

### ❌ 모호한 지시

```
"이 코드를 개선해줘"
→ 무엇을? 어떻게? 왜?

"성능을 높여줘"
→ 어느 부분? 얼마나? 어떤 방법?

"버그를 고쳐줘"
→ 어떤 버그? 어떤 증상?
```

### ✅ 명시적이고 직접적인 지시

```
"사용자 등록 함수에 다음 검증을 추가해줘:
1. 이메일: 정규식으로 형식 검증
2. 비밀번호: 최소 8자, 대소문자+숫자 포함
3. 사용자명: 3-20자, 영숫자만 허용
4. 중복 이메일: 데이터베이스 체크
각 검증 실패 시 명확한 오류 메시지 반환"
```

```
"getUserById SQL 쿼리를 최적화해줘:
1. users 테이블의 id 컬럼에 인덱스 추가
2. SELECT *를 필요한 컬럼만 선택으로 변경
3. LEFT JOIN을 INNER JOIN으로 (user는 항상 존재)
4. 쿼리 결과 Redis에 5분간 캐싱
변경 전후 성능을 EXPLAIN으로 비교해줘"
```

## 구체성의 스펙트럼

```
레벨 1 (너무 모호): "고쳐줘"
레벨 2 (약간 나음): "로그인 버그 고쳐줘"
레벨 3 (좋음): "잘못된 비밀번호 입력 시 오류 메시지 안 나오는 버그 고쳐줘"
레벨 4 (매우 좋음): "login() 함수에서 bcrypt.compare() 실패 시
InvalidCredentials 예외를 발생시키지 않는 버그를 고쳐줘.
api/auth.py 라인 45 부근"
레벨 5 (완벽): "api/auth.py의 login() 함수 (line 45)에서
bcrypt.compare(password, user.password_hash)가 False를 반환할 때
InvalidCredentials 예외를 raise하지 않는 문제를 수정해줘.
현재는 None을 반환하고 있어서 클라이언트가 500 에러를 받음.
대신 401 Unauthorized와 함께 명확한 오류 메시지를 반환해야 함"
```

## 템플릿

### 기능 추가
```
"[파일명]의 [함수/클래스]에 [기능]을 추가해줘:
- 입력: [형식]
- 출력: [형식]
- 제약사항: [조건들]
- 오류 처리: [시나리오들]
- 테스트: [커버해야 할 케이스들]"
```

### 버그 수정
```
"[파일명]의 [위치]에서 발생하는 버그를 수정해줘:
- 증상: [문제 설명]
- 재현 방법: [단계들]
- 예상 동작: [올바른 동작]
- 현재 동작: [잘못된 동작]
- 오류 메시지: [있다면]"
```

### 리팩토링
```
"[파일명]의 [코드 부분]을 리팩토링해줘:
- 목표: [가독성/성능/유지보수성]
- 방법: [구체적 기법]
- 제약: [변경하면 안 되는 것]
- 검증: [동작 확인 방법]"
```

### 성능 최적화
```
"[기능]의 성능을 개선해줘:
- 현재 성능: [측정값]
- 목표 성능: [목표값]
- 병목: [알고 있다면]
- 방법: [선호하는 접근]
- 측정: [벤치마크 방법]"
```

## 비교: 모호함 vs 명시성

### 예시 1: 폼 검증

❌ **모호함**
```
"폼 검증을 추가해줘"
```

✅ **명시적**
```
"회원가입 폼 (components/RegisterForm.tsx)에 클라이언트 사이드 검증을 추가해줘:

필드별 규칙:
- email:
  - 형식: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  - 실시간 검증 (onChange)
  - 오류: "유효한 이메일 주소를 입력하세요"

- password:
  - 최소 8자
  - 대문자 1개 이상
  - 소문자 1개 이상
  - 숫자 1개 이상
  - 강도 표시기 표시 (약함/보통/강함)
  - 오류: 각 조건별 구체적 메시지

- confirmPassword:
  - password와 일치 여부
  - 실시간 검증
  - 오류: "비밀번호가 일치하지 않습니다"

- username:
  - 3-20자
  - 영숫자와 언더스코어만
  - 실시간 중복 체크 (debounce 500ms)
  - 오류: 각 조건별 메시지

검증 타이밍:
- onBlur: 필드 벗어날 때
- onChange: 타이핑 중 (debounce)
- onSubmit: 최종 검증

UI/UX:
- 검증 중: 로딩 스피너
- 성공: 녹색 체크마크
- 실패: 빨간색 X와 오류 메시지
- Submit 버튼: 모든 필드 valid일 때만 활성화"
```

### 예시 2: API 통합

❌ **모호함**
```
"결제 API를 통합해줘"
```

✅ **명시적**
```
"Stripe 결제 API를 백엔드에 통합해줘:

환경:
- Python 3.11, FastAPI
- stripe 라이브러리 사용
- 테스트 모드 (test API key)

구현할 엔드포인트:
1. POST /api/payments/create-intent
   - 입력: {amount: number, currency: string, customer_id: string}
   - Stripe PaymentIntent 생성
   - 출력: {client_secret: string, payment_intent_id: string}

2. POST /api/payments/confirm
   - 입력: {payment_intent_id: string}
   - PaymentIntent 상태 확인
   - 데이터베이스에 결제 기록 저장
   - 출력: {status: string, receipt_url: string}

3. POST /api/webhooks/stripe
   - Stripe webhook 이벤트 처리
   - 서명 검증 필수
   - 이벤트: payment_intent.succeeded, payment_intent.failed
   - 비동기 처리 (Celery task)

오류 처리:
- Stripe API 오류: 클라이언트에 명확한 메시지 전달
- 네트워크 오류: 재시도 로직 (최대 3회)
- Webhook 서명 실패: 400 반환, 로그 기록

보안:
- API key는 환경변수에서만
- Webhook 서명 검증 필수
- HTTPS only (프로덕션)
- Rate limiting: 분당 100 요청

테스트:
- 단위 테스트: 각 함수
- 통합 테스트: 실제 Stripe test API 사용
- Webhook 테스트: stripe CLI로 로컬 테스트

문서화:
- OpenAPI schema 업데이트
- README에 설정 방법 추가
- .env.example 업데이트"
```

## 명시성 체크리스트

지시를 내리기 전에 확인:

```
[ ] 무엇을 해야 하는지 명확한가?
[ ] 어디서 해야 하는지 명시되었는가?
[ ] 어떻게 해야 하는지 구체적인가?
[ ] 왜 필요한지 설명되었는가?
[ ] 성공 기준이 정의되었는가?
[ ] 제약사항이 명시되었는가?
[ ] 예외 상황이 다뤄졌는가?
[ ] 검증 방법이 제시되었는가?
```

## 점진적 구체화

처음부터 완벽할 필요는 없습니다. 대화를 통해 구체화:

```
사용자: "로그인 기능을 추가해줘"

Claude: "로그인 기능을 추가하겠습니다. 몇 가지 확인하고 싶습니다:
1. 인증 방식: JWT, Session, OAuth?
2. 로그인 필드: 이메일/비밀번호, 사용자명/비밀번호?
3. 추가 기능: Remember me, 비밀번호 찾기?
4. 보안: 2FA, Rate limiting?"

사용자: "JWT 사용하고, 이메일/비밀번호로 로그인.
Remember me와 rate limiting 필요해"

Claude: "알겠습니다. 다음과 같이 진행하겠습니다:
[구체적인 계획]"
```

## 효과 측정

### Before (모호한 지시)
- 첫 시도 성공률: 40%
- 평균 재작업: 2-3회
- 완료 시간: 2시간

### After (명시적 지시)
- 첫 시도 성공률: 85%
- 평균 재작업: 0-1회
- 완료 시간: 30분

## 팁

1. **예시 제공**: "이런 형식으로..."
2. **반례 제공**: "이렇게 하지 마..."
3. **우선순위**: "가장 중요한 것은..."
4. **제약사항**: "절대 하지 말아야 할 것..."
5. **검증 방법**: "이렇게 확인..."

## 관련 항목

- [18-be-specific-not-vague.md](18-be-specific-not-vague.md) - 구체적 요청
- [20-define-success-criteria.md](20-define-success-criteria.md) - 성공 기준
- [16-ask-for-plan-first.md](16-ask-for-plan-first.md) - 계획 우선
