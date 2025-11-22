"""
테스트용 샘플 데이터 생성 스크립트
"""
import psycopg2
from datetime import datetime, timedelta
import random

# DB 연결
conn = psycopg2.connect(
    host='postgres',
    port=5432,
    database='stocktrading',
    user='admin',
    password='admin123'
)
cursor = conn.cursor()

print('🚀 샘플 데이터 생성 시작')
print('=' * 60)

# 샘플 종목 정보
sample_stocks = [
    ('005930', '삼성전자'),
    ('000660', 'SK하이닉스'),
    ('035720', '카카오'),
    ('035420', 'NAVER'),
    ('051910', 'LG화학'),
    ('006400', '삼성SDI'),
    ('207940', '삼성바이오로직스'),
    ('005380', '현대차'),
    ('000270', '기아'),
    ('068270', '셀트리온'),
]

# 1. stocks 테이블에 종목 추가
print('\n📝 종목 정보 저장 중...')
for ticker, name in sample_stocks:
    cursor.execute('''
        INSERT INTO stocks (ticker, company_name, sector, industry)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE SET company_name = EXCLUDED.company_name
    ''', (ticker, name, 'IT', 'Technology'))
conn.commit()
print(f'✅ {len(sample_stocks)}개 종목 저장 완료')

# 2. 주가 데이터 생성 (최근 30일)
print('\n📈 주가 데이터 생성 중...')
price_count = 0
today = datetime.now()

for days_ago in range(30, 0, -1):
    date = today - timedelta(days=days_ago)
    # 주말 제외
    if date.weekday() >= 5:
        continue

    date_str = date.strftime('%Y-%m-%d')

    for ticker, name in sample_stocks:
        # 임의의 주가 생성
        base_price = random.uniform(30000, 100000)
        open_price = base_price + random.uniform(-5000, 5000)
        close_price = base_price + random.uniform(-5000, 5000)
        high_price = max(open_price, close_price) + random.uniform(0, 3000)
        low_price = min(open_price, close_price) - random.uniform(0, 3000)
        volume = random.randint(100000, 10000000)

        cursor.execute('''
            INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, date) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume
        ''', (ticker, date_str, open_price, high_price, low_price, close_price, volume))
        price_count += 1

    if days_ago % 10 == 0:
        conn.commit()

conn.commit()
print(f'✅ {price_count}개 주가 데이터 생성 완료')

# 3. 기술 지표 생성
print('\n📊 기술 지표 생성 중...')
indicator_count = 0

for days_ago in range(30, 0, -1):
    date = today - timedelta(days=days_ago)
    if date.weekday() >= 5:
        continue

    date_str = date.strftime('%Y-%m-%d')

    for ticker, name in sample_stocks:
        # 임의의 지표 값 생성
        ma_20 = random.uniform(30000, 100000)
        ma_50 = random.uniform(30000, 100000)
        ma_200 = random.uniform(30000, 100000)
        rsi = random.uniform(20, 80)
        bb_upper = ma_20 + 5000
        bb_middle = ma_20
        bb_lower = ma_20 - 5000
        macd = random.uniform(-1000, 1000)
        macd_signal = random.uniform(-1000, 1000)
        macd_hist = macd - macd_signal
        stoch_k = random.uniform(20, 80)
        stoch_d = random.uniform(20, 80)

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
        ''', (ticker, date_str, ma_20, ma_50, ma_200, rsi,
              bb_upper, bb_middle, bb_lower,
              macd, macd_signal, macd_hist,
              stoch_k, stoch_d))
        indicator_count += 1

    if days_ago % 10 == 0:
        conn.commit()

conn.commit()
print(f'✅ {indicator_count}개 기술 지표 생성 완료')

# 4. 시장 지수 생성
print('\n📊 시장 지수 생성 중...')
index_count = 0

for days_ago in range(30, 0, -1):
    date = today - timedelta(days=days_ago)
    if date.weekday() >= 5:
        continue

    date_str = date.strftime('%Y-%m-%d')

    for index_code, index_name in [('1001', 'KOSPI'), ('2001', 'KOSDAQ')]:
        base_price = 2500 if index_code == '1001' else 750
        open_price = base_price + random.uniform(-50, 50)
        close_price = base_price + random.uniform(-50, 50)
        high_price = max(open_price, close_price) + random.uniform(0, 30)
        low_price = min(open_price, close_price) - random.uniform(0, 30)
        volume = random.randint(500000000, 1000000000)

        cursor.execute('''
            INSERT INTO market_indices (index_code, index_name, date, open_price, high_price, low_price, close_price, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (index_code, date) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume
        ''', (index_code, index_name, date_str, open_price, high_price, low_price, close_price, volume))
        index_count += 1

conn.commit()
print(f'✅ {index_count}개 시장 지수 생성 완료')

cursor.close()
conn.close()

print('\n' + '=' * 60)
print('✅ 샘플 데이터 생성 완료!')
print(f'   - 종목: {len(sample_stocks)}개')
print(f'   - 주가: {price_count}개')
print(f'   - 지표: {indicator_count}개')
print(f'   - 지수: {index_count}개')
print('=' * 60)
