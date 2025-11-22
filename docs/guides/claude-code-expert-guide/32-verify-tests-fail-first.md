# Error Prevention #32: 구현 전 테스트 실패 확인

## 원칙
테스트를 작성한 후 실패하는 것을 확인하고, 구현 코드는 작성하지 말라고 명시하세요.

## TDD Red-Green-Refactor
```
1. Red: 실패하는 테스트 작성
2. 실패 확인 ← 중요!
3. Green: 최소 구현
4. 테스트 통과 확인
5. Refactor: 개선
```

## 왜 실패 확인이 중요한가?
- 테스트가 실제로 작동하는지 검증
- False positive 방지
- 올바른 것을 테스트하는지 확인

## 실전 예시
```
사용자: "이메일 검증 함수의 테스트를 작성해줘.
⚠️ 구현 코드는 아직 작성하지 마"

Claude: [테스트만 작성]

사용자: "테스트를 실행해서 실패하는지 확인해줘"

Claude:
$ pytest test_email.py
FAILED - NameError: name 'validate_email' is not defined
✅ 예상대로 실패

사용자: "좋아, 이제 구현해줘"
```

## 관련 항목
- [31-write-tests-first-tdd.md](31-write-tests-first-tdd.md)
