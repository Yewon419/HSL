"""
간단한 주가 데이터 수집 스크립트
"""
import psycopg2
from pykrx import stock as pykrx_stock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# DB 연결
conn = psycopg2.connect(
    host='postgres',
    port=5432,
    database='stocktrading',
    user='admin',
    password='admin123'
)
cursor = conn.cursor()

# 최근 거래일 찾기
today = datetime.now()
target_date = today

# 주말이면 금요일로 이동
if target_date.weekday() == 5:  # 토요일
    target_date = target_date - timedelta(days=1)
elif target_date.weekday() == 6:  # 일요일
    target_date = target_date - timedelta(days=2)

date_str = target_date.strftime('%Y%m%d')
date_sql = target_date.strftime('%Y-%m-%d')

print(f'🚀 데이터 수집 시작: {date_sql}')
print('=' * 60)

# 1. 종목 목록 수집
print('\n📋 종목 목록 수집 중...')
kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
all_tickers = list(set(kospi_tickers) | set(kosdaq_tickers))
print(f'✅ 총 {len(all_tickers)}개 종목 발견')

# 2. stocks 테이블에 종목 추가
print('\n📝 종목 정보 저장 중...')
stock_count = 0
for ticker in all_tickers:
    try:
        name = pykrx_stock.get_market_ticker_name(ticker)
        cursor.execute('''
            INSERT INTO stocks (ticker, company_name)
            VALUES (%s, %s)
            ON CONFLICT (ticker) DO UPDATE SET company_name = EXCLUDED.company_name
        ''', (ticker, name))
        stock_count += 1
    except Exception as e:
        print(f'⚠️  {ticker} 저장 실패: {e}')
        continue

conn.commit()
print(f'✅ {stock_count}개 종목 정보 저장 완료')

# 3. 주가 데이터 수집
print(f'\n📈 주가 데이터 수집 중... (0/{len(all_tickers)})', end='', flush=True)
price_count = 0
for idx, ticker in enumerate(all_tickers):
    try:
        df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
        if not df.empty:
            row = df.iloc[0]
            cursor.execute('''
                INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
            ''', (ticker, date_sql, float(row['시가']), float(row['고가']),
                  float(row['저가']), float(row['종가']), int(row['거래량'])))
            price_count += 1

        # 진행상황 업데이트
        if (idx + 1) % 100 == 0:
            print(f'\r📈 주가 데이터 수집 중... ({idx+1}/{len(all_tickers)})', end='', flush=True)
            conn.commit()  # 100개마다 커밋

    except Exception as e:
        continue

conn.commit()
print(f'\r📈 주가 데이터 수집 완료: {price_count}개          ')

# 4. 시장 지수 수집
print('\n📊 시장 지수 수집 중...')
try:
    kospi_df = pykrx_stock.get_index_ohlcv(date_str, date_str, "1001")  # KOSPI
    kosdaq_df = pykrx_stock.get_index_ohlcv(date_str, date_str, "2001")  # KOSDAQ

    indices_saved = 0
    for index_code, df, index_name in [("1001", kospi_df, "KOSPI"), ("2001", kosdaq_df, "KOSDAQ")]:
        if not df.empty:
            row = df.iloc[0]
            cursor.execute('''
                INSERT INTO market_indices (index_code, index_name, date, open_price, high_price, low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (index_code, date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
            ''', (index_code, index_name, date_sql, float(row['시가']), float(row['고가']),
                  float(row['저가']), float(row['종가']), int(row['거래량'])))
            indices_saved += 1

    conn.commit()
    print(f'✅ {indices_saved}개 시장 지수 저장 완료')
except Exception as e:
    print(f'⚠️  시장 지수 저장 실패: {e}')

# 5. 기술 지표 계산
print(f'\n📊 기술 지표 계산 중... (0/{price_count})', end='', flush=True)

