# Error Prevention #41: 컴파일 오류 명시적 확인

## 원칙
컴파일 언어에서 코드가 실제로 컴파일되는지 명시적으로 확인하세요.

## 확인 항목
```
1. Syntax 오류 없음
2. Type 오류 없음
3. Import 오류 없음
4. Linking 오류 없음
```

## 언어별 확인

### TypeScript
```bash
tsc --noEmit
```

### Java
```bash
javac src/**/*.java
```

### C++
```bash
g++ -Wall -Werror src/*.cpp
```

### Rust
```bash
cargo check
```

## 요청
```
"코드를 작성한 후 컴파일 오류가 있는지 확인해줘.
Warning도 모두 수정해줘"
```
