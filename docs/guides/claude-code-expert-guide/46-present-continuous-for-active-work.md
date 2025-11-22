# Communication Patterns #46: 작업 중 현재진행형 사용

## 원칙

Claude가 작업을 수행하는 동안 설명할 때는 현재진행형(present continuous)을 사용하세요.

## 이유

- 진행 상황이 명확함
- 사용자 경험 향상
- 자연스러운 커뮤니케이션
- 작업 상태 투명성

## Todo 형식

### 명령형 (content)
```
"테스트 실행"
"빌드"
"배포"
```

### 현재진행형 (activeForm)
```
"테스트 실행 중"
"빌드 중"
"배포 중"
```

## 실전 예시

### ❌ 일관성 없음
```
todo: {
  content: "Run tests",
  activeForm: "Run tests"  // 같은 형태
}
```

### ✅ 올바른 사용
```
todo: {
  content: "Run tests",  // 명령형: 무엇을 할지
  activeForm: "Running tests"  // 진행형: 지금 하고 있는 것
}
```

## 패턴

```javascript
{
  content: "테스트 작성",
  activeForm: "테스트 작성 중"
},
{
  content: "API 구현",
  activeForm: "API 구현 중"
},
{
  content: "문서 업데이트",
  activeForm: "문서 업데이트 중"
},
{
  content: "코드 리뷰",
  activeForm: "코드 리뷰 중"
}
```

## 영어 패턴

```javascript
{
  content: "Write tests",
  activeForm: "Writing tests"
},
{
  content: "Build project",
  activeForm: "Building project"
},
{
  content: "Deploy to production",
  activeForm: "Deploying to production"
},
{
  content: "Update documentation",
  activeForm: "Updating documentation"
}
```

## UI 표시 예시

### 대기 중 (pending)
```
[ ] 테스트 실행
```

### 진행 중 (in_progress)
```
[→] 테스트 실행 중... ⏳
```

### 완료 (completed)
```
[✓] 테스트 실행
```

## TodoWrite 사용

```javascript
// Claude가 TodoWrite 호출 시
{
  "todos": [
    {
      "content": "Run full test suite",
      "status": "in_progress",
      "activeForm": "Running full test suite"
    },
    {
      "content": "Fix linting errors",
      "status": "pending",
      "activeForm": "Fixing linting errors"
    },
    {
      "content": "Commit changes",
      "status": "pending",
      "activeForm": "Committing changes"
    }
  ]
}
```

## 사용자 관점에서 표시

```
프로젝트 진행 상황:
[✓] 계획 수립
[→] 테스트 작성 중... (진행 중)
[ ] 구현
[ ] 문서화
```

## 장점

### 1. 명확성
```
Before: "테스트 실행"
→ 할 일인가? 하는 중인가? 완료했나?

After: "테스트 실행 중"
→ 지금 하고 있구나!
```

### 2. 진행 상황 파악
```
[✓] 코드 작성
[→] 테스트 실행 중
[ ] 커밋

→ 사용자: "아, 지금 테스트 중이구나. 기다려야겠다"
```

### 3. 자연스러운 대화
```
Claude: "테스트 실행 중입니다..."
[30초 후]
Claude: "테스트가 완료되었습니다. 모두 통과했습니다."

vs.

Claude: "테스트 실행"
[30초 침묵]
Claude: "완료"
→ 어색함
```

## 동사별 패턴

| 명령형 | 현재진행형 |
|--------|-----------|
| Create | Creating |
| Update | Updating |
| Delete | Deleting |
| Build | Building |
| Test | Testing |
| Deploy | Deploying |
| Refactor | Refactoring |
| Review | Reviewing |
| Analyze | Analyzing |
| Optimize | Optimizing |
| Debug | Debugging |
| Implement | Implementing |
| Configure | Configuring |
| Validate | Validating |
| Generate | Generating |

## CLAUDE.md 설정

```markdown
## Todo Format Rules

When creating todos, always use:
- `content`: Imperative form (what to do)
- `activeForm`: Present continuous (what is being done)

Examples:
- content: "Run tests"
  activeForm: "Running tests"

- content: "Build Docker image"
  activeForm: "Building Docker image"
```

## 예외 사항

일부 동사는 진행형이 어색할 수 있음:

```
❌ "Commiting" (오타처럼 보임)
✅ "Committing"

❌ "Debuging"
✅ "Debugging"
```

## 한국어 패턴

```javascript
{
  content: "테스트 실행",
  activeForm: "테스트 실행 중"
},
{
  content: "빌드",
  activeForm: "빌드 중"
},
{
  content: "배포",
  activeForm: "배포 중"
},
{
  content: "분석",
  activeForm: "분석 중"
}
```

## 관련 항목

- [45-explicit-direct-instructions.md](45-explicit-direct-instructions.md) - 명확한 지시
- TodoWrite tool usage
