# 📧 매매신호 알림 설정 가이드

매매신호탭의 종목을 이메일이나 Slack으로 받는 기능의 설정 방법입니다.

## ✨ 새로운 기능

### 매매신호 탭에 추가된 기능
- **알림 설정 (⚙️)**: 이메일/Slack 정보 등록
- **이메일 전송 (📧)**: 현재 종목들을 이메일로 전송
- **Slack 전송 (💬)**: 현재 종목들을 Slack으로 전송

## 🔧 설정 방법

### 1️⃣ Slack 알림 설정하기

#### Slack 웹훅 생성 방법:

1. **Slack 워크스페이스 접속**
   - https://api.slack.com/apps 로 이동

2. **새 앱 생성**
   - "Create New App" 클릭
   - "From scratch" 선택
   - 앱 이름: "Stock Trading Bot"
   - 워크스페이스 선택

3. **Incoming Webhooks 활성화**
   - 왼쪽 메뉴에서 "Incoming Webhooks" 클릭
   - "Activate Incoming Webhooks" 토글 ON
   - "Add New Webhook to Workspace" 클릭
   - 채널 선택 (예: #stock-signals)
   - "Allow" 클릭

4. **웹훅 URL 복사**
   - Webhook URL이 생성됨 (예: https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX)
   - 이 URL을 복사해서 프론트엔드에 입력

#### 프론트엔드에서 설정하기:

```
1. http://localhost:8000 접속
2. "매매 신호" 탭으로 이동
3. "알림 설정" (⚙️) 버튼 클릭
4. "Slack 웹훅 URL" 필드에 위에서 복사한 URL 붙여넣기
5. "저장" 클릭
```

### 2️⃣ 이메일 알림 설정하기

#### Gmail 사용 (권장)

1. **Gmail 계정에서 앱 비밀번호 생성**
   - https://myaccount.google.com/apppasswords 이동
   - 2단계 인증 설정 필요
   - 앱 선택: "메일"
   - 기기 선택: "Windows 컴퓨터" (또는 해당 기기)
   - "생성" 클릭
   - 16자리 비밀번호 복사

2. **백엔드 환경 설정 (.env.development 또는 .env.production)**

```env
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER_ADDRESS=your-email@gmail.com
EMAIL_SENDER_PASSWORD=your-16-digit-password
```

3. **프론트엔드에서 이메일 주소 입력**

```
1. http://localhost:8000 접속
2. "매매 신호" 탭으로 이동
3. "알림 설정" (⚙️) 버튼 클릭
4. "이메일 주소" 필드에 메일주소 입력
5. "저장" 클릭
```

#### 다른 SMTP 서버 사용

Outlook, Yahoo, 회사 메일 등도 사용 가능합니다.

| 서비스 | SMTP 서버 | 포트 |
|--------|----------|------|
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp-mail.outlook.com | 587 |
| Yahoo | smtp.mail.yahoo.com | 587 |
| 회사 메일 | 관리자 문의 | 587 |

## 📤 알림 전송하기

### 매매신호 조회 후 알림 전송

```
1. http://localhost:8000 접속
2. "매매 신호" 탭으로 이동
3. 필터 적용 (국가, 종목, 날짜 등) - 선택 사항
4. "이메일 전송" (📧) 또는 "Slack 전송" (💬) 클릭
5. 알림 완료 메시지 확인
```

## 🔔 전송되는 정보

### 알림 메시지 구성
```
📊 RSI+MA 상승전략 시그널 알림

📅 날짜: 2025-10-02
📈 매수 시그널: 15개

상위 5개 종목:
1. 005930 - 삼성전자
   현재가: 55,000원
   RSI: 25.50
   MA20: 54,000 > MA50: 52,000
   ...

💻 전체 시그널 확인: http://localhost:8000/rsi_ma_strategy.html
```

## 🔒 보안 주의사항

### ⚠️ 주의
- **이메일 비밀번호**: 정상 Gmail 비밀번호가 아닌 **앱 비밀번호** 사용
- **Slack 웹훅**: 웹훅 URL은 민감한 정보이므로 공유하지 말 것
- **로컬 스토리지**: 설정은 브라우저 로컬 스토리지에 저장됨
  - 같은 컴퓨터를 여러 사람이 사용하면 비활성화 권장

### 환경 변수 보안
- 서버에서 `.env` 파일에 실제 비밀번호 저장
- Git에 비밀번호 커밋하지 않기 (`.gitignore` 확인)
- 운영 환경: 강력한 신규 비밀번호 설정 필수

## 🧪 테스트

### 프론트엔드 테스트
```javascript
// 브라우저 콘솔에서 테스트
localStorage.setItem('notificationSettings', JSON.stringify({
    email: 'test@example.com',
    slackWebhook: 'https://hooks.slack.com/services/...'
}));
```

### 백엔드 테스트 (cURL)
```bash
# Slack 알림 테스트
curl -X POST http://localhost:8000/api/trading/notifications/send-signals \
  -H "Content-Type: application/json" \
  -d '{
    "target_date": "2025-10-02",
    "slack_webhook": "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXX",
    "channels": ["slack"]
  }'

# 이메일 알림 테스트
curl -X POST http://localhost:8000/api/trading/notifications/send-signals \
  -H "Content-Type: application/json" \
  -d '{
    "target_date": "2025-10-02",
    "email": "your-email@gmail.com",
    "channels": ["email"]
  }'
```

## 📝 설정 파일 위치

| 파일 | 경로 | 설명 |
|------|------|------|
| 개발 환경 | `.env.development` | 로컬 개발용 |
| 운영 환경 | `.env.production` | 서버 배포용 |
| 프론트엔드 | `stock-trading-system/frontend/index.html` | UI 변경사항 |
| 백엔드 API | `stock-trading-system/backend/trading_service/router.py` | 알림 API |
| 알림 서비스 | `stock-trading-system/backend/trading_service/notification_service.py` | 알림 로직 |

## 🚀 구현 세부사항

### 프론트엔드 변경사항
- ✅ 매매신호 탭에 3개 버튼 추가 (알림설정, 이메일, Slack)
- ✅ 알림 설정 모달 추가 (이메일, Slack 웹훅 입력)
- ✅ 로컬 스토리지에 설정 저장
- ✅ 유효성 검사 (이메일 형식, 웹훅 URL 형식)

### 백엔드 API
- ✅ `POST /api/trading/notifications/send-signals`
  - 매개변수: target_date, email, slack_webhook, channels
  - 응답: status, message, signal_count, sent_count

### 알림 서비스
- ✅ `NotificationService.send_email()` - SMTP 이메일 전송
- ✅ `NotificationService.send_slack()` - Slack 웹훅 전송
- ✅ HTML 형식 이메일 지원
- ✅ 에러 로깅 및 처리

## ❓ FAQ

### Q1: 이메일이 수신되지 않습니다
**A:**
- Gmail 2단계 인증 확인
- 앱 비밀번호 정확하게 입력 확인
- 스팸 폴더 확인
- `.env` 파일 EMAIL_ENABLED=true 확인

### Q2: Slack 웹훅 오류가 발생합니다
**A:**
- 웹훅 URL 정확하게 복사 확인
- 웹훅이 비활성화되지 않았는지 확인
- https://hooks.slack.com/으로 시작하는지 확인

### Q3: 설정이 저장되지 않습니다
**A:**
- 브라우저 로컬 스토리지 허용 확인
- 개인정보 보호 모드에서 테스트하지 않기
- 브라우저 개발자 도구 > Application > Local Storage 확인

### Q4: 여러 명이 사용하는 경우
**A:**
- 각자 다른 컴퓨터에서 접속 (설정 분리)
- 또는 매번 알림 설정에서 자신의 정보 입력

## 📞 트러블슈팅

### 로그 확인
```bash
# Docker 로그 확인
docker logs stock-backend

# 또는 로그 파일
tail -f /var/log/stock-trading-system/backend.log
```

### 일반적인 오류
| 오류 | 원인 | 해결방법 |
|------|------|----------|
| SMTP 연결 실패 | 이메일 설정 오류 | .env 파일 확인 |
| 401 Unauthorized | Slack 웹훅 만료 | 웹훅 URL 재생성 |
| 유효하지 않은 이메일 | 형식 오류 | example@domain.com 형식 확인 |

## 📚 참고자료

- [Slack API - Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [Gmail - 앱 비밀번호 생성](https://support.google.com/accounts/answer/185833)
- [Python SMTP 문서](https://docs.python.org/3/library/smtplib.html)

---

**마지막 업데이트**: 2025-10-23
**작성자**: Stock Trading System
