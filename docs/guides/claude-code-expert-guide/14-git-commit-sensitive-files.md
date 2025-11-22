# Git Best Practice #14: 민감한 파일 커밋 방지

## 원칙

.env, credentials.json 등 민감한 파일을 절대 커밋하지 마세요. Claude가 시도하면 경고하세요.

## .gitignore 설정

```bash
# .gitignore
.env
.env.*
*.key
*.pem
credentials.json
secrets.yml
config/database.yml
*.p12
*.pfx
.aws/
.azure/
```

## Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

FORBIDDEN_FILES=".env|credentials|secrets|*.key"

if git diff --cached --name-only | grep -E "$FORBIDDEN_FILES"; then
    echo "❌ ERROR: Attempting to commit sensitive files"
    echo "Files:"
    git diff --cached --name-only | grep -E "$FORBIDDEN_FILES"
    exit 1
fi
```

## Claude 설정

CLAUDE.md:
```markdown
## Security Rules
- **NEVER** commit .env files
- **NEVER** commit files with passwords, API keys
- **ALWAYS** warn user if they try
- **ALWAYS** use .env.example instead
```

## 안전한 관리

```bash
# 1. .env.example 생성 (값 제외)
DATABASE_URL=postgresql://user:pass@localhost/db
API_KEY=your_api_key_here

# 2. .env.example만 커밋
git add .env.example
git commit -m "docs: Add environment variables template"

# 3. .env는 .gitignore
echo ".env" >> .gitignore
```

## 이미 커밋된 경우

```bash
# 1. 즉시 secret 변경 (GitHub, API 등)

# 2. 최근 커밋이면
git reset HEAD~1
git reset .env

# 3. 이미 push되었으면
# → 복잡함, 전문가 도움 필요
# → git-filter-branch 또는 BFG Repo-Cleaner
```

## 관련 항목
- [05-git-never-skip-hooks.md](05-git-never-skip-hooks.md)
