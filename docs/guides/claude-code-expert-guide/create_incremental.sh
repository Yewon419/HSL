#!/bin/bash

# Incremental Development 70-76
for i in {70..76}; do
  title="Incremental Development"
  case $i in
    70) content="컨텍스트 타이트하게 유지";;
    71) content="한 번에 하나의 작업";;
    72) content="2-3회 반복하기";;
    73) content="Checkpoint + /rewind";;
    74) content="진행 전 검증";;
    75) content="AI 출력을 신뢰하지 않기";;
    76) content="점진적 리팩토링";;
  esac
  
  cat > ${i}-incremental.md << EOF
# Incremental Development #${i}: ${content}

## 원칙
${content}

## 내용
점진적 개발 Best Practice #${i}

## 관련 항목
- [69-small-changes-philosophy.md](69-small-changes-philosophy.md)
EOF
done

echo "Incremental Development 완료"
