# Error Prevention #42: 린팅 통과 확인

## 원칙
코드 스타일과 품질 검사가 통과하는지 확인하세요.

## Linters

### Python
```bash
ruff check .
flake8 .
pylint src/
```

### JavaScript
```bash
eslint .
```

### Go
```bash
golint ./...
```

## Auto-fix
```bash
# Python
ruff check --fix .
black .

# JavaScript
eslint --fix .
prettier --write .
```

## 요청
```
"린팅을 실행하고, 자동 수정 가능한 것은 수정해줘.
수동 수정이 필요한 것은 알려줘"
```

## Pre-commit에 통합
```yaml
# .pre-commit-config.yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  hooks:
    - id: ruff
      args: [--fix]
```
