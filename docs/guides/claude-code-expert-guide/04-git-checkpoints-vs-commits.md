# Git Best Practice #4: Checkpoint vs Git의 용도 구분

## 원칙

- **Checkpoint**: 로컬 실행 취소 (세션 내 빠른 복구)
- **Git**: 영구 버전 관리 (커밋, 브랜치, 장기 히스토리)

## 언제 무엇을 사용할까?

### Checkpoint 사용 시점
- 실험적인 변경 시도 전
- 리팩토링 시작 전
- 불확실한 접근 방식 테스트 전
- 빠른 되돌림이 필요한 경우

**특징:**
- 세션 내에서만 유효
- Esc + Esc 또는 `/rewind`로 즉시 복구
- Git 히스토리에 영향 없음

### Git 사용 시점
- 완성된 기능
- 의미 있는 변경 단위
- 팀과 공유할 코드
- 장기 보관이 필요한 시점

**특징:**
- 영구 보존
- 브랜치, PR, 협업 가능
- 언제든 복구 가능

## 실전 예시

### Scenario 1: 실험적 리팩토링

```
사용자: "이 함수를 리팩토링해보고 싶은데, 잘 될지 모르겠어"

Claude:
1. [자동으로 checkpoint 생성]
2. 리팩토링 시도
3.
   - 성공 → git commit
   - 실패 → /rewind로 되돌리기
```

### Scenario 2: 완성된 기능

```
사용자: "로그인 기능이 완성되었어. 커밋해줘"

Claude:
1. git add .
2. git commit -m "feat: Add user login functionality"
3. git push
```

## Checkpoint의 한계

⚠️ **주의사항:**
- Claude Code 외부에서 한 변경은 추적 안 됨
- 동시에 여러 세션에서 작업 시 충돌 가능
- 세션 종료 후 일부 환경에서 손실 가능 (CLI/Replit)

## 최적의 워크플로우

```
1. Git commit (안전한 시작점)
2. Checkpoint (실험 시작)
3. 시도 및 테스트
4. 성공 → Git commit
   실패 → /rewind → 다시 시도
```

## 팁

- 중요한 변경 전에는 **둘 다** 사용
- Git commit 후 checkpoint로 실험
- 불안정한 환경에서는 Git을 주요 백업으로

## 관련 항목

- [89-rewind-command.md](89-rewind-command.md) - Rewind 사용법
- [65-git-primary-backup.md](65-git-primary-backup.md) - Git 백업 전략
