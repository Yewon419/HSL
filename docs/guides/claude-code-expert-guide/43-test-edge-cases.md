# Error Prevention #43: Edge Case 테스트

## 원칙
Claude에게 edge case, 오류 조건, 다양한 입력 시나리오를 커버하도록 요청하세요.

## Edge Cases 유형

### 경계값
```python
def test_age_validation():
    assert validate_age(0) == False    # 최소값
    assert validate_age(1) == True
    assert validate_age(120) == True
    assert validate_age(121) == False  # 최대값
```

### Null/Empty
```python
def test_empty_inputs():
    assert process(None) raises ValueError
    assert process("") raises ValueError
    assert process([]) raises ValueError
```

### 특수 문자
```python
def test_special_characters():
    assert validate_email("user@domain.com") == True
    assert validate_email("user+tag@domain.com") == True
    assert validate_email("user@sub.domain.com") == True
```

## 요청 방법
```
"이 함수의 테스트를 작성해줘. 특히:
- Boundary values
- Null/empty inputs
- 특수 문자
- 동시성 이슈
- 네트워크 오류
를 포함해줘"
```

## 관련 항목
- [31-write-tests-first-tdd.md](31-write-tests-first-tdd.md)
