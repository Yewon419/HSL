# Git Best Practice #15: 대화형 Git 명령어 사용 금지

## 원칙

`git rebase -i`, `git add -i` 등 대화형 명령어는 Claude Code에서 사용하지 마세요.

## 이유

- Claude Code는 대화형 입력 지원 안 함
- 명령어가 멈추고 응답 없음
- 세션이 중단될 수 있음

## ❌ 사용 금지

```bash
git rebase -i HEAD~3    # 대화형 에디터 필요
git add -i              # 대화형 스테이징
git commit --interactive
```

## ✅ 대안

### Rebase 대신
```bash
# 개별 커밋 수정
git commit --fixup <commit-hash>
git rebase --autosquash

# 또는 squash merge
git merge --squash feature-branch
```

### Add -i 대신
```bash
# 파일별로 명시적 add
git add file1.py file2.py

# 패턴 사용
git add src/**/*.py

# Patch mode (비대화형)
git add -p file.py  # y/n으로 응답 가능
```

## Claude에게 요청

```
"여러 커밋을 하나로 합쳐줘.
단, 대화형 명령어는 사용하지 마"

Claude:
git reset --soft HEAD~3
git commit -m "Combined: feature implementation"
```

## 관련 항목
- [09-git-github-flow.md](09-git-github-flow.md)
