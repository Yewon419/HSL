# Git Best Practice #3: 프로젝트의 커밋 메시지 규칙 따르기

## 원칙

Claude에게 `git log`로 최근 커밋 히스토리를 확인하고 프로젝트의 커밋 메시지 스타일을 따르도록 합니다.

## 이유

- 프로젝트 전체의 일관성 유지
- 팀 규칙 준수
- 자동화 도구와의 호환성 (conventional commits, changelog 생성 등)
- 코드 리뷰 시 혼란 방지

## 실전 예시

```
사용자: "커밋하기 전에 기존 커밋 스타일을 확인해줘"

Claude:
1. git log --oneline -10 실행
2. 패턴 분석:
   - "feat(auth): ..."
   - "fix(api): ..."
   - 스코프를 괄호로 표시하는 규칙 발견
3. 같은 형식으로 커밋 메시지 작성
```

## 자주 사용되는 커밋 규칙들

### Conventional Commits
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Semantic Commit Messages
```
feat: add hat wobble
^--^  ^------------^
│     │
│     └─⫸ 요약 (현재형, 소문자, 마침표 없음)
│
└─⫸ Type: chore, docs, feat, fix, refactor, style, test
```

### Angular Convention
```
<type>(<scope>): <short summary>
  │       │             │
  │       │             └─⫸ 명령형 현재 시제
  │       │
  │       └─⫸ 변경 위치 (선택)
  │
  └─⫸ build|ci|docs|feat|fix|perf|refactor|test
```

## Claude에게 요청하는 방법

```
"프로젝트의 최근 20개 커밋을 확인하고,
같은 스타일로 커밋 메시지를 작성해줘"
```

## 팁

- 새 프로젝트 시작 시 규칙을 CLAUDE.md에 문서화
- `.gitmessage` 템플릿 파일 활용
- commitlint 같은 도구로 규칙 강제

## 관련 항목

- [02-git-commit-messages.md](02-git-commit-messages.md) - 커밋 메시지 생성
- [97-claude-md-best-practices.md](97-claude-md-best-practices.md) - CLAUDE.md 작성법
