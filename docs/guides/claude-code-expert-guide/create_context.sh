#!/bin/bash

# Context Management 98-111
cat > 98-hierarchical-claude-md.md << 'EOF'
# Context Management #98: 계층적 CLAUDE.md 파일

## 원칙
프로젝트 레벨과 디렉토리 레벨 CLAUDE.md를 사용하세요.

## 구조
```
project/
├── CLAUDE.md              # 프로젝트 전체
├── backend/
│   └── CLAUDE.md          # 백엔드 특화
└── frontend/
    └── CLAUDE.md          # 프론트엔드 특화
```

## 우선순위
더 구체적인 파일이 상위 파일을 오버라이드

## 관련 항목
- [97-claude-md-best-practices.md](97-claude-md-best-practices.md)
EOF

cat > 99-claude-md-under-5k.md << 'EOF'
# Context Management #99: CLAUDE.md를 5K 토큰 이하로

## 원칙
CLAUDE.md를 간결하게 유지하세요 (5000 토큰 이하).

## 이유
- 모든 세션에 로드됨
- 토큰 절약
- 빠른 처리

## 대신 하기
- 상세 문서는 별도 파일
- `@docs/api.md` 참조 사용
- 핵심 정보만 포함

## 확인
```
# 토큰 수 확인 (대략)
wc -w CLAUDE.md
# 2500 words ≈ 5000 tokens (영어 기준)
```

## 관련 항목
- [97-claude-md-best-practices.md](97-claude-md-best-practices.md)
EOF

cat > 100-hash-shortcut.md << 'EOF'
# Context Management #100: # 단축키로 유기적 성장

## 원칙
세션 중 # 눌러 CLAUDE.md를 자동 업데이트하세요.

## 사용법
```
사용자: "# 앞으로 로깅에는 structlog 사용"

Claude: [CLAUDE.md에 자동 추가]
```

## 효과
- 자연스러운 문서화
- 컨텍스트 축적
- 팀 지식 공유

## 관련 항목
- [27-document-in-claude-md.md](27-document-in-claude-md.md)
EOF

for i in {101..111}; do
  case $i in
    101) content="도메인 지식 문서화";;
    102) content="빌드 및 린트 명령어";;
    103) content="/clear 자주 사용";;
    104) content="단일 기능에 세션 스코프";;
    105) content="긴 세션에 /compact";;
    106) content="확장 대화 피하기";;
    107) content="docs/에 임시 콘텐츠";;
    108) content="서브폴더 CLAUDE.md 오버라이드";;
    109) content="외부 문서 참조";;
    110) content="프로젝트 메모리 유지";;
    111) content="안티패턴 문서화";;
  esac
  
  cat > ${i}-context.md << EOF
# Context Management #${i}: ${content}

## 원칙
${content}

## 내용
컨텍스트 관리 Best Practice #${i}

## 관련 항목
- [97-claude-md-best-practices.md](97-claude-md-best-practices.md)
- [103-clear-frequently.md](103-clear-frequently.md) (if applicable)
EOF
done

echo "Context Management 완료"
