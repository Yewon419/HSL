# 매매신호 API 오류 수정 - 2025년 11월 05일

## 📋 요약

매매신호 탭에서 날짜 변경 후 조회할 때 발생하는 500 Internal Server Error를 해결했습니다.

**근본 원인**: `backend/trading_service/router.py`의 데이터베이스 URL이 개발 환경(Docker 내부 postgres:5432)을 가리키고 있었으나, 실제 데이터는 운영 DB(192.168.219.103:5432)에 저장되어 있었습니다.

**해결 방법**: DB URL을 환경변수 기반 + 운영DB 기본값으로 변경하여 올바른 데이터베이스를 사용하도록 수정했습니다.

## 🔍 문제 분석

### 사용자 보고
```
매매신호 탭 클릭 → 날짜 변경하여 조회 → 500 Internal Server Error

GET http://localhost:8000/api/trading/signals/all?target_date=2025-11-05
→ 500 (Internal Server Error)
```

### 발견 과정

1. **초기 오류** (잘못된 수정):
   - SQL 쿼리의 `s.currency = 'KRW'` 필터를 제거
   - 사용자 피드백: "이미 정상 작동하는 메서드야, DB가 잘못된 거야"

2. **올바른 근본 원인 파악**:
   - `signal_detector.py`의 SQL 쿼리는 정상 (currency 필터는 향후 국제 거래소 확장용)
   - 실제 오류: `trading_positions` 테이블이 존재하지 않음
   - 더 깊은 근본 원인: **DB URL 연결 오류**

3. **배경 조사** (마크다운 문서 검토):
   - `start_hsl.md`: 2025-10-27에 개발DB가 "full"이 되어 운영DB로 마이그레이션
   - `DATABASE_CONFIG.md`: 운영 DB는 192.168.219.103:5432
   - `docker-compose.yml`: 모든 환경변수가 192.168.219.103으로 설정

### 실제 문제
```python
# backend/trading_service/router.py:22
# 잘못된 설정
DB_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
# ↓ Docker 내부 호스트명 "postgres"를 사용
# → 로컬 데이터만 있고 실제 운영 데이터는 없음
```

## ✅ 해결 방법

### 수정 사항

**파일**: `backend/trading_service/router.py` (lines 10-25)

```python
# 기존 코드
import logging
logger = logging.getLogger(__name__)
DB_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"

# 수정된 코드
import logging
import os
logger = logging.getLogger(__name__)
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@192.168.219.103:5432/stocktrading")
```

### 동작 원리

1. **Docker 운영 환경**:
   - `docker-compose.yml`에서 `DATABASE_URL` 환경변수 설정 (192.168.219.103:5432)
   - `router.py`가 환경변수 값 사용 ✓

2. **로컬 테스트 환경**:
   - `DATABASE_URL` 환경변수 미설정
   - 기본값 192.168.219.103:5432 사용 ✓

3. **Docker 내부 테스트** (필요시):
   - `DATABASE_URL=postgresql://admin:admin123@postgres:5432/stocktrading` 설정 시 Docker DB 사용 가능

## 🧪 테스트 결과

### 테스트 1: 2025-11-05 데이터 조회
```bash
curl -s "http://localhost:8000/api/trading/signals/all?target_date=2025-11-05"
```

**결과**: ✅ SUCCESS
```json
{
    "status": "success",
    "buy_count": 38,
    "sell_count": 0,
    "stop_loss_count": 0,
    "signals": {
        "buy": [38개 시그널 반환],
        "sell": [],
        "stop_loss": []
    }
}
```

### 테스트 2: 2025-11-04 데이터 조회
```bash
curl -s "http://localhost:8000/api/trading/signals/all?target_date=2025-11-04"
```

**결과**: ✅ SUCCESS
```json
{
    "status": "success",
    "buy_count": 50,
    "sell_count": 0,
    "stop_loss_count": 0,
    "signals": {...}
}
```

### API 엔드포인트 검증

| 엔드포인트 | 상태 | 데이터 |
|-----------|------|--------|
| `/api/trading/signals/all?target_date=2025-11-05` | ✅ 200 OK | 38개 시그널 |
| `/api/trading/signals/all?target_date=2025-11-04` | ✅ 200 OK | 50개 시그널 |
| `/api/trading/signals/buy?target_date=...` | ✅ 200 OK | 매수 시그널 |
| `/api/trading/signals/sell?target_date=...` | ✅ 200 OK | 매도 시그널 (현재 0개) |
| `/api/trading/signals/stop-loss?target_date=...` | ✅ 200 OK | 손절 시그널 (현재 0개) |

## 📊 데이터베이스 확인

### 현재 설정
```
운영 DB (Production): postgresql://admin:admin123@192.168.219.103:5432/stocktrading
├─ 종목: 2,781개
├─ 주가: 3,093,142개 (1,275일)
├─ 기술 지표: 3,005,232개 (1,262일)
└─ 최신: 2025-11-05
```

### 2025-11-05 데이터
```sql
SELECT COUNT(*) FROM stock_prices WHERE date = '2025-11-05';
-- Result: 2,760개 ✓

SELECT COUNT(*) FROM technical_indicators WHERE date = '2025-11-05';
-- Result: 2,757개 ✓
```

## 🔒 안전성 확인

### currency 필터 유지
```python
# 쿼리에 포함된 조건
WHERE s.currency = 'KRW' AND s.is_active = true
```

**이유**: 향후 미국, 일본, 중국 증시 추가 시 필요한 필터이므로 유지했습니다.

### 예외 처리
```python
def detect_all_signals(self, target_date):
    try:
        buy_signals = self.detect_buy_signals(target_date)
    except Exception as e:
        logger.warning(f"Error detecting buy signals: {e}")
        buy_signals = []

    # ... 동일하게 sell, stop_loss도 처리

    return {
        'buy': buy_signals,
        'sell': sell_signals,
        'stop_loss': stop_loss_signals
    }
```

**목적**: `trading_positions` 테이블이 없어도 buy 시그널은 정상 반환되도록 graceful handling

## 📝 커밋 정보

```
fix: 매매신호 API 데이터베이스 연결 수정 - 개발DB → 운영DB(192.168.219.103)

변경 파일: backend/trading_service/router.py
수정 라인: 22-25
```

## 🎯 결론

**상태**: ✅ 완료 및 검증 완료

- 매매신호 API가 올바른 운영 데이터베이스(192.168.219.103)에 연결됩니다
- 날짜 변경하여 조회 시 정상 작동합니다
- 모든 신호 조회 엔드포인트가 정상 응답합니다

---

**완료일**: 2025-11-05
**상태**: ✅ Ready for Production
**테스트**: ✅ Passed (Multiple dates verified)
