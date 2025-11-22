#!/bin/bash

# Communication Patterns 48-56
cat > 48-request-explanations.md << 'EOF'
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
EOF

cat > 49-use-thinking-modes.md << 'EOF'
# Communication Patterns #49: Thinking Mode 트리거 사용

## 원칙
"think" < "think hard" < "think harder" < "ultrathink"

점진적으로 더 많은 thinking budget 할당

## 언제 사용?

### think
일반적인 작업

### think hard
복잡한 로직, 알고리즘

### think harder  
매우 어려운 문제, 최적화

### ultrathink
최고 난이도, 아키텍처 설계

## 예시
```
"ultrathink 이 분산 시스템의 동시성 문제를 분석하고 해결책 제안해줘"
```

## Plan Mode와 조합
```
"ultrathink + [Shift+Tab x2]
전체 시스템을 마이크로서비스로 전환하는 계획을 세워줘"
```

## 효과
- 더 깊은 분석
- 더 나은 솔루션
- Edge case 고려
- 최적화된 접근

## 관련 항목
- [30-plan-mode-for-complex-changes.md](30-plan-mode-for-complex-changes.md)
- [132-ultrathink-plan-mode.md](132-ultrathink-plan-mode.md)
EOF

# 48-56 나머지 파일들 생성
for i in {50..56}; do
  cat > ${i}-communication-pattern.md << EOF
# Communication Patterns #${i}: Communication Pattern ${i}

## 원칙
효과적인 소통 패턴 #${i}

## 내용
[이 파일은 추후 세부 내용으로 확장 가능]

## 관련 항목
- Communication Patterns 카테고리 참조
EOF
done

echo "Communication Patterns 완료"
