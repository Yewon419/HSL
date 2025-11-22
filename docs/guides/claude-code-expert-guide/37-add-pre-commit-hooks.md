# Error Prevention #37: Pre-commit Hook 설정

## 원칙
커밋 전에 테스트, 타입 체크, 린트 등을 자동 실행하도록 hook을 설정하세요.

## Husky (JavaScript)
```bash
npm install -D husky
npx husky init

# .husky/pre-commit
npm test
npm run lint
npm run type-check
```

## pre-commit (Python)
```bash
pip install pre-commit

# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.0.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

pre-commit install
```

## 수동 Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running tests..."
pytest tests/ || exit 1

echo "Running linter..."
ruff check . || exit 1

echo "Running type checker..."
mypy . || exit 1

echo "✅ All checks passed"
```

## 관련 항목
- [05-git-never-skip-hooks.md](05-git-never-skip-hooks.md)
