# Git Best Practice #2: Claude가 커밋 메시지를 생성하게 하기

## 원칙

Claude에게 변경사항을 분석해서 설명적인 커밋 메시지를 작성하도록 합니다.

## 이유

- Claude는 변경된 모든 파일을 분석하여 포괄적인 메시지 작성 가능
- 일관된 커밋 메시지 스타일 유지
- "what"보다 "why"에 집중한 메시지 작성
- 시간 절약

## 실전 예시

### ❌ 피해야 할 메시지
```
"update files"
"fix bug"
"changes"
```

### ✅ Claude가 생성한 좋은 메시지
```
feat: Add user authentication with JWT tokens

- Implement login/logout endpoints
- Add JWT token generation and validation
- Create auth middleware for protected routes
- Update user model with password hashing

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## 사용 방법

```
사용자: "변경사항을 커밋해줘"
Claude:
1. git status로 변경사항 확인
2. git diff로 구체적 변경 내용 분석
3. git log로 기존 커밋 스타일 확인
4. 스타일에 맞는 커밋 메시지 작성
5. git commit -m "..."
```

## 커밋 메시지 구조

```
<타입>: <제목>

<본문: 무엇을, 왜 변경했는지>

<footer: 이슈 번호, co-author 등>
```

### 타입 예시
- `feat`: 새 기능
- `fix`: 버그 수정
- `refactor`: 코드 리팩토링
- `docs`: 문서 수정
- `test`: 테스트 추가/수정
- `chore`: 빌드, 설정 등

## 팁

- 제목은 50자 이내
- 본문은 72자에서 줄바꿈
- 명령형 현재 시제 사용 ("Add" not "Added")
- 왜 변경했는지 설명

## 관련 항목

- [03-git-follow-conventions.md](03-git-follow-conventions.md) - 프로젝트 규칙 따르기
