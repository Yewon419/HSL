# Error Prevention #40: 전체 테스트 스위트 실행

## 원칙
Claude가 변경 후 포괄적인 테스트를 실행하도록 하세요.

## 단일 테스트만 ❌
```bash
pytest tests/test_auth.py  # 한 파일만
```

## 전체 테스트 ✅
```bash
pytest tests/  # 모든 테스트
pytest tests/ -v --cov=src --cov-report=term
```

## 요청 방법
```
"변경 후 전체 테스트 스위트를 실행하고,
커버리지 리포트도 보여줘"
```

## 회귀 방지
```
새 기능 추가 시:
- 새 테스트 통과 ✓
- 기존 테스트도 통과 ✓  ← 중요!
```

## CI에서 확인
```yaml
# .github/workflows/test.yml
- run: pytest tests/ --cov=src --cov-report=xml
- uses: codecov/codecov-action@v3
```
