# Airflow DAG 백업

## 개요
이 디렉토리는 기존 Airflow DAG 파일들의 백업입니다.
새로운 수집 시스템으로 마이그레이션되며 참고용으로 보관됩니다.

## 백업 파일 목록

### 핵심 파일
- **common_functions.py** (21KB): 공통 함수 - pykrx 호출, DB 저장 등
- **daily_collection_dag.py** (6.2KB): 일일 주가/지수 수집 DAG (사용 중)
- **technical_indicator_dag.py** (7.8KB): 기술적 지표 계산 DAG

### 참고 파일 (비활성)
- **manual_collection_dag.py**: 수동 수집용 DAG
- **daily_stock_data_pipeline.py**: 대체 파이프라인
- **korean_stock_data_collection.py**: 한국 주식 수집 파이프라인
- **enhanced_korean_stock_pipeline.py**: 향상된 파이프라인
- **integrated_stock_pipeline.py**: 통합 파이프라인
- 기타 여러 시도들...

## 사용한 주요 함수

### pykrx 호출
```python
from pykrx import stock

# 티커 조회
tickers = stock.get_market_ticker_list(date='20251020')

# 주가 조회
df = stock.get_market_ohlcv(start_date, end_date, ticker)

# 지수 조회
df = stock.get_index_ohlcv(start_date, end_date, index_name)
```

### DB 저장 패턴
```python
from database import SessionLocal
from models import StockPrice, MarketIndex

session = SessionLocal()
# 데이터 저장
for item in data:
    session.add(StockPrice(**item))
session.commit()
```

## 새 시스템에서 재사용할 함수
다음 함수들을 새 `collect_stock_data.py`에 통합:

1. **fetch_stock_prices_api()** - pykrx로 주가 수집
2. **fetch_market_indices_api()** - pykrx로 지수 수집
3. **save_stock_prices()** - DB에 주가 저장
4. **save_market_indices()** - DB에 지수 저장
5. **get_execution_date()** - 날짜 추출

## 기술적 지표 계산
`comprehensive_indicators.py`에서 사용한 지표들:
- RSI (상대강도지수)
- MACD
- SMA (단순이동평균)
- Bollinger Bands
- 거래량 지표

## 마이그레이션 체크리스트
- [ ] 새 수집 스크립트에서 common_functions 로직 재사용
- [ ] pykrx 호출 메서드 통일
- [ ] DB 모델 일관성 유지
- [ ] 기술적 지표 계산 로직 마이그레이션
- [ ] 로깅 및 모니터링 추가

---
**백업일**: 2025-10-20
**마이그레이션 목표**: 새로운 Cron 기반 시스템으로 전환
