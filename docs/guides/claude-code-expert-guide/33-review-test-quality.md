# Error Prevention #33: 테스트 품질 철저히 검토

## 원칙
생성된 테스트를 평소보다 더 많은 시간을 들여 검토하세요. 잘못된 테스트는 데스 스파이럴을 유발합니다.

## 나쁜 테스트의 징후
```python
# ❌ 너무 광범위
def test_everything():
    assert system.works() == True

# ❌ 의미 없음
def test_add():
    assert 2 + 2 == 4  # 우리 코드 테스트 아님

# ❌ 구현에 의존
def test_internal():
    assert obj._private_method() == "value"
```

## 좋은 테스트
```python
# ✅ 명확한 단일 동작
def test_user_registration_with_valid_email():
    user = register_user("test@example.com", "password")
    assert user.email == "test@example.com"
    assert user.is_active == True

# ✅ Edge case
def test_user_registration_with_duplicate_email():
    register_user("test@example.com", "pass1")
    with pytest.raises(DuplicateEmailError):
        register_user("test@example.com", "pass2")
```

## 리뷰 체크리스트
- [ ] 테스트 이름이 명확한가?
- [ ] 하나의 동작만 테스트하는가?
- [ ] Edge case를 포함하는가?
- [ ] 실패 시 원인을 알 수 있는가?
- [ ] False positive 가능성은 없는가?

## 관련 항목
- [31-write-tests-first-tdd.md](31-write-tests-first-tdd.md)
- [35-watch-test-modifications.md](35-watch-test-modifications.md)
