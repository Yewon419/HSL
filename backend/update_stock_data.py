"""
기존 종목 리스트 기반 주가 데이터 업데이트 스크립트
- get_market_ticker_list가 작동하지 않을 때 사용
- DB에 있는 종목 리스트를 사용하여 최신 데이터 수집
"""
import psycopg2
from pykrx import stock as pykrx_stock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import sys

# DB 연결
conn = psycopg2.connect(
    host='postgres',
    port=5432,
    database='stocktrading',
    user='admin',
    password='admin123'
)
cursor = conn.cursor()

# DB에서 마지막 데이터 날짜 확인
cursor.execute("SELECT MAX(date) FROM stock_prices")
last_date = cursor.fetchone()[0]
print(f'📅 DB 마지막 날짜: {last_date}')

# 수집할 날짜 범위 설정
start_date = (last_date + timedelta(days=1)).strftime('%Y%m%d')
end_date = datetime.now().strftime('%Y%m%d')

print(f'📅 수집 기간: {start_date} ~ {end_date}')
print('=' * 60)

# DB에서 종목 리스트 가져오기
cursor.execute("SELECT ticker FROM stocks WHERE is_active = true OR is_active IS NULL")
tickers = [row[0] for row in cursor.fetchall()]
print(f'📋 수집 대상 종목: {len(tickers)}개')

# 주가 데이터 수집
print(f'\n📈 주가 데이터 수집 중...')
price_count = 0
error_count = 0

for idx, ticker in enumerate(tickers):
    try:
        df = pykrx_stock.get_market_ohlcv(start_date, end_date, ticker)

        if not df.empty:
            for date_idx, row in df.iterrows():
                date_str = date_idx.strftime('%Y-%m-%d')
                cursor.execute('''
                    INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                ''', (ticker, date_str, float(row['시가']), float(row['고가']),
                      float(row['저가']), float(row['종가']), int(row['거래량'])))
                price_count += 1

        # 진행상황 출력
        if (idx + 1) % 100 == 0:
            conn.commit()
            print(f'  진행: {idx+1}/{len(tickers)} ({price_count}개 저장)')

    except Exception as e:
        error_count += 1
        continue

conn.commit()
print(f'\n✅ 주가 수집 완료: {price_count}개 (에러: {error_count}개)')

# 기술 지표 계산
print(f'\n📊 기술 지표 계산 중...')
indicator_count = 0

# 새로 수집된 날짜 확인
cursor.execute(f"SELECT DISTINCT date FROM stock_prices WHERE date > '{last_date}' ORDER BY date")
new_dates = [row[0] for row in cursor.fetchall()]
print(f'  새 날짜: {new_dates}')

for target_date in new_dates:
    date_str = target_date.strftime('%Y-%m-%d')

    for idx, ticker in enumerate(tickers):
        try:
            # 과거 200일치 데이터 가져오기
            cursor.execute('''
                SELECT date, close_price, high_price, low_price, volume
                FROM stock_prices
                WHERE ticker = %s AND date <= %s
                ORDER BY date DESC
                LIMIT 200
            ''', (ticker, date_str))

            rows = cursor.fetchall()
            if len(rows) < 20:
                continue

            df = pd.DataFrame(rows, columns=['date', 'close', 'high', 'low', 'volume'])
            df = df.sort_values('date')
            df['close'] = pd.to_numeric(df['close'])
            df['high'] = pd.to_numeric(df['high'])
            df['low'] = pd.to_numeric(df['low'])
            df['volume'] = pd.to_numeric(df['volume'])

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
            rsi_val = rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else None

            # Bollinger Bands
            bb_middle = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            bb_upper = bb_middle + (bb_std * 2)
            bb_lower = bb_middle - (bb_std * 2)
            bb_upper_val = bb_upper.iloc[-1] if not pd.isna(bb_upper.iloc[-1]) else None
            bb_lower_val = bb_lower.iloc[-1] if not pd.isna(bb_lower.iloc[-1]) else None

            # MACD
            exp1 = df['close'].ewm(span=12, adjust=False).mean()
            exp2 = df['close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            macd_hist = macd - macd_signal
            macd_val = macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else None
            macd_signal_val = macd_signal.iloc[-1] if not pd.isna(macd_signal.iloc[-1]) else None
            macd_hist_val = macd_hist.iloc[-1] if not pd.isna(macd_hist.iloc[-1]) else None

            # Stochastic
            low_14 = df['low'].rolling(14).min()
            high_14 = df['high'].rolling(14).max()
            stoch_k = 100 * ((df['close'] - low_14) / (high_14 - low_14))
            stoch_d = stoch_k.rolling(3).mean()
            stoch_k_val = stoch_k.iloc[-1] if not pd.isna(stoch_k.iloc[-1]) else None
            stoch_d_val = stoch_d.iloc[-1] if not pd.isna(stoch_d.iloc[-1]) else None

            # DB 저장
            cursor.execute('''
                INSERT INTO technical_indicators (
                    ticker, date, ma_20, ma_50, ma_200, rsi,
                    bollinger_upper, bollinger_lower,
                    macd, macd_signal, macd_histogram,
                    stoch_k, stoch_d
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    ma_20 = EXCLUDED.ma_20, ma_50 = EXCLUDED.ma_50, ma_200 = EXCLUDED.ma_200,
                    rsi = EXCLUDED.rsi, bollinger_upper = EXCLUDED.bollinger_upper,
                    bollinger_lower = EXCLUDED.bollinger_lower,
                    macd = EXCLUDED.macd, macd_signal = EXCLUDED.macd_signal,
                    macd_histogram = EXCLUDED.macd_histogram,
                    stoch_k = EXCLUDED.stoch_k, stoch_d = EXCLUDED.stoch_d
            ''', (ticker, date_str, ma_20, ma_50, ma_200, rsi_val,
                  bb_upper_val, bb_lower_val, macd_val, macd_signal_val, macd_hist_val,
                  stoch_k_val, stoch_d_val))

            indicator_count += 1

        except Exception as e:
            continue

    conn.commit()
    print(f'  {date_str} 지표 계산 완료')

print(f'\n✅ 기술 지표 계산 완료: {indicator_count}개')

# 최종 확인
cursor.execute("SELECT MAX(date) FROM stock_prices")
new_last_date = cursor.fetchone()[0]

cursor.close()
conn.close()

print('\n' + '=' * 60)
print('✅ 데이터 업데이트 완료!')
print(f'   - 이전 마지막 날짜: {last_date}')
print(f'   - 현재 마지막 날짜: {new_last_date}')
print(f'   - 수집된 주가: {price_count}개')
print(f'   - 계산된 지표: {indicator_count}개')
print('=' * 60)
