# Project Management #22: Diff를 200 lines 이하로 유지

## 원칙

각 단계의 diff를 200 lines 이하로 제한하세요.

## 이유

- 리뷰 가능
- 이해 가능
- 테스트 가능
- 롤백 안전

## 크기 가이드

```
✅ 50-200 lines: 이상적
⚠️ 200-500 lines: 가능하지만 나누는 것 권장
❌ 500+ lines: 너무 큼, 반드시 나눠야 함
```

## 실전 예시

### ❌ 큰 Diff
```
사용자: "사용자 인증 전체를 구현해줘"

Claude: [1500 lines 변경]
- models.py: 200 lines
- api/auth.py: 400 lines
- middleware.py: 150 lines
- utils/crypto.py: 100 lines
- tests/: 650 lines

→ 리뷰 불가능
→ 어디서 버그인지 모름
```

### ✅ 작은 Diffs

```
사용자: "사용자 인증을 5단계로 나눠서 구현해줘. 각 단계는 200 lines 이하"

Step 1 (~80 lines):
- models.py: User 모델만

Step 2 (~120 lines):
- utils/crypto.py: Password hashing
- tests/test_crypto.py

Step 3 (~180 lines):
- utils/jwt.py: JWT 생성/검증
- tests/test_jwt.py

Step 4 (~150 lines):
- api/auth.py: 회원가입 endpoint
- tests/test_register.py

Step 5 (~140 lines):
- api/auth.py: 로그인 endpoint
- tests/test_login.py
```

## Diff 크기 확인

```bash
# 현재 변경사항 라인 수
git diff --stat

# 스테이징된 변경사항
git diff --cached --stat

# 예:
# models.py | 45 ++++++++++++
# api/auth.py | 120 ++++++++++++++++++++
# tests/test.py | 80 +++++++++++++
# 3 files changed, 245 insertions(+)
```

## Claude에게 요청

```
"이 기능을 구현해줘.
단, 각 단계는 200 lines 이하로 제한하고,
각 단계마다 내게 diff 크기를 보고해줘"
```

## 너무 커지면

```
사용자: "이 diff가 500 lines인데, 200 lines 2개로 나눠줘"

Claude:
Step 1 (180 lines): 핵심 로직
Step 2 (150 lines): 테스트
Step 3 (170 lines): 에러 처리 및 검증
```

## 관련 항목
- [69-small-changes-philosophy.md](69-small-changes-philosophy.md)
- [17-break-large-tasks.md](17-break-large-tasks.md)
