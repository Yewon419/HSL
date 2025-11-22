# Git Best Practice #12: Amend 전 작성자 확인

## 원칙

커밋을 `--amend`하기 전에 항상 작성자와 push 여부를 확인하세요.

## 이유

- 다른 사람의 커밋을 수정하면 안 됨
- 이미 push된 커밋 수정 시 문제 발생
- 협업 시 혼란 방지

## 안전한 Amend 절차

```bash
# 1. 작성자 확인
git log -1 --format='%an %ae'

# 2. Push 여부 확인
git status
# "Your branch is ahead" 확인

# 3. 본인 커밋 + 미push인 경우만 amend
git commit --amend

# 4. 이미 push되었거나 다른 사람 커밋이면
# → 새 커밋 생성
git commit -m "fix: ..."
```

## Claude가 자동 확인

```
사용자: "커밋을 수정해줘"

Claude:
1. git log -1 --format='%an %ae' 확인
2. git status로 push 여부 확인
3. 안전하면 amend, 아니면 새 커밋
```

## Amend가 안전한 경우

```
✅ 본인이 작성한 커밋
✅ 아직 push 안 함
✅ 로컬에만 존재
```

## Amend 대신 새 커밋

```
❌ 다른 사람 커밋
❌ 이미 push됨
❌ 공유된 브랜치
→ 항상 새 커밋 생성
```

## 관련 항목
- [11-git-never-force-push-main.md](11-git-never-force-push-main.md)
