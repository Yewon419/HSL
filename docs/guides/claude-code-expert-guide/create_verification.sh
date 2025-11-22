#!/bin/bash

# Verification Workflows 77-88
for i in {77..88}; do
  title="Verification Workflows"
  case $i in
    77) content="/security-review 명령어";;
    78) content="PR용 GitHub Action";;
    79) content="독립 서브에이전트로 리뷰";;
    80) content="주관적 이슈 체크";;
    81) content="테스트 커버리지 확인";;
    82) content="테스트 실행 및 통과 확인";;
    83) content="점진적 마이그레이션 테스트";;
    84) content="TDD - Claude 최적";;
    85) content="린트 및 타입 체크";;
    86) content="프로젝트 빌드";;
    87) content="Breaking change 체크";;
    88) content="커밋 메시지 리뷰";;
  esac
  
  cat > ${i}-verification.md << EOF
# Verification Workflows #${i}: ${content}

## 원칙
${content}

## 내용
검증 워크플로우 #${i}

## 관련 항목
- Verification Workflows 카테고리 참조
EOF
done

echo "Verification Workflows 완료"
