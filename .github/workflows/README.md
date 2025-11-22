# CI/CD 파이프라인 설정 가이드

## 개요

GitHub Actions를 사용하여 `main` 브랜치에 Push할 때마다 자동으로 운영 서버(101, 102)에 배포됩니다.

## 배포 흐름

```
로컬 PC (개발)
    ↓ git push
GitHub Repository
    ↓ GitHub Actions 트리거
[Job 1] 102 서버 배포 (Backend/Celery)
    ↓ 성공 시
[Job 2] 101 서버 배포 (Scheduler/Grafana)
    ↓ 성공 시
[Job 3] Health Check
    ↓
배포 완료 ✅
```

## 초기 설정

### 1. GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions → New repository secret

**필수 Secret:**
- `SSH_PRIVATE_KEY`: 서버 접속용 SSH Private Key

#### SSH Key 생성 및 등록

1. **로컬에서 SSH Key 생성** (이미 생성했으면 스킵)
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ""
   ```

2. **Public Key를 각 서버에 등록**
   ```bash
   # 102 서버
   ssh-copy-id hansol@192.168.219.102

   # 101 서버
   ssh-copy-id hansol@192.168.219.101
   ```

3. **Private Key를 GitHub Secrets에 등록**
   ```bash
   # Private Key 내용 복사
   cat ~/.ssh/id_rsa
   ```

   GitHub에 `SSH_PRIVATE_KEY` 이름으로 저장

### 2. 서버에 Git 저장소 Clone

각 서버에서 실행:

```bash
# 101, 102 서버
cd ~
git clone https://github.com/chohkcloud/happystocklife.git stock-trading-system
cd stock-trading-system
```

### 3. 서버에 .env.production 파일 생성

**102 서버:**
```bash
cd /home/hansol/stock-trading-system
cp stock-trading-system/.env.production.example stock-trading-system/.env.production
# 실제 값으로 수정
nano stock-trading-system/.env.production
```

**101 서버:**
```bash
cd /home/hansol/stock-trading-system
cp stock-trading-system/.env.production.example stock-trading-system/.env.production
# 실제 값으로 수정
nano stock-trading-system/.env.production
```

**중요:** `.env.production` 파일은 Git에서 제외되므로 각 서버에서 직접 생성 필요!

## 사용 방법

### 자동 배포 (권장)

```bash
# 로컬에서 개발
cd F:\hhstock
git add .
git commit -m "feat: 새로운 기능 추가"
git push origin main

# GitHub Actions가 자동으로 배포 시작
# https://github.com/chohkcloud/happystocklife/actions 에서 진행 상황 확인
```

### 수동 배포

GitHub Repository → Actions → Deploy to Production Servers → Run workflow

## 배포 확인

### GitHub Actions 로그 확인

https://github.com/chohkcloud/happystocklife/actions

### 서버 상태 확인

```bash
# 102 서버
ssh hansol@192.168.219.102
docker ps
docker-compose logs -f backend

# 101 서버
ssh hansol@192.168.219.101
docker ps
docker-compose logs -f grafana
```

### Health Check

```bash
# Backend API
curl http://192.168.219.102:8000/health

# Grafana
curl http://192.168.219.101:3000/api/health
```

## 문제 해결

### 배포 실패 시

1. **GitHub Actions 로그 확인**
   - https://github.com/chohkcloud/happystocklife/actions
   - 실패한 Job의 로그 확인

2. **서버 로그 확인**
   ```bash
   ssh hansol@192.168.219.102
   cd /home/hansol/stock-trading-system
   docker-compose logs --tail=100
   ```

3. **롤백**
   ```bash
   # 서버에서 실행
   cd /home/hansol/stock-trading-system
   git log --oneline -5  # 이전 커밋 확인
   git checkout <이전-커밋-해시>
   docker-compose down
   ENVIRONMENT=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

### SSH 연결 실패

- GitHub Secrets의 `SSH_PRIVATE_KEY` 확인
- 서버의 `~/.ssh/authorized_keys`에 Public Key가 있는지 확인
- 서버의 SSH 서비스 상태 확인: `sudo systemctl status ssh`

### Docker 빌드 실패

- 서버 디스크 공간 확인: `df -h`
- Docker 이미지 정리: `docker system prune -a`

## 보안 고려사항

1. **.env.production 파일**
   - Git에 절대 커밋하지 않음
   - 각 서버에서 직접 관리

2. **SSH Private Key**
   - GitHub Secrets에만 저장
   - 절대 코드에 포함하지 않음

3. **네트워크 접근**
   - GitHub Actions Runner는 서버에 SSH로만 접근
   - 방화벽 설정 확인: 22번 포트 허용

## 다음 단계

- [ ] Staging 환경 구축 (테스트 서버)
- [ ] 롤백 자동화
- [ ] Slack/Discord 알림 연동
- [ ] 배포 전 테스트 자동화
- [ ] Blue-Green 배포 전략
