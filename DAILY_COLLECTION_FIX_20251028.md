# 2025-10-28 주가 수집 개선 작업

**작업 일시**: 2025-10-28 13:00 KST
**작업자**: Claude Code
**상태**: 진행 중

---

## 📋 작업 개요

### 현재 문제점

1. **데이터베이스 연결 오류 (FIXED)** ✅
   - Airflow가 Docker 로컬 postgres 연결 → 운영DB(192.168.219.103) 연결로 수정
   - `common_functions.py` line 24: `host: "postgres"` → `host: "192.168.219.103"`

2. **종목 수 부족 (IN PROGRESS)** 🔴
   - **현재**: 958개만 수집 (KOSPI만)
   - **목표**: 2,759개 모두 수집 (KOSPI + KOSDAQ + 기타)
   - **원인**: `get_market_ticker_list()`가 기본값으로 KOSPI만 반환

3. **TimescaleDB 제약 조건 오류 (BLOCKED)** 🔴
   - Stock prices 저장 시 `dimension_slice_pkey` 충돌
   - 시스템이 완전히 고장난 상태는 아니지만, 주가 저장 불가

### 정상 작동 항목

| 항목 | 상태 | 비고 |
|------|------|------|
| 데이터베이스 연결 | ✅ 정상 | 192.168.219.103 운영DB 연결됨 |
| pykrx API 수집 | ✅ 정상 | 955+개 종목의 OHLCV 데이터 수집됨 |
| 지수 데이터 저장 | ✅ 정상 | KOSPI, KOSDAQ 2개 지수 저장됨 |
| 컬렉션 로그 기록 | ✅ 정상 | 수집 상태를 collection_log에 기록 |

---

## 🔍 955개인 이유 분석

### pykrx 시장별 종목 수

```
KOSPI (유가증권시장)  : 958개
KOSDAQ (코스닥)       : 1,801개
---
합계                  : 2,759개
```

### 현재 코드의 문제

```python
# 문제 코드 - common_functions.py line ~65
tickers = pykrx_stock.get_market_ticker_list(date=date_str)
# 이 코드는 기본값으로 KOSPI만 반환!
```

### 왜 KOSDAQ이 안 수집되나?

**pykrx 함수 서명:**
```python
get_market_ticker_list(market="KOSPI", date=None)
# market 파라미터 기본값이 "KOSPI"
```

따라서 KOSDAQ을 명시적으로 지정하지 않으면 KOSPI만 가져온다!

---

## 💡 해결 방안 5가지

### **방법 1: 마켓별 별도 수집 (권장)** ⭐⭐⭐⭐⭐

**장점**: 구현 간단, 명확한 제어, 재시도 전략 개별 적용 가능
**단점**: 수집 로직이 약간 길어짐

```python
def fetch_stock_prices_api(target_date):
    """KOSPI + KOSDAQ 모두 수집"""
    all_prices = []

    # 1. KOSPI 수집
    kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
    for ticker in kospi_tickers:
        try:
            df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                df['ticker'] = ticker
                all_prices.append(df)
        except:
            pass  # 실패한 종목은 스킵

    # 2. KOSDAQ 수집
    kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
    for ticker in kosdaq_tickers:
        try:
            df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                df['ticker'] = ticker
                all_prices.append(df)
        except:
            pass  # 실패한 종목은 스킵

    return pd.concat(all_prices, ignore_index=True)
```

---

### **방법 2: 종목 마스터 테이블 유지** ⭐⭐⭐⭐

**장점**: 상장폐지/신규 상장 추적 가능, 가장 정확함
**단점**: 초기 구축에 시간 필요

```python
def fetch_stock_prices_api(target_date):
    """DB에 저장된 모든 종목에 대해 수집 시도"""
    conn = engine.raw_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ticker FROM stocks WHERE is_active = true")
    tickers = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()

    all_prices = []
    for ticker in tickers:
        try:
            df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                df['ticker'] = ticker
                all_prices.append(df)
        except:
            pass

    return pd.concat(all_prices, ignore_index=True)
```

---

### **방법 3: 동적 종목 발견** ⭐⭐⭐

**장점**: 신규 상장 종목 자동 포함, 유연함
**단점**: API 호출 횟수 증가

```python
def fetch_all_available_tickers(date_str):
    """모든 가능한 마켓에서 종목 수집"""
    all_tickers = set()

    for market in ["KOSPI", "KOSDAQ", "KONEX"]:  # KONEX도 포함
        try:
            tickers = pykrx_stock.get_market_ticker_list(market=market, date=date_str)
            all_tickers.update(tickers)
        except:
            pass

    return list(all_tickers)
```

