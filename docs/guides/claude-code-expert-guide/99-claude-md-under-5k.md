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
