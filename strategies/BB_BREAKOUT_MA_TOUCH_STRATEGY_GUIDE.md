# 볼린저밴드 하단돌파 후 이동평균선 터치 전략 가이드

## 📊 전략 개요

이 전략은 주가가 볼린저밴드 하단선을 하향 돌파한 후, 다시 상승하여 이동평균선을 터치하거나 돌파하는 패턴을 감지하는 반등 매매 전략입니다.

## 🎯 전략 로직

### 1. 패턴 감지 조건
- **1단계**: 주가가 볼린저밴드 하단선을 하향 돌파
- **2단계**: 이후 주가가 반등하여 이동평균선(기본 20일)에 터치 또는 돌파
- **3단계**: 상승 모멘텀 확인 (현재가 > 전일가)

### 2. 기술적 배경
- **볼린저밴드 하단 돌파**: 과매도 상태 진입 신호
- **이동평균선 터치**: 기술적 저항선 돌파 시도
- **상승 모멘텀**: 매수 세력 유입 확인

## ⚙️ 전략 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| ma_period | 20 | 이동평균 기간 (일) |
| lookback_days | 5 | 패턴 확인 기간 (일) |
| bb_period | 20 | 볼린저밴드 기간 |
| bb_std | 2.0 | 볼린저밴드 표준편차 |
| ma_tolerance | 1% | 이동평균선 터치 허용 오차 |

## 🚀 사용 방법

### 1. 웹 인터페이스 사용

1. **스크리닝 API 접속**
   ```
   http://localhost:8000
   ```

2. **조건 설정**
   - 지표: `BB` (볼린저밴드) 선택
   - 조건: `볼린저밴드 하단돌파 → 이평선터치` 선택
   - 값 1: 이동평균 기간 (예: 20)
   - 조회 기간: 패턴 확인 기간 (예: 5)

3. **스크리닝 실행**
   - 분석 기간 설정
   - `스크리닝 실행` 버튼 클릭

### 2. 파이썬 코드 사용

```python
from strategies.bb_breakout_ma_touch_strategy import BollingerBreakoutMATouchStrategy

# 전략 인스턴스 생성
strategy = BollingerBreakoutMATouchStrategy()

# 스크리닝 실행
screening_result = strategy.run_screening(
    start_date='2025-09-01',
    end_date='2025-09-24',
    ma_period=20,      # 20일 이동평균
    lookback_days=5    # 5일 패턴 확인
)

# 결과 확인
print(f"발견된 종목 수: {len(screening_result)}")
print(screening_result[['ticker', 'company_name', 'current_price']].head())
```

### 3. 직접 실행

```bash
cd stock-trading-system/strategies
python bb_breakout_ma_touch_strategy.py
```

## 📈 백테스트 결과 해석

### 포트폴리오 성과 지표
- **총 수익률**: 전체 기간 수익률
- **연환산 수익률**: 연간 기준 수익률
- **변동성**: 수익률 표준편차
- **샤프 비율**: 위험 대비 수익 비율
- **최대 낙폭**: 최대 손실 구간

### 스크리닝 결과 필드
| 필드명 | 설명 |
|--------|------|
| ticker | 종목 코드 |
| company_name | 회사명 |
| current_price | 현재가 |
| bb_lower | 볼린저밴드 하단선 |
| bb_middle | 볼린저밴드 중간선 |
| sma_20 | 20일 이동평균 |
| bb_lower_distance_pct | BB 하단 대비 거리(%) |
| ma_distance_pct | MA 대비 거리(%) |

## 🎛️ 전략 최적화

### 1. 파라미터 조정
```python
# 단기 전략 (민감도 높음)
strategy.run_screening(ma_period=10, lookback_days=3)

# 장기 전략 (안정성 높음)
strategy.run_screening(ma_period=50, lookback_days=10)
```

### 2. 추가 필터링
```python
# 거래량 조건 추가 (별도 구현 필요)
conditions = [
    {
        'indicator': 'BB',
        'condition': 'bb_breakout_ma_touch',
        'ma_period': 20,
        'lookback_days': 5
    },
    {
        'indicator': 'OBV',  # 거래량 지표
        'condition': 'above',
        'value': 0  # 거래량 증가 확인
    }
]
```

## ⚠️ 리스크 관리

### 1. 손절 조건
- 볼린저밴드 하단선 재돌파 시 손절
- 이동평균선 하향 이탈 시 손절
- 일정 손실률 도달 시 손절 (-5% 권장)

### 2. 익절 조건
- 볼린저밴드 상단선 도달 시 부분 익절
- 이동평균선 상승 기울기 둔화 시 익절
- 일정 수익률 도달 시 익절 (+10% 권장)

### 3. 포지션 관리
- 단일 종목 비중 제한 (최대 20%)
- 동시 보유 종목 수 제한 (최대 5-10개)
- 총 투자 비중 제한 (최대 80%)

## 📊 성과 분석

### 백테스트 예시 (2025년 9월)
```
📊 볼린저밴드 하단돌파 + 이평선터치 전략 결과
============================================================

🎯 스크리닝 결과: 12개 종목
----------------------------------------
005930   | 삼성전자          |   71500원
         └ BB하단대비: +2.15% | MA대비: +0.85%

000660   | SK하이닉스        |  131000원
         └ BB하단대비: +1.80% | MA대비: +1.20%

💼 포트폴리오 성과
------------------------------
총 수익률: +5.67%
연환산 수익률: +12.34%
변동성: 15.80%
샤프 비율: 0.78
최대 낙폭: -3.20%
```

## 🔧 문제 해결

### 일반적인 오류
1. **데이터베이스 연결 실패**
   - Docker 컨테이너 상태 확인
   - 데이터베이스 서비스 재시작

2. **지표 데이터 부족**
   - 지표 계산 스크립트 실행
   - 주가 데이터 업데이트

3. **스크리닝 결과 없음**
   - 분석 기간 확장
   - 파라미터 조정 (ma_period, lookback_days)

### 디버그 모드
```python
import logging
logging.basicConfig(level=logging.DEBUG)

strategy = BollingerBreakoutMATouchStrategy()
result = strategy.run_screening(...)
```

## 📝 추가 개발 아이디어

1. **다중 시간프레임 분석**
   - 일봉, 주봉, 월봉 동시 분석

2. **변동성 필터**
   - ATR 기반 변동성 조건 추가

3. **시장 상황 필터**
   - 코스피/코스닥 지수 추세 고려

4. **동적 파라미터**
   - 시장 변동성에 따른 파라미터 자동 조정

## 📞 지원

문의사항이나 개선 제안이 있으시면 다음을 참고하세요:
- 시스템 로그: `docker logs stock-backend`
- API 문서: `http://localhost:8000/docs`
- 모니터링 대시보드: `http://localhost:3000`

---

**면책조항**: 이 전략은 교육 및 연구 목적으로 제공됩니다. 실제 투자 시에는 충분한 검토와 위험 관리가 필요합니다.