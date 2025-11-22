# Error Prevention #31: 테스트 먼저 작성하기 (TDD)

## 원칙

구현 전에 Claude에게 **테스트를 먼저** 작성하도록 요청하세요.

## 이유

- 명확한 목표 정의 (입력/출력 명세)
- 구현이 스펙을 정확히 따르는지 검증
- 리팩토링 안전성 확보
- Claude의 성능이 TDD에서 최고
- 버그 조기 발견

## TDD 사이클 with Claude

```
1. Red: 실패하는 테스트 작성
2. Green: 테스트를 통과하는 최소 코드 작성
3. Refactor: 코드 개선
```

## 실전 예시

### ❌ 테스트 없이 구현

```
사용자: "이메일 검증 함수를 만들어줘"

Claude:
def validate_email(email):
    return '@' in email

→ 버그 많음 (빈 문자열, 여러 @, 등)
→ 나중에 발견
→ 수정 어려움
```

### ✅ TDD 방식

```
사용자: "이메일 검증 함수의 테스트를 먼저 작성해줘. 구현은 하지 말고"

Claude:
import pytest

def test_validate_email_valid():
    assert validate_email("user@example.com") == True
    assert validate_email("name.surname@company.co.uk") == True

def test_validate_email_invalid():
    assert validate_email("invalid") == False
    assert validate_email("@example.com") == False
    assert validate_email("user@") == False
    assert validate_email("") == False
    assert validate_email("user@@example.com") == False

def test_validate_email_edge_cases():
    assert validate_email("user+tag@example.com") == True
    assert validate_email("user@subdomain.example.com") == True

사용자: "좋아, 이제 테스트를 실행해서 실패하는지 확인하고,
통과하는 구현을 작성해줘"

Claude:
# Run tests
pytest test_email.py
→ All tests FAILED (validate_email not defined)

# Implementation
import re

def validate_email(email):
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# Run tests again
pytest test_email.py
→ All tests PASSED ✓
```

## Claude에게 TDD 요청하는 방법

### 1. 명확한 스펙 제공

```
"사용자 등록 함수를 TDD로 구현해줘.

요구사항:
- username: 3-20자, 영숫자만
- email: 유효한 이메일 형식
- password: 최소 8자, 대소문자+숫자 포함
- 중복 사용자 거부

먼저 이 스펙을 검증하는 테스트를 작성하고,
실패하는 것을 확인한 후, 구현해줘"
```

### 2. 단계별 지시

```
"Step 1: 테스트 작성 (구현 코드는 작성하지 마)
Step 2: 테스트 실행해서 실패 확인
Step 3: 테스트를 통과하는 최소 구현 작성
Step 4: 테스트 실행해서 통과 확인
Step 5: 코드 리팩토링 (테스트는 계속 통과)"
```

### 3. 명시적 금지

```
"테스트를 먼저 작성해줘.
⚠️ 중요: 구현 코드는 아직 작성하지 마.
테스트만 작성하고 실패하는 것을 확인할 거야"
```

## 좋은 테스트 작성 원칙

### FIRST 원칙

- **Fast**: 빠르게 실행
- **Independent**: 독립적으로 실행 가능
- **Repeatable**: 반복 가능
- **Self-Validating**: 명확한 pass/fail
- **Timely**: 적시에 작성 (구현 전)

### AAA 패턴

```python
def test_user_creation():
    # Arrange (준비)
    username = "testuser"
    email = "test@example.com"

    # Act (실행)
    user = create_user(username, email)

    # Assert (검증)
    assert user.username == username
    assert user.email == email
    assert user.id is not None
```

## Edge Cases 포함

```
사용자: "결제 처리 함수의 테스트를 작성해줘.
엣지 케이스를 충분히 포함해줘"

Claude:
def test_payment_edge_cases():
    # 0원 결제
    assert process_payment(0) raises ValueError

    # 음수 금액
    assert process_payment(-100) raises ValueError

    # 매우 큰 금액
    assert process_payment(999999999) == Success

    # 소수점 (센트)
    assert process_payment(10.99) == Success

    # 통화 단위 경계
    assert process_payment(0.01) == Success

    # None/null
    assert process_payment(None) raises ValueError
```

## 테스트가 바뀌는 것 경계하기

⚠️ **주의**: Claude가 테스트를 수정해서 잘못된 구현에 맞추려고 할 수 있음

```
사용자: "⚠️ 중요: 테스트는 절대 수정하지 마.
구현이 테스트를 통과하도록 만들어야 해"
```

## 테스트 커버리지 확인

```
사용자: "pytest --cov=mymodule --cov-report=html 실행해서
커버리지를 확인해줘. 90% 이상이어야 해"
```

## TDD의 이점

1. **명확한 스펙**: 무엇을 만들어야 하는지 명확
2. **자신감**: 리팩토링 시 테스트가 보호
3. **문서화**: 테스트가 사용 예시
4. **디버깅 용이**: 실패 지점 명확
5. **설계 개선**: 테스트하기 쉬운 코드 = 좋은 설계

## 팁

- **작은 단위**: 한 번에 하나의 기능
- **실패 먼저 확인**: Red 단계 건너뛰지 말기
- **최소 구현**: Green 단계에서 과도한 구현 금지
- **리팩터링은 마지막**: 테스트 통과 후에만

## 관련 항목

- [32-verify-tests-fail-first.md](32-verify-tests-fail-first.md) - 테스트 실패 확인
- [33-review-test-quality.md](33-review-test-quality.md) - 테스트 품질 검토
- [84-tdd-best-for-claude.md](84-tdd-best-for-claude.md) - Claude의 TDD 강점
