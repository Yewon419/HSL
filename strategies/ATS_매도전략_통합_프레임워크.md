# 자동매매 시스템(ATS) 매도 전략 통합 프레임워크

> **통합 문서**: 자동매매 매도 전략 연구 계획 + APAC 동적 알고리즘 레버리지 축소 프레임워크
> **문서 작성일**: 2025-11-25 (최종 통합)
> **버전**: 2.0

---

## 목차

1. [서론 및 전략적 목표](#1-서론-및-전략적-목표)
2. [3계층 알고리즘 아키텍처](#2-3계층-알고리즘-아키텍처)
3. [매도 신호 유형별 분류](#3-매도-신호-유형별-분류)
4. [동적 손절매 및 리스크 관리](#4-동적-손절매-및-리스크-관리)
5. [시장 레짐 기반 동적 전략 조정](#5-시장-레짐-기반-동적-전략-조정)
6. [포트폴리오 레벨 매도 조건](#6-포트폴리오-레벨-매도-조건)
7. [복수 타임프레임(MTF) 분석](#7-복수-타임프레임mtf-분석)
8. [거래량 기반 매도 신호](#8-거래량-기반-매도-신호)
9. [캔들스틱 패턴 기반 매도](#9-캔들스틱-패턴-기반-매도)
10. [모멘텀 소진 신호](#10-모멘텀-소진-신호)
11. [피보나치 기반 단계적 익절](#11-피보나치-기반-단계적-익절)
12. [한국 시장 특화 로직 (K-Logic)](#12-한국-시장-특화-로직-k-logic)
13. [이벤트 기반 매도](#13-이벤트-기반-매도)
14. [부분 매도 및 단계적 청산](#14-부분-매도-및-단계적-청산)
15. [계층적 우선순위 및 충돌 해결](#15-계층적-우선순위-및-충돌-해결)
16. [백테스팅 및 최적화](#16-백테스팅-및-최적화)
17. [기술적 구현 권고사항](#17-기술적-구현-권고사항)
18. [전략 템플릿](#18-전략-템플릿)
19. [결론](#19-결론)
20. [참고 자료](#참고-자료)

---

## 1. 서론 및 전략적 목표

### 1.1 전략적 필요성

자동매매 시스템(ATS)의 매도 전략은 두 가지 상충하는 목표를 동시에 달성하도록 설계되어야 한다:

| 목표 | 설명 | 핵심 지표 |
|------|------|----------|
| **P0 (자본 보존)** | 최대 낙폭(MDD) 방지, 동적 손절 로직 확보 | MDD 최소화 |
| **P1 (수익 극대화)** | 추세 종료 예측, 효율적 이익 실현 | Sharpe Ratio 개선 |

#### P0: 최대 낙폭(Drawdown) 방지 (리스크 관리)

P0는 시장 변동성에 유연하게 대응하여 계좌의 손실 폭을 최소화하는 동적 손절(Dynamic Stop-Loss) 로직을 확보하는 데 중점을 둔다. ATR 기반의 동적 손절매는 시장의 현재 변동성에 맞춰 손절 거리를 조정함으로써:
- 변동성이 낮은 시장: 불필요한 손절 방지
- 변동성이 높은 시장: 충분한 버퍼 제공으로 조기 청산(Whipsaw) 위험 감소

**연구 결과**: 2×ATR 손절매 사용 시 고정 손절매 대비 최대 낙폭을 **32%까지 감소** 가능

#### P1: 수익 극대화 및 확보 (수익성 최적화)

P1은 감정적 개입 없이 추세의 끝을 예측하고, 추세가 유지되는 동안 이익을 실현하며 Sharpe Ratio를 개선하는 로직 확보를 목표로 한다:
- 추세 종료 신호(Type B)
- 목표 수익 실현 신호(Type C)

### 1.2 P0와 P1의 트레이드오프

- **손절 타이트** → P0 개선, but 잦은 휩쏘우로 P1 저하
- **손절 넓음** → P1 잠재력 유지, but MDD 증가로 P0 훼손
- **해결책**: ATR 승수 N을 시장 상황에 따라 동적 조정

### 1.3 성과 측정 지표

| 지표 | 설명 | 목표 기준 |
|------|------|----------|
| **MDD** | P0 전략의 직접 측정 | ≤ 15% |
| **Profit Factor** | 총 이익 / 총 손실 | ≥ 1.75 (OOS) |
| **Sharpe Ratio** | 리스크 조정 수익률 | 최대화 |

---

## 2. 3계층 알고리즘 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│  제1계층 (시스템 제어) - 최고 우선순위                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • 포트폴리오 VaR/MDD 초과                                 │   │
│  │ • KRX 규제 (VI/사이드카) 발동                             │   │
│  │ • 강제 청산 실행 (모든 하위 신호 Override)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  제2계층 (상황 인식) - 필터/조정자                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • 시장 레짐 분류 (ADX + ATR)                              │   │
│  │ • MTF (다중 시간 프레임) 분석                              │   │
│  │ • ATR 승수 동적 조정                                      │   │
│  │ • 제3계층 신호 유효성 필터링                               │   │
│  └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────────┤
│  제3계층 (실행 신호) - 정밀 타이밍                               │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ • 거래량 소진 (Buying Climax, OBV 다이버전스)              │   │
│  │ • 캔들스틱 패턴 (RSI 필터 통합)                            │   │
│  │ • 피보나치 확장 익절                                       │   │
│  │ • ATR 추적 손절매                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 계층별 상세 역할

| 계층 | 역할 | 핵심 기능 |
|------|------|----------|
| **제1계층** | 시스템 제어 | 자본 보존 최우선, 모든 하위 신호 Override |
| **제2계층** | 상황 인식 | 시장 레짐 분류, ATR 승수 동적 조정 |
| **제3계층** | 실행 신호 | 정밀한 청산 타이밍 포착 |

---

## 3. 매도 신호 유형별 분류

### 3.1 3단계 신호 분류

| Type | 분류 | 목표 | 긴급도 | 주문 유형 |
|------|------|------|--------|----------|
| **Type A** | 리스크 관리 (Hard Stop) | P0 (자본 보존) | 최고 | Stop-Loss → Market Order |
| **Type B** | 추세 종료 (Trend Termination) | P1 (추세 포착) | 높음 | Stop Order / Market Order |
| **Type C** | 목표 수익 실현 (Take-Profit) | P1 (이익 확보) | 중간 | Limit Order |

### 3.2 Type별 상세 조건

#### Type A (리스크 관리) - 최고 우선순위
- ATR 기반 동적 손절
- 고정 손실률 손절 (-3% 등)
- Time Stop (시간 기반 청산)
- 포트폴리오 VaR/MDD 초과
- VI/사이드카 발동

**핵심 원칙**: Type A 신호는 다른 모든 신호에 우선하여 즉각적인 주문 실행 필요

#### Type B (추세 종료)
- Parabolic SAR 반전
- MACD 복합 신호 (히스토그램 수축 + 데드크로스)
- RSI/MACD 다이버전스
- Donchian Channel 하단 이탈
- 거래량 기반 매수 절정 (Climax Top)

#### Type C (수익 목표)
- 목표 R/R 달성 (1:2, 1:3)
- 피보나치 확장 레벨 도달
- 볼린저 밴드 상단 터치 후 중심선 복귀

---

## 4. 동적 손절매 및 리스크 관리

### 4.1 ATR 기반 동적 손절매

#### 기본 공식
```
롱 포지션: SL = Entry Price - (ATR × N)
숏 포지션: SL = Entry Price + (ATR × N)
```

#### ATR 승수(N) 권장값

| 시장 | 권장 N값 | 근거 |
|------|---------|------|
| **KOSPI** | 1.8 ~ 2.3 | 대형주 중심, 낮은 변동성 |
| **KOSDAQ** | 2.5 ~ 3.0 | 중소형주, 높은 변동성 |

#### 동적 조정 원칙
- **조용한 시장**: N = 1.5 ~ 2.0 (타이트한 이익 보호)
- **변동성 높은 시장**: N = 2.5 ~ 3.0 (노이즈 필터링)

#### 로직 설계: 변동성 적응형 손절 가격 갱신

```python
class DynamicATRStopLoss:
    def __init__(self, atr_period=14, base_multiplier=2.0):
        self.atr_period = atr_period
        self.base_multiplier = base_multiplier

    def calculate_stop_loss(self, entry_price, atr_value, position_type='LONG'):
        """ATR 기반 동적 손절가 계산"""
        if position_type == 'LONG':
            return entry_price - (atr_value * self.base_multiplier)
        else:  # SHORT
            return entry_price + (atr_value * self.base_multiplier)

    def update_trailing_stop(self, current_price, current_atr, previous_stop, position_type='LONG'):
        """추적 손절매 갱신 (유리한 방향으로만 이동)"""
        new_stop = self.calculate_stop_loss(current_price, current_atr, position_type)

        if position_type == 'LONG':
            return max(previous_stop, new_stop)  # 손절선은 상향만 가능
        else:
            return min(previous_stop, new_stop)  # 숏은 하향만 가능
```

### 4.2 트레일링 스톱

#### Parabolic SAR 활용
```python
# 가속 계수(AF) 설정
기본 설정: AF 시작 = 0.02, 최대 = 0.20
느린 시장: AF 시작 = 0.015 (민감도 감소)
변동성 높은 시장: AF = 0.025 ~ 0.03 (타이트한 이익 확보)
```

**AF 값과 민감도 관계**:
- AF 값 높음 → PSAR 민감도 상승 → 손절선이 가격에 더 가깝게 이동
- AF 값 낮음 → PSAR 민감도 하락 → 조기 청산 위험 최소화

#### Donchian Channel 활용
- **롱 포지션**: N일 최저가를 TS 기준으로 활용
- **단기 스윙**: N = 10 ~ 20
- **장기 포지션**: N = 50 ~ 100+
- **하단 이탈**: 구조적 추세 붕괴 신호

```python
def donchian_trailing_stop(data, period=20, position_type='LONG'):
    """Donchian Channel 기반 트레일링 스톱"""
    if position_type == 'LONG':
        # 롱 포지션: N일 최저가가 손절선
        return data['low'].rolling(period).min()
    else:
        # 숏 포지션: N일 최고가가 손절선
        return data['high'].rolling(period).max()
```

### 4.3 Time Stop (시간 기반 청산)

```python
class TimeStop:
    def __init__(self, max_holding_days, min_profit_pct=0):
        self.t_max = max_holding_days
        self.p_min = min_profit_pct

    def check(self, position, current_date, current_price):
        """시간 기반 청산 조건 확인"""
        holding_days = (current_date - position.entry_date).days
        pnl_pct = (current_price - position.entry_price) / position.entry_price

        # 최대 보유 기간 내 최소 수익 미달성 시 청산
        if holding_days >= self.t_max and pnl_pct < self.p_min:
            return True, 'time_stop'
        return False, None
```

| 트레이딩 스타일 | T_max | P_min | 목적 |
|---------------|-------|-------|------|
| 단타 | 1~2일 | 0% | 빠른 자금 회전 |
| 스윙 | 5일 | 0% | 중기 추세 포착 |
| 포지션 | 20일 | 2% | 장기 추세 추종 |

---

## 5. 시장 레짐 기반 동적 전략 조정

### 5.1 레짐 정의 지표

#### ADX (Average Directional Index)
- **ADX ≥ 25**: 유의미한 추세 존재
- **ADX < 20**: 횡보/약세장, 거짓 신호 위험 증가

#### ATR (Average True Range)
- 변동성 측정
- T3 ATR 활용 시 변동성 변화에 더 빠르게 반응

### 5.2 레짐별 파라미터 매핑

| 시장 레짐 | ADX 조건 | 변동성 | 주요 전략 | ATR 승수 |
|---------|---------|-------|---------|---------|
| **강한 추세** | ADX ≥ 25 | 보통/낮음 | ATR 추적 손절 | 2.5× ~ 3.0× |
| **횡보/약세** | ADX < 20 | 낮음/수렴 | 타이트 손절, 부분 익절 | 1.5× ~ 2.0× |
| **변동성 확장** | ADX ≥ 25 | 높음/확장 | 넓은 손절, 포트폴리오 점검 | 3.0× 이상 |

### 5.3 레짐 전환 시 자동 조정

```python
class MarketRegimeManager:
    def __init__(self):
        self.current_regime = None

    def classify_regime(self, adx_value, atr_percentile):
        """시장 레짐 분류"""
        if adx_value >= 25:
            if atr_percentile > 80:  # 상위 20% 변동성
                return 'VOLATILE'
            else:
                return 'TRENDING'
        else:
            return 'RANGING'

    def adjust_parameters(self, regime):
        """레짐에 따른 파라미터 조정"""
        params = {
            'VOLATILE': {
                'atr_multiplier': 3.0,
                'volume_threshold': 3.0,  # ADVR 기준 상향
                'max_leverage': 0.5       # 레버리지 축소
            },
            'TRENDING': {
                'atr_multiplier': 2.5,
                'volume_threshold': 2.0,
                'max_leverage': 1.0
            },
            'RANGING': {
                'atr_multiplier': 1.5,
                'volume_threshold': 2.0,
                'max_leverage': 0.7
            }
        }
        return params.get(regime, params['RANGING'])
```

**핵심 원칙**: ADX 레짐이 ATR 승수를 결정하는 인과적 조정자 역할 수행

---

## 6. 포트폴리오 레벨 매도 조건

### 6.1 VaR 기반 레버리지 축소

```python
class VaRMonitor:
    def __init__(self, var_limit=0.03):  # 99% 1일 VaR 3%
        self.var_limit = var_limit
        self.exceedance_count = 0

    def check(self, portfolio_pnl, calculated_var):
        """VaR 초과 모니터링"""
        if abs(portfolio_pnl) > calculated_var:
            self.exceedance_count += 1

            # 연속 VaR 초과 시 자동 디레버리징
            if self.exceedance_count >= 2:
                return 'ADL_TRIGGER'
        else:
            self.exceedance_count = 0

        return None
```

### 6.2 상관관계 리스크 관리

| 조건 | 임계값 | 대응 |
|-----|-------|------|
| 종목간 상관계수 | > 0.7 | 고상관 종목 중 약세 종목 우선 청산 |
| 섹터 집중도 | > 40% | 해당 섹터 내 저성과 종목 리밸런싱 |
| 포트폴리오 VaR 95% | > 5% | 고베타 종목 우선 청산 |

**상관관계 리스크의 핵심**: 개별 종목 손실보다 **상관성 높은 자산들의 동시 손실(Tail Risk)**이 더 위험

### 6.3 MDD 기반 강제 청산

| 기간 | 손실 한도 | 대응 |
|-----|---------|------|
| 일일 | -3% | 신규 거래 중단 |
| 주간 | -8% | 공격적 전략 중단 |
| 월간 | -15% | 전체 포지션 50% 축소 |

---

## 7. 복수 타임프레임(MTF) 분석

### 7.1 MTF 계층 구조

| 타임프레임 | 역할 | 지표 | 기능 |
|----------|------|------|------|
| **HTF** (주간/일봉) | Context | 200 EMA | 장기 추세 방향 설정 |
| **MTF** (4H/1H) | Confirmation | RSI, MACD | 중간 모멘텀 확인 |
| **LTF** (15분/5분) | Execution | 캔들스틱, 지지선 | 정밀 청산 타이밍 |

### 7.2 우위 원칙(Dominance Principle) 기반 신호 충돌 해결

```
HTF 추세 방향 > MTF 확인 신호 > LTF 실행 신호
```

#### 신호 해석 규칙
| HTF 상태 | LTF 약세 신호 | 해석 |
|---------|-------------|------|
| 강세 (200 EMA 위) | 발생 | 부분 익절 또는 트레일링 타이트 (전량 청산 X) |
| 약세 (200 EMA 아래) | 발생 | 전량 청산 신호로 간주 |

### 7.3 신호 가중치

| 신호 | 가중치 | 예시 |
|-----|-------|------|
| HTF 200 EMA 돌파 | 5 | 일봉 200 EMA 하향 돌파 |
| MTF MACD 데드크로스 | 3 | 4시간봉 MACD 데드크로스 |
| LTF 캔들스틱 패턴 | 1 | 15분봉 Shooting Star |

**청산 규모 결정**: 총 가중치 합산 점수에 따라 부분/전체 청산 결정

---

## 8. 거래량 기반 매도 신호

### 8.1 매수 절정 (Buying Climax)

```python
def detect_buying_climax(data, lookback=20, volume_multiplier=2.0, price_threshold=0.03):
    """매수 절정 감지"""
    avg_volume = data['volume'].rolling(lookback).mean()
    volume_ratio = data['volume'] / avg_volume
    price_change = data['close'].pct_change()

    # 조건: 거래량 급증 + 가격 급등 + 저항 근처
    climax = (volume_ratio > volume_multiplier) & (price_change > price_threshold)

    return climax
```

| 조건 | 임계값 | 해석 |
|-----|-------|------|
| 거래량 | > 20일 평균 × 2~3배 | 극단적 거래량 급증 |
| 가격 | 급등 + 저항 근처 | 수요 고갈 |
| **결과** | **강력한 매도 신호** | 급격한 반전 예고 |

### 8.2 거래량-가격 다이버전스

| 유형 | 조건 | 해석 |
|-----|------|------|
| **OBV 다이버전스** | 가격↑ but OBV↓ | 추세 건전성 약화, 기관 유입 없음 |
| **거래량 고갈** | 가격↑ but 거래량 감소 | 추세 약화 |

```python
def detect_obv_divergence(price, obv, lookback=14):
    """OBV 약세 다이버전스 감지"""
    price_highs = price.rolling(lookback).max() == price
    obv_highs = obv.rolling(lookback).max() == obv

    # 가격 신고가 but OBV 신고가 아님 = 약세 다이버전스
    bearish_div = price_highs & ~obv_highs

    return bearish_div
```

---

## 9. 캔들스틱 패턴 기반 매도

### 9.1 주요 약세 반전 패턴

| 패턴 | 구조적 조건 | 신뢰도 |
|-----|----------|-------|
| **Shooting Star** | 상단 꼬리 ≥ 몸통 × 2배 | 높음 |
| **Bearish Engulfing** | 음봉이 전일 양봉 완전 포함 | 높음 |
| **Dark Cloud Cover** | 갭업 후 전일 몸통 50% 이하 마감 | 중간 |
| **Evening Star** | 3일 패턴 (양봉-도지-음봉) | 높음 |
| **Hanging Man** | 하단 꼬리 ≥ 몸통 × 2배 (상승 후) | 중간 |

### 9.2 RSI 필터 통합

```python
def confirm_candlestick_signal(pattern, rsi, rsi_prev):
    """캔들스틱 패턴 + RSI 필터 확증"""
    # RSI 과매수 구간에서 약세 패턴 발생 시 신뢰도 상승
    if pattern == 'BEARISH' and rsi > 70:
        return 'HIGH_CONFIDENCE'

    # RSI가 70 이하로 하향 돌파 시점에 패턴 발생
    if pattern == 'BEARISH' and rsi < 70 and rsi_prev >= 70:
        return 'CONFIRMED_SELL'

    return 'MONITOR'
```

### 9.3 후속 확증

- **필수 조건**: 패턴 발생 후 다음 캔들이 패턴의 저점 아래에서 마감
- **확증 없이 패턴만으로는 매도 신호 발동하지 않음**

---

## 10. 모멘텀 소진 신호

### 10.1 MACD 기반 신호

#### 히스토그램 수축 (Rolling Over)
```python
def detect_macd_rollover(macd_hist):
    """MACD 히스토그램 수축 감지"""
    # 양의 영역에서 고점 낮추며 수축
    in_positive = macd_hist > 0
    decreasing = macd_hist < macd_hist.shift(1)

    rollover = in_positive & decreasing
    return rollover
```

#### 데드 크로스
- MACD선이 시그널선 하향 돌파
- **0선 부근 또는 양수 영역**에서 발생 시 강한 매도 압력

### 10.2 하락 다이버전스 (Bearish Divergence)

```
가격: Higher High (신고가)
RSI/MACD: Lower High (고점 하락)
= 약세 다이버전스 (모멘텀 부족)
```

### 10.3 복합 신호 조합 (Type B 최고 우선순위)

```python
def momentum_exhaustion_signal(data):
    """복합 모멘텀 소진 신호"""
    conditions = [
        detect_macd_rollover(data['macd_hist']),
        detect_bearish_divergence(data['close'], data['rsi']),
        data['rsi'] < 70  # RSI가 70 이하로 하향 돌파
    ]

    if all(conditions):
        return 'HIGH_PRIORITY_SELL'
    elif sum(conditions) >= 2:
        return 'PARTIAL_EXIT'

    return None
```

---

## 11. 피보나치 기반 단계적 익절

### 11.1 피보나치 확장 레벨

| 레벨 | 시장 해석 | 청산 행동 | 리스크 조정 |
|-----|---------|---------|-----------|
| **127.2%** | 초기 저항/1차 목표 | 25~33% 청산 | **손절매를 본절(BE)로 이동** |
| **161.8%** | 주요 목표 (T2) | 50% 청산 (누적 75%) | ATR 트레일링 타이트 |
| **261.8%** | 추세 소진/최대 목표 | 전량 청산 | 거래량 소진 신호 확인 |

### 11.2 리스크 제로화 메커니즘

```python
def fibonacci_phased_exit(position, current_price, fib_levels):
    """피보나치 단계적 익절"""
    pnl_pct = (current_price - position.entry_price) / position.entry_price

    if pnl_pct >= fib_levels['127.2']:
        # 1차 익절: 25~33% 청산
        exit_qty = position.quantity * 0.30
        # 핵심: 손절매를 본절로 이동 → 리스크 제로화
        position.stop_loss = position.entry_price
        return exit_qty, 'PARTIAL_EXIT_T1'

    if pnl_pct >= fib_levels['161.8']:
        # 2차 익절: 50% 청산
        exit_qty = position.quantity * 0.50
        # ATR 트레일링 타이트하게
        position.trailing_atr_mult = 1.5
        return exit_qty, 'PARTIAL_EXIT_T2'

    if pnl_pct >= fib_levels['261.8']:
        # 전량 청산
        return position.quantity, 'FULL_EXIT_T3'

    return 0, None
```

### 11.3 스윙 감지 알고리즘

- **앵커 포인트 자동 선정**: 주관성 배제
- **확인 봉 수 및 최소 스윙 백분율** 임계값 사용
- 유효한 피벗 포인트 자동 식별

---

## 12. 한국 시장 특화 로직 (K-Logic)

### 12.1 VI (변동성 완화장치) 대응

#### 발동 조건
- 직전 체결가 대비 3% 또는 10% 변동
- 발동 시 2분간 단일가 매매 전환

#### 알고리즘 대응
```python
def handle_vi_trigger(position, vi_event):
    """VI 발동 시 대응 로직"""
    # 1. 시장가 주문 즉시 중단
    cancel_market_orders()

    # 2. 단일가 매매 시간 동안 긴급 청산 전략
    if vi_event.direction == 'DOWN' and position.side == 'LONG':
        # 추적 지정가 주문으로 전환
        limit_price = calculate_trailing_limit(
            current_price=vi_event.trigger_price,
            offset_pct=0.02  # 2% 오프셋
        )
        submit_limit_order(position, limit_price, 'SELL')
```

### 12.2 사이드카 대응

#### 발동 조건
- KOSPI 200 선물 5% 이상 변동
- 프로그램 매매 효력 5분간 정지
- 장 마감 40분 전 비활성화

#### 알고리즘 대응
```python
def handle_sidecar(position):
    """사이드카 발동 시 대응"""
    # 1. 프로그램 매매 채널 주문 취소
    cancel_program_orders()

    # 2. 비프로그램 채널 또는 고정 리밋 전략 전환
    # 5분 정지 동안 준비
    prepare_non_program_exit(position)
```

### 12.3 장 마감 동시호가 (Random End)

- **시간**: 15:20~15:30
- **특징**: 종료 시점 무작위 연장 가능 (RE 메커니즘)
- **대응**: 종료 1분 전까지 적극적 주문 수정, 체결 우선순위 확보

### 12.4 K-Factor (외국인 집중 매도)

```python
def detect_k_factor(foreign_flow, threshold=-500):  # 억원 단위
    """K-Factor 감지: 외국인 집중 매도 흐름"""
    if foreign_flow < threshold:
        return 'K_FACTOR_ACTIVE'
    return None

def apply_k_factor_rules(k_factor_status, order_type):
    """K-Factor 활성 시 주문 유형 조정"""
    if k_factor_status == 'K_FACTOR_ACTIVE':
        # 시장가 → 보수적 지정가 전환
        if order_type == 'MARKET':
            return 'CONSERVATIVE_LIMIT'
        # 포지션 선제 축소
        return 'REDUCE_POSITION'
    return order_type
```

---

## 13. 이벤트 기반 매도

### 13.1 어닝 발표 선제적 전략

| 지표 | 조건 | 대응 |
|-----|------|------|
| **PAR (Pre-Announcement Return)** | 비정상적으로 높음 | 발표 전 청산 또는 숏 진입 |
| **발표일 변경 (ΔD < 0)** | 발표일 앞당김 | 포지션 규모 축소 |

### 13.2 거시 경제 이벤트

| 이벤트 | 영향 | 대응 |
|-------|------|------|
| **금리 인상** | 고성장 기술주 밸류에이션 압력 | 성장주 레버리지 축소 태그 할당 |
| **자산 매각 개시** | 유동성 축소 | 레버리지 포트폴리오 선제 축소 |

### 13.3 뉴스 센티멘트

```python
def sentiment_based_exit(sentiment_score, threshold=-0.3):
    """센티멘트 기반 청산 신호"""
    # Negativity, Uncertainty, FinancialDown 지표 급증 시
    if sentiment_score < threshold:
        return 'PARTIAL_EXIT_SIGNAL'
    return None
```

---

## 14. 부분 매도 및 단계적 청산

### 14.1 50%/50% 전략

```
1차 익절 (50%):
  - 조건: R/R 1:2 또는 1:3 달성
  - 유형: Type C 신호
  - 목적: 초기 투자 위험 회수

2차 익절 (50%):
  - 조건: Parabolic SAR 또는 Donchian Channel 트레일링
  - 유형: Type B 신호
  - 목적: 추세 끝까지 추종
```

### 14.2 OR 조건 모듈 (25% 부분 청산)

```python
def partial_exit_25_percent(data):
    """일시적 과열 시 25% 부분 청산"""
    conditions = [
        data['rsi'] >= 70,                    # RSI 과매수
        data['close'] >= data['bb_upper'],    # BB 상단 터치
    ]

    # OR 조건: 하나라도 만족 시 25% 청산
    if any(conditions):
        return 0.25, 'PARTIAL_OVERHEAT'

    return 0, None
```

### 14.3 피보나치 기반 단계적 청산

| 단계 | 레벨 | 청산 비율 | 누적 청산 |
|-----|------|---------|---------|
| T1 | 127.2% | 25~33% | 25~33% |
| T2 | 161.8% | 50% | 75~83% |
| T3 | 261.8% | 잔여 전량 | 100% |

---

## 15. 계층적 우선순위 및 충돌 해결

### 15.1 4단계 매도 실행 프로토콜

| Level | 트리거 | 행동 | Override |
|-------|-------|------|----------|
| **1 (자본 보존)** | VaR/MDD 초과, VI/사이드카 | 강제 청산 | 모든 신호 무시 |
| **2 (매크로)** | K-Factor, 센티멘트 급증 | 부분 디레버리징, ATR 축소 | Level 3,4 조정 |
| **3 (구조적)** | HTF 200 EMA 돌파, MTF 반전 확인 | 높은 확신 청산 | Level 4 압도 |
| **4 (집행)** | 거래량/캔들/피보나치/ATR | 정밀 실행 | 최종 타이밍 |

### 15.2 Type A 신호 충돌 해결

#### 원칙: **가장 보수적인 조건 선택**

| 상황 | 신호 1 | 신호 2 | 선택 로직 | 결과 |
|-----|-------|-------|---------|------|
| 롱 포지션 | ATR SL $95.00 | 고정% SL $94.50 | 가장 높은 가격 | $95.00 |
| 롱 포지션 | PSAR $96.50 | ATR SL $96.00 | 가장 높은 가격 | $96.50 |
| Time Stop | 발동 | ATR SL $95.00 | 비가격 조건 우선 | 즉시 시장가 청산 |

### 15.3 AND/OR 프레임워크

```python
# 사용자 정의 로직 조합
sell_condition = (
    (SL_1 OR SL_2) AND TP_1
)

# 시스템 제약: Type A는 항상 독립적 OR 조건
# Type A에 AND로 Type C 결합 금지 (손절 지연 방지)
```

---

## 16. 백테스팅 및 최적화

### 16.1 Walk-Forward Analysis (WFA)

```
1. 데이터 분할: 히스토리를 여러 구간으로 분할
2. 최적화 단계 (In-Sample): 첫 번째 구간에서 파라미터 최적화
3. 테스트 단계 (Out-of-Sample): 다음 구간에서 성능 테스트
4. 워크 포워드: 시간 순서대로 반복
```

### 16.2 목표 함수

```python
def objective_function(params, data):
    """WFA 최적화 목표 함수"""
    result = backtest(data, params)

    # P0 제약: MDD ≤ 15%
    if result.mdd > 0.15:
        return float('-inf')

    # P1 최적화: Profit Factor 최대화
    return result.profit_factor
```

### 16.3 ATR 파라미터 최적화

| 트레이딩 스타일 | ATR 기간 | ATR 승수 |
|---------------|---------|---------|
| 단기 (1-5일) | 5-10일 | 1.5-2.0× |
| 스윙 (5-20일) | 14-21일 | 2.0-2.5× |
| 포지션 (20일+) | 20-30일 | 2.5-3.0× |

### 16.4 K-Logic 스트레스 테스트

- VI/사이드카 발동 이력 기준 테스트
- 5분 정지 시 주문 변경 및 전환 성공 여부 검증
- 규제 환경에서 시스템 실행 로직 검증

---

## 17. 기술적 구현 권고사항

### 17.1 실시간 데이터 무결성

| 항목 | 요구사항 |
|-----|---------|
| **데이터 소스** | KRX 실시간 피드 또는 승인 벤더 |
| **업데이트 주기** | sub-100ms (고성능: sub-20ms) |
| **시간 동기화** | 동적 변수와 시장 가격 간 동기화 필수 |

### 17.2 주문 유형 선택 기준

| Exit Type | 목표 | 주문 유형 | 이유 |
|-----------|------|---------|------|
| **Type A** | 실행 확실성 (P0) | Stop-Loss → Market | 체결 보장 |
| **Type C** | 가격 정확성 (P1) | Limit Order | 슬리피지 방지 |

### 17.3 슬리피지 및 지연 관리

```python
class LatencyManager:
    def __init__(self, max_latency_ms=100):
        self.max_latency = max_latency_ms

    def check_data_freshness(self, data_timestamp):
        """데이터 신선도 확인"""
        latency = time.now() - data_timestamp
        if latency > self.max_latency:
            logger.warning(f"Stale data detected: {latency}ms")
            return False
        return True
```

### 17.4 가격 무결성 보장

- 동적 지표 계산에 사용된 가격이 체결 불가능한 과거 가격이면 'Stale Value' 발생
- Type A 신호 발동 시 오래된 값 기반 주문은 심각한 슬리피지 초래
- **계산 시점의 시장 가격과 동적 변수의 시간 동기화(Time Synchronization) 필수**

---

## 18. 전략 템플릿

### 18.1 템플릿 1: ATR 기반 Risk-Off 전략 (P0 집중)

```python
class ATRRiskOffStrategy:
    """
    목표: 최소 MDD 및 높은 Profit Factor
    """
    def __init__(self):
        self.atr_multiplier = 2.0
        self.rr_target = 2.0  # 1:2 R/R
        self.partial_exit_pct = 0.50

    def generate_signals(self, data, position):
        signals = []

        # Type A: ATR 기반 하드 손절
        atr_stop = position.entry_price - (data['atr'] * self.atr_multiplier)
        if data['close'] <= atr_stop:
            signals.append(('FULL_EXIT', 'ATR_STOP'))

        # Type C: R/R 목표 50% 청산
        target_price = position.entry_price + (
            (position.entry_price - atr_stop) * self.rr_target
        )
        if data['close'] >= target_price:
            signals.append(('PARTIAL_EXIT', self.partial_exit_pct, 'RR_TARGET'))

        # 나머지 50%: ATR Trailing Stop
        # ... trailing logic

        return signals
```

### 18.2 템플릿 2: 모멘텀 소진 하이브리드 전략 (P1 집중)

```python
class MomentumExhaustionStrategy:
    """
    목표: 추세 전환 직전 최고점 청산으로 Sharpe Ratio 극대화
    """
    def generate_signals(self, data, position):
        signals = []

        # Type A: 기본 ATR 손절 (P0 유지)
        # ... ATR stop logic

        # Type B: 복합 모멘텀 소진 신호
        macd_rollover = detect_macd_rollover(data)
        rsi_divergence = detect_rsi_divergence(data)
        rsi_below_70 = data['rsi'] < 70 and data['rsi'].shift(1) >= 70

        if macd_rollover and rsi_divergence and rsi_below_70:
            signals.append(('FULL_EXIT', 'MOMENTUM_EXHAUSTION'))

        return signals
```

### 18.3 템플릿 3: Donchian 추세 추종 전략 (로버스트 집중)

```python
class DonchianTrendStrategy:
    """
    목표: 장기 추세 최대 포착, 총 수익률 극대화
    """
    def __init__(self):
        self.atr_multiplier = 3.0  # 넓은 손절 (KOSDAQ 적합)
        self.donchian_period = 20
        self.time_stop_days = 5

    def generate_signals(self, data, position):
        signals = []

        # Type A: 넓은 ATR 손절
        # ... wide ATR stop logic

        # Type B: Donchian Channel 하단 이탈
        dc_lower = data['low'].rolling(self.donchian_period).min()
        if data['close'] < dc_lower:
            signals.append(('FULL_EXIT', 'DONCHIAN_BREAK'))

        # Time Stop: 5일 미수익 시 청산
        holding_days = (data.index[-1] - position.entry_date).days
        if holding_days >= self.time_stop_days:
            pnl_pct = (data['close'] - position.entry_price) / position.entry_price
            if pnl_pct <= 0:
                signals.append(('FULL_EXIT', 'TIME_STOP'))

        return signals
```

---

## 19. 결론

### 19.1 핵심 원칙 요약

```
1. 계층적 우선순위: 규제 > 포트폴리오 > 레짐 > 기술 신호
2. 동적 적응: 시장 레짐에 따른 파라미터 자동 조정
3. 리스크 제로화: 피보나치 127.2% 도달 시 손절매를 본절로 이동
4. MTF 정렬: HTF 추세 방향이 LTF 신호 유효성 결정
5. K-Logic 준수: 한국 시장 미시구조 (VI/사이드카/RE) 적극 반영
```

### 19.2 구현 체크리스트

- [ ] 3계층 알고리즘 아키텍처 구현
- [ ] ADX + ATR 기반 레짐 분류 로직
- [ ] MTF 분석 및 우위 원칙 적용
- [ ] 거래량 기반 매수 절정 감지
- [ ] 캔들스틱 패턴 + RSI 필터
- [ ] 피보나치 단계적 익절 로직
- [ ] VI/사이드카 대응 프로토콜
- [ ] K-Factor 감지 및 대응
- [ ] VaR/MDD 기반 자동 디레버리징
- [ ] WFA 기반 파라미터 최적화
- [ ] K-Logic 스트레스 테스트
- [ ] 슬리피지/지연 관리 모듈
- [ ] 실시간 데이터 무결성 검증

### 19.3 추가 연구 제언

1. **ATR 기간 최적화**: 단기 5-10일, 스윙 14-21일 세분화
2. **피벗 탐지 알고리즘 개선**: 객관적 앵커 포인트 자동 선정
3. **저지연 인프라**: KRX 실시간 데이터 피드 확보
4. **규제 정보 실시간 처리**: VI/사이드카 발동 즉시 감지
5. **센티멘트 분석 고도화**: 뉴스 기반 선행 지표 개발

---

## 참고 자료

### ATR 및 손절매
- LuxAlgo: How to Use ATR for Volatility-Based Stop-Losses
- LuxAlgo: 5 ATR Stop-Loss Strategies for Risk Control
- Markets.com: Optimise Stop Losses Using The ATR Indicator

### Parabolic SAR
- Alchemy Markets: Parabolic SAR Comprehensive Trading Guide
- QuantInsti: Parabolic SAR Formula, Calculation, and Python Code

### Donchian Channel
- Investopedia: Understanding Donchian Channels
- TrendSpider: Donchian Channel Trading Strategies

### MTF 분석
- GO Markets: Multi-Timeframe Analysis: A Practical Systems Approach
- OSL: How to Find Entry-Exit Points Using Multiple Time Frame Analysis

### 거래량 분석
- LuxAlgo: Volume Spikes: Timing Trades with Precision
- LuxAlgo: Volume Divergence in Bullish Trends

### 캔들스틱
- TrendSpider: Candlestick Pattern Trading Strategies
- IBKR: Bearish Candlestick Patterns Explained

### 피보나치
- LuxAlgo: A Basic Guide to Fibonacci Extensions
- TrendSpider: What Are Fibonacci Extensions

### 한국 시장
- Morgan Stanley: Asia Swap Overview
- FSC: SFC Imposes Penalty Surcharge for Market Disturbance

### 리스크 관리
- Investopedia: How to Calculate Value at Risk (VaR)
- AlgoBulls: Risk Management in Algorithmic Trading
- Interactive Brokers: Walk-Forward Analysis

### 센티멘트 분석
- Acuity Trading: Trading with Sentiment
- Magnifi: A Deep Dive into AI Stock Market Sentiment Analysis

### 어닝 전략
- Wall Street Horizon: Pre-earnings Announcement Strategies
- TrendSpider: How to Trade Earnings Announcements With Technical Analysis

---

*문서 통합일: 2025-11-25*
*버전: 2.0 (3개 문서 통합)*
*원본 문서:*
- *자동매매 매도 전략 연구 계획.pdf*
- *ATS_매도전략_통합_프레임워크.md (v1.0)*
- *매도 전략 연구 보충 요청.pdf*
