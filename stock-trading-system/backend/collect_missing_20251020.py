#!/usr/bin/env python3
import sys
sys.path.insert(0, '/app')
from datetime import date
from sqlalchemy import create_engine, text
import pandas as pd
import os

os.environ['DATABASE_URL'] = 'postgresql://admin:admin123@stock-db:5432/stocktrading'

engine = create_engine(
    'postgresql://admin:admin123@stock-db:5432/stocktrading',
    connect_args={'options': '-c client_encoding=utf8'}
)

target_date = date(2025, 10, 20)
reference_date = date(2025, 10, 17)

print('='*70)
print('Collecting missing stock prices for 2025-10-20')
print('='*70 + '\n')

try:
    # Get tickers that exist on 17th but not on 20th
    print('[1] Finding missing tickers...')
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT DISTINCT sp17.ticker
            FROM stock_prices sp17
            WHERE sp17.date = :ref_date
            AND NOT EXISTS (
                SELECT 1 FROM stock_prices sp20
                WHERE sp20.date = :target_date
                AND sp20.ticker = sp17.ticker
            )
        '''), {'ref_date': reference_date, 'target_date': target_date})

        missing_tickers = [row[0] for row in result.fetchall()]

    print(f'✓ Found {len(missing_tickers)} missing tickers')

    # Fetch data for missing tickers from pykrx
    print('[2] Fetching data from pykrx for missing tickers...')
    from pykrx import stock as pykrx_stock

    date_str = target_date.strftime("%Y%m%d")
    all_prices = []
    failed_tickers = []
    success_count = 0

    for i, ticker in enumerate(missing_tickers):
        if (i + 1) % 200 == 0:
            print(f'   Progress: {i+1}/{len(missing_tickers)}...')

        try:
            df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                df['ticker'] = ticker
                df['date'] = target_date
                all_prices.append(df)
                success_count += 1
        except Exception as e:
            failed_tickers.append((ticker, str(e)))

    print(f'✓ Fetched {success_count}/{len(missing_tickers)} tickers')
    if failed_tickers:
        print(f'  {len(failed_tickers)} failed (likely delisted or no data)')

    if all_prices:
        # Prepare dataframe
        print('[3] Preparing data...')
        prices_df = pd.concat(all_prices, ignore_index=True)

        # Normalize
        normalized_df = pd.DataFrame({
            'ticker': prices_df['ticker'],
            'date': target_date,
            'open_price': prices_df['시가'].astype(float),
            'high_price': prices_df['고가'].astype(float),
            'low_price': prices_df['저가'].astype(float),
            'close_price': prices_df['종가'].astype(float),
            'volume': prices_df['거래량'].astype(int),
            'created_at': pd.Timestamp.now()
        })

        print(f'✓ Prepared {len(normalized_df)} records')

        # Save to database
        print('[4] Saving to database...')
        with engine.begin() as conn:
            insert_count = 0
            for i, (_, row) in enumerate(normalized_df.iterrows()):
                if (i + 1) % 200 == 0:
                    print(f'   Saving progress: {i+1}/{len(normalized_df)}...')

                try:
                    result = conn.execute(text('''
                        INSERT INTO stock_prices
                        (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                        VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
                        ON CONFLICT (ticker, date) DO NOTHING
                    '''), {
                        'ticker': row['ticker'],
                        'date': row['date'],
                        'open_price': row['open_price'],
                        'high_price': row['high_price'],
                        'low_price': row['low_price'],
                        'close_price': row['close_price'],
                        'volume': row['volume'],
                        'created_at': row['created_at']
                    })
                    if result.rowcount > 0:
                        insert_count += 1
                except Exception as e:
                    print(f'  Error inserting {row["ticker"]}: {e}')

        print(f'✓ Saved {insert_count} records')

    # Final count
    print('[5] Final verification...')
    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT COUNT(DISTINCT ticker) FROM stock_prices WHERE date = :date
        '''), {'date': target_date})
        final_count = result.scalar()
        print(f'✓ Total tickers for 2025-10-20: {final_count}')

    print('\n' + '='*70)
    print('✓ Collection complete!')
    print('='*70)

except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