# 먼저 모든 종목의 과거 데이터를 가져와서 지표 계산
indicator_count = 0
for idx, ticker in enumerate(all_tickers[:price_count]):  # 주가가 수집된 종목만
    try:
        # 과거 200일치 데이터 가져오기
        cursor.execute('''
            SELECT date, close_price, volume
            FROM stock_prices
            WHERE ticker = %s AND date <= %s
            ORDER BY date DESC
            LIMIT 200
        ''', (ticker, date_sql))

        rows = cursor.fetchall()
        if len(rows) < 20:  # 최소 20일 데이터 필요
            continue

        df = pd.DataFrame(rows, columns=['date', 'close', 'volume'])
        df = df.sort_values('date')
        df['close'] = pd.to_numeric(df['close'])
        df['volume'] = pd.to_numeric(df['volume'])

        # 기술 지표 계산
        # MA
        ma_20 = df['close'].rolling(20).mean().iloc[-1] if len(df) >= 20 else None
        ma_50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else None
        ma_200 = df['close'].rolling(200).mean().iloc[-1] if len(df) >= 200 else None

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_val = rsi.iloc[-1] if len(rsi) > 0 and not pd.isna(rsi.iloc[-1]) else None

        # Bollinger Bands
        bb_middle = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        bb_upper = bb_middle + (bb_std * 2)
        bb_lower = bb_middle - (bb_std * 2)

        bb_upper_val = bb_upper.iloc[-1] if len(bb_upper) > 0 and not pd.isna(bb_upper.iloc[-1]) else None
        bb_middle_val = bb_middle.iloc[-1] if len(bb_middle) > 0 and not pd.isna(bb_middle.iloc[-1]) else None
        bb_lower_val = bb_lower.iloc[-1] if len(bb_lower) > 0 and not pd.isna(bb_lower.iloc[-1]) else None

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=9, adjust=False).mean()
        macd_hist = macd - macd_signal

        macd_val = macd.iloc[-1] if len(macd) > 0 and not pd.isna(macd.iloc[-1]) else None
        macd_signal_val = macd_signal.iloc[-1] if len(macd_signal) > 0 and not pd.isna(macd_signal.iloc[-1]) else None
        macd_hist_val = macd_hist.iloc[-1] if len(macd_hist) > 0 and not pd.isna(macd_hist.iloc[-1]) else None

        # Stochastic
        low_14 = df['close'].rolling(14).min()
        high_14 = df['close'].rolling(14).max()
        stoch_k = 100 * ((df['close'] - low_14) / (high_14 - low_14))
        stoch_d = stoch_k.rolling(3).mean()

        stoch_k_val = stoch_k.iloc[-1] if len(stoch_k) > 0 and not pd.isna(stoch_k.iloc[-1]) else None
        stoch_d_val = stoch_d.iloc[-1] if len(stoch_d) > 0 and not pd.isna(stoch_d.iloc[-1]) else None

        # DB에 저장
        cursor.execute('''
            INSERT INTO technical_indicators (
                ticker, date, ma_20, ma_50, ma_200, rsi,
                bollinger_upper, bollinger_middle, bollinger_lower,
                macd, macd_signal, macd_histogram,
                stoch_k, stoch_d
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, date) DO UPDATE SET
                ma_20 = EXCLUDED.ma_20,
                ma_50 = EXCLUDED.ma_50,
                ma_200 = EXCLUDED.ma_200,
                rsi = EXCLUDED.rsi,
                bollinger_upper = EXCLUDED.bollinger_upper,
                bollinger_middle = EXCLUDED.bollinger_middle,
                bollinger_lower = EXCLUDED.bollinger_lower,
                macd = EXCLUDED.macd,
                macd_signal = EXCLUDED.macd_signal,
                macd_histogram = EXCLUDED.macd_histogram,
                stoch_k = EXCLUDED.stoch_k,
                stoch_d = EXCLUDED.stoch_d
        ''', (ticker, date_sql, ma_20, ma_50, ma_200, rsi_val,
              bb_upper_val, bb_middle_val, bb_lower_val,
              macd_val, macd_signal_val, macd_hist_val,
              stoch_k_val, stoch_d_val))

        indicator_count += 1

        # 진행상황 업데이트
        if (idx + 1) % 100 == 0:
            print(f'\r📊 기술 지표 계산 중... ({idx+1}/{price_count})', end='', flush=True)
            conn.commit()

    except Exception as e:
        continue

conn.commit()
print(f'\r📊 기술 지표 계산 완료: {indicator_count}개          ')

cursor.close()
conn.close()

print('\n' + '=' * 60)
print('✅ 모든 데이터 수집 완료!')
print(f'   - 종목: {stock_count}개')
print(f'   - 주가: {price_count}개')
print(f'   - 지표: {indicator_count}개')
print('=' * 60)
