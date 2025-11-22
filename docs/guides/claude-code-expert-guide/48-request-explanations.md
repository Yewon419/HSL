# Communication Patterns #48: 설명 요청하기

## 원칙
구현하면서 솔루션의 합리성을 검증하도록 Claude에게 요청하세요.

## 요청 방법
"이 기능을 구현하면서 각 단계의 선택 이유를 설명해줘"

## 효과
- 더 나은 솔루션 발견
- 학습 기회
- 잘못된 방향 조기 감지
- 의사결정 투명성

## 예시
```
Claude: "이 문제를 Redis로 해결하겠습니다.

선택 이유:
1. 메모리 기반으로 빠른 읽기/쓰기
2. TTL 지원으로 자동 만료
3. Pub/Sub 기능으로 확장 가능
4. 기존 인프라와 호환

대안:
- Memcached: TTL 세밀 제어 부족
- In-memory: 서버 재시작 시 데이터 손실

따라서 Redis가 최적입니다."
```

## 관련 항목
- [45-explicit-direct-instructions.md](45-explicit-direct-instructions.md)