---

### **방법 4: 배치 처리 + 실패 재시도** ⭐⭐⭐⭐

**장점**: 효율적인 처리, 실패한 종목 재수집
**단점**: 복잡도 증가

```python
def fetch_stock_prices_api_with_retry(target_date):
    """배치 처리로 효율성 향상"""
    # 1. 모든 종목 가져오기
    kospi = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
    kosdaq = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
    all_tickers = list(set(kospi) | set(kosdaq))

    # 2. 배치 처리 (100개씩)
    batch_size = 100
    all_prices = []
    failed_tickers = []

    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i:i+batch_size]
        for ticker in batch:
            try:
                df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                if not df.empty:
                    df['ticker'] = ticker
                    all_prices.append(df)
            except Exception as e:
                failed_tickers.append((ticker, str(e)))

    # 3. 실패한 종목 재시도
    logger.info(f"Failed tickers: {len(failed_tickers)}")
    for ticker, error in failed_tickers:
        try:
            df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                df['ticker'] = ticker
                all_prices.append(df)
        except:
            pass

    return pd.concat(all_prices, ignore_index=True)
```

---

### **방법 5: 설정 파일 기반 수집** ⭐⭐⭐⭐⭐

**장점**: 운영하면서 수집 대상 조정 가능, 유지보수 쉬움
**단점**: 설정 파일 관리 필요

**config.json 생성:**
```json
{
  "markets": ["KOSPI", "KOSDAQ", "KONEX"],
  "collection_settings": {
    "batch_size": 100,
    "retry_count": 3,
    "timeout_seconds": 30,
    "skip_suspended": true
  },
  "excluded_tickers": [],
  "included_tickers": []
}
```

**코드:**
```python
def fetch_stock_prices_api(target_date):
    """설정 파일 기반 수집"""
    import json

    with open('/app/config.json', 'r') as f:
        config = json.load(f)

    all_tickers = set()

    # 설정된 마켓에서 종목 수집
    for market in config['markets']:
        try:
            tickers = pykrx_stock.get_market_ticker_list(market=market, date=date_str)
            all_tickers.update(tickers)
        except:
            pass

    # 제외 종목 제거
    all_tickers -= set(config['excluded_tickers'])

    # 포함 종목 추가
    all_tickers.update(config['included_tickers'])

    # 수집 로직...
    return prices_df
```

---

## 📊 방법 비교표

| 기준 | 방법 1 | 방법 2 | 방법 3 | 방법 4 | 방법 5 |
|------|-------|-------|-------|-------|-------|
| 구현 난도 | ⭐ | ⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐⭐ |
| 정확도 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 유연성 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 성능 | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 유지보수 | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 🎯 권장 조치

**1단계**: 방법 1 (마켓별 별도 수집) 구현
- 가장 간단하고 빠르게 2,700개 수집 가능
- 지금 당장 적용 가능

**2단계**: 방법 5 (설정 파일) 기반으로 리팩토링
- 운영 단계에서 종목 관리 용이
- 상장폐지/신규 상장 대응 자동화

---

## 📝 작업 계획

### Phase 1: 즉시 (30분)
- [ ] 방법 1 구현: `fetch_stock_prices_api()` 수정
- [ ] KOSDAQ 명시 추가
- [ ] DAG 재시작 및 테스트

### Phase 2: 단기 (2시간)
- [ ] TimescaleDB 제약 조건 문제 해결
- [ ] 2025-10-28 데이터 재수집

### Phase 3: 중기 (1일)
- [ ] 방법 5 (설정 파일 기반) 구현
- [ ] 과거 데이터 재수집 스크립트 작성

### Phase 4: 장기 (지속)
- [ ] 방법 2 (종목 마스터 테이블) 구축
- [ ] 상장폐지 종목 추적 시스템 개발

---

## ⚠️ 주의사항

1. **2,700개 모두는 불가능할 수도**
   - 상장폐지, 거래정지 종목 제외
   - 실제 거래 가능한 종목: ~2,200개

2. **API 호출량 증가**
   - 하루에 2,700회 호출 (1종목 1회)
   - pykrx 제한 확인 필요

3. **수집 시간 증가**
   - 현재: ~5분 (955개)
   - 예상: ~15분 (2,700개)

---

## 📌 다음 단계

사용자의 선택을 기다리는 중:
1. 방법 1부터 구현할까?
2. 방법 5 (설정 파일) 바로 구현?
3. 다른 방법 우선?
