# Self-hosted Runner 설정 가이드

## 개요
GitHub Actions의 self-hosted runner를 설정하여 로컬 네트워크 내부 서버에 자동 배포합니다.

## 왜 필요한가?
- 배포 대상 서버(192.168.219.101, 192.168.219.102)는 사설 IP
- GitHub의 클라우드 runner는 사설 네트워크에 접근 불가
- 로컬 네트워크 내부에서 실행되는 runner 필요

## Self-hosted Runner 설치

### 1단계: Runner 설치할 서버 선택
- 101 서버 또는 102 서버 중 하나를 선택
- 또는 별도의 관리 서버 사용 가능

### 2단계: GitHub에서 Runner 설정
1. GitHub 저장소 → **Settings** → **Actions** → **Runners**
2. **New self-hosted runner** 클릭
3. OS 선택 (Linux)
4. 표시되는 명령어 복사

### 3단계: 서버에서 Runner 설치 (예: 102 서버)

```bash
# 102 서버에 SSH 접속
ssh yunsang@192.168.219.102

# runner용 디렉토리 생성
mkdir -p ~/actions-runner && cd ~/actions-runner

# Runner 다운로드 (GitHub에서 제공하는 최신 버전 URL 사용)
curl -o actions-runner-linux-x64-2.311.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.311.0/actions-runner-linux-x64-2.311.0.tar.gz

# 압축 해제
tar xzf ./actions-runner-linux-x64-2.311.0.tar.gz

# Runner 설정 (GitHub에서 제공한 토큰 사용)
./config.sh --url https://github.com/chohkcloud/happystocklife --token YOUR_TOKEN_HERE

# 서비스로 등록 (재부팅 시 자동 시작)
sudo ./svc.sh install
sudo ./svc.sh start
```

### 4단계: Runner 상태 확인
GitHub 저장소 → Settings → Actions → Runners에서 runner가 "Idle" 상태인지 확인

## 워크플로우 파일 수정

`.github/workflows/deploy.yml`을 수정하여 self-hosted runner 사용:

```yaml
jobs:
  deploy-all:
    name: Deploy to Servers
    runs-on: self-hosted  # ← ubuntu-latest에서 변경

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Deploy to 102 Server
        run: |
          ssh yunsang@192.168.219.102 << 'EOF'
            cd /home/yunsang/stock-trading-system
            git pull origin main
            docker-compose down
            ENVIRONMENT=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
          EOF

      - name: Deploy to 101 Server
        run: |
          ssh yunsang@192.168.219.101 << 'EOF'
            cd /home/yunsang/stock-trading-system
            git pull origin main
            docker-compose down
            ENVIRONMENT=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
          EOF
```

## 장단점

### 장점
- ✅ 로컬 네트워크 내부 서버에 직접 접근
- ✅ 복잡한 네트워크 설정 불필요
- ✅ 빠른 배포 속도
- ✅ SSH 키 설정 간소화

### 단점
- ❌ Runner 서버가 항상 켜져 있어야 함
- ❌ Runner 서버 관리 필요

## 대안: 수동 배포 스크립트

Self-hosted runner 설정이 부담스럽다면 수동 배포 스크립트 사용:

```bash
# deploy.sh
#!/bin/bash
echo "🚀 배포 시작..."

# 102 서버 배포
echo "📦 102 서버 배포 중..."
ssh yunsang@192.168.219.102 << 'EOF'
  cd /home/yunsang/stock-trading-system
  git pull origin main
  docker-compose down
  ENVIRONMENT=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
EOF

# 101 서버 배포
echo "📦 101 서버 배포 중..."
ssh yunsang@192.168.219.101 << 'EOF'
  cd /home/yunsang/stock-trading-system
  git pull origin main
  docker-compose down
  ENVIRONMENT=production docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
EOF

echo "✅ 배포 완료!"
```

사용법:
```bash
chmod +x deploy.sh
./deploy.sh
```
