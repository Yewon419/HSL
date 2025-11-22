# Error Prevention #36: 컴파일 확인 보장

## 원칙
컴파일 언어에서 Claude가 테스트 실행 전에 컴파일하는 것을 잊는 경우가 많습니다.

## 문제
```
Claude: "테스트를 실행하겠습니다"
$ pytest tests/
→ 이전 빌드 실행 (새 코드 반영 안 됨)
```

## 해결
```
사용자: "코드를 수정한 후 반드시:
1. 먼저 컴파일
2. 그 다음 테스트
순서로 진행해줘"
```

## 언어별 예시

### Java
```bash
mvn compile && mvn test
```

### C/C++
```bash
make && make test
```

### Go
```bash
go build && go test ./...
```

### Rust
```bash
cargo build && cargo test
```

## CLAUDE.md 설정
```markdown
## Testing Workflow (Java)
1. mvn clean compile
2. mvn test
Never skip compilation!
```
