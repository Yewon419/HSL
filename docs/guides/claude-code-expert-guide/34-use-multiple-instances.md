# Error Prevention #34: 여러 Claude 인스턴스 사용

## 원칙
하나의 Claude는 코드 작성, 다른 Claude는 리뷰 또는 테스트하도록 분리하세요.

## 사용 패턴
```
터미널 1 (Claude-Dev):
"사용자 인증 API를 구현해줘"

터미널 2 (Claude-Review):
"@auth/api.py를 보안 관점에서 리뷰해줘"

터미널 3 (Claude-Test):
"@auth/api.py의 엣지 케이스 테스트를 작성해줘"
```

## 역할 분리
- **Developer**: 기능 구현
- **Reviewer**: 코드 리뷰, 보안 검사
- **Tester**: 테스트 작성, 품질 보증
- **Architect**: 설계, 리팩토링

## 장점
- 독립적 관점
- 병렬 작업
- 품질 향상

## 관련 항목
- [117-specialized-instances.md](117-specialized-instances.md)
