# Git Best Practice #1: 항상 기능 브랜치를 먼저 만들기

## 원칙

작업을 시작하기 전에 **항상** Claude에게 새로운 브랜치를 만들도록 요청하세요.

## 이유

- main 브랜치를 변경사항으로부터 격리
- 잘못된 변경사항을 쉽게 되돌릴 수 있음
- 여러 기능을 동시에 작업 가능
- Pull Request 생성이 용이

## 실전 예시

### ❌ 잘못된 방법
```
사용자: "로그인 기능을 추가해줘"
Claude: [main 브랜치에서 직접 작업 시작]
```

### ✅ 올바른 방법
```
사용자: "로그인 기능을 위한 브랜치를 만들고 작업해줘"
Claude:
1. git checkout -b feature/login
2. [작업 진행]
3. git commit
4. git push -u origin feature/login
```

## 브랜치 이름 규칙

- `feature/기능명` - 새 기능
- `fix/버그명` - 버그 수정
- `refactor/모듈명` - 리팩토링
- `docs/문서명` - 문서 업데이트

## 팁

- 브랜치 이름은 짧고 명확하게
- 한 브랜치는 한 가지 목적만
- 브랜치 작업이 끝나면 삭제하기

## 관련 항목

- [02-git-commit-messages.md](02-git-commit-messages.md) - 커밋 메시지 작성법
- [09-git-github-flow.md](09-git-github-flow.md) - GitHub Flow 워크플로우
