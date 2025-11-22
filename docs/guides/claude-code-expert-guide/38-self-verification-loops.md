# Error Prevention #38: 자동 검증 루프 설정

## 원칙
Claude가 자신의 작업을 빌드, 테스트, 린트 실행으로 자동 검증하도록 설정하세요.

## 워크플로우
```
1. 코드 작성
2. 자동 빌드
3. 자동 테스트
4. 자동 린트
5. 모두 통과 → 커밋
   하나라도 실패 → 수정
```

## 요청 방법
```
"이 기능을 구현한 후:
1. 빌드
2. 모든 테스트 실행
3. 린트 체크
4. 타입 체크
를 자동으로 실행하고, 모두 통과하면 커밋해줘"
```

## CI/CD 통합
```yaml
# .github/workflows/pr.yml
name: PR Checks
on: [pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm test
      - run: npm run lint
      - run: npm run type-check
```

## 장점
- 자동 품질 보증
- 휴먼 에러 방지
- 일관된 검증
