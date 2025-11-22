#!/bin/bash

# Recovery Strategies 89-96
cat > 89-rewind-command.md << 'EOF'
# Recovery Strategies #89: /rewind 명령어 사용

## 원칙
Esc 두 번 눌러 rewind 메뉴에 액세스하세요.

## 사용법
```
Esc Esc → Rewind 메뉴
또는
/rewind
```

## 옵션
1. **대화만 복원**: 코드는 그대로, 대화만 되돌리기
2. **코드만 복원**: 대화는 그대로, 파일만 되돌리기
3. **둘 다 복원**: 모두 되돌리기

## 언제 사용?
- 잘못된 변경 발생
- 실험 실패
- 다른 방향으로 시도
- 대화가 혼란스러울 때

## 장점
- 빠른 복구
- Git 커밋 불필요
- 여러 시점 선택 가능

## 관련 항목
- [04-git-checkpoints-vs-commits.md](04-git-checkpoints-vs-commits.md)
- [39-checkpoints-before-major-changes.md](39-checkpoints-before-major-changes.md)
EOF

for i in {90..96}; do
  case $i in
    90) content="복구 범위 선택";;
    91) content="Undo 전 미리보기";;
    92) content="Checkpoint 선택적 복원";;
    93) content="Claude에게 되돌리기 요청";;
    94) content="Git 롤백 사용";;
    95) content="/clear로 새로 시작";;
    96) content="실패 작업 나누기";;
  esac
  
  cat > ${i}-recovery.md << EOF
# Recovery Strategies #${i}: ${content}

## 원칙
${content}

## 내용
복구 전략 #${i}

## 관련 항목
- [89-rewind-command.md](89-rewind-command.md)
EOF
done

echo "Recovery Strategies 완료"
