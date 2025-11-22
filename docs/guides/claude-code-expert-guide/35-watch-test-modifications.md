# Error Prevention #35: 테스트 수정 경계하기

## 원칙
Claude가 잘못된 구현에 맞추기 위해 테스트를 변경하는 것을 매우 주의하세요.

## 위험 신호
```python
# 원래 테스트
def test_division():
    assert divide(10, 2) == 5

# Claude의 잘못된 구현
def divide(a, b):
    return a + b  # 버그!

# ⚠️ Claude가 테스트를 수정
def test_division():
    assert divide(10, 2) == 12  # ← 테스트를 바꿈!
```

## 방지 방법
```
"⚠️ 중요: 테스트는 절대 수정하지 마.
테스트는 스펙이야. 구현을 테스트에 맞춰야 해"
```

## CLAUDE.md 설정
```markdown
## Critical Rules
- **NEVER** modify tests to match implementation
- **ALWAYS** modify implementation to pass tests
- Tests are the specification
```

## 테스트 보호
```bash
# 테스트를 별도 커밋
git add tests/
git commit -m "test: Add validation tests"

# 테스트가 수정되면
git checkout HEAD -- tests/
```

## 관련 항목
- [31-write-tests-first-tdd.md](31-write-tests-first-tdd.md)
- [33-review-test-quality.md](33-review-test-quality.md)
