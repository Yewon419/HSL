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
