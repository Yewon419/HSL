#!/bin/bash

# File Management 57-68
for i in {57..68}; do
  title="File Management"
  case $i in
    57) content="파일 참조에 @ 사용하기";;
    58) content="일반 영역 지정하기";;
    59) content="Glob 패턴 사용";;
    60) content="불필요한 파일 읽기 방지";;
    61) content="파일 생성보다 편집 우선";;
    62) content="파일을 집중적으로 유지";;
    63) content="변경사항 리뷰하기";;
    64) content="/rewind로 코드만 롤백";;
    65) content="Git을 주요 백업으로";;
    66) content="세션 복구용 Checkpoint";;
    67) content="수동 변경은 추적 안 됨";;
    68) content="동시 세션 편집 주의";;
  esac
  
  cat > ${i}-file-management.md << EOF
# File Management #${i}: ${content}

## 원칙
${content} 관련 모범 사례

## 내용
파일 관리 Best Practice #${i}

## 관련 항목
- File Management 카테고리 참조
EOF
done

echo "File Management 완료"
