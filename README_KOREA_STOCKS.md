# Korean Stock Market Data Fetcher

## Overview
This module extends the existing stock trading system to fetch and store all Korean stock market data (KOSPI and KOSDAQ) with 5 years of historical prices.

## Features
- Fetches all KOSPI and KOSDAQ listed stocks
- Retrieves 5 years of historical price data (OHLCV)
- Stores market type classification (KOSPI/KOSDAQ)
- Includes market capitalization and fundamental data
- Supports incremental updates for recent prices
- Progress tracking with detailed logging

## Installation

### Prerequisites
- Python 3.8+
- PostgreSQL or SQLite database
- Stable internet connection

### Install Required Libraries
```bash
pip install -r backend/requirements.txt
```

Key dependencies:
- `pykrx`: Korean stock market data API
- `yfinance`: Backup data source
- `pandas`: Data manipulation
- `sqlalchemy`: Database ORM
- `tqdm`: Progress bars

## Usage

### 1. Full Data Fetch (First Time Setup)
Fetch all Korean stocks with 5 years of history:

```bash
# Windows
fetch_korea_stocks.bat

# Or directly with Python
python backend/fetch_korea_stocks.py --years 5
```

### 2. Update Recent Prices
Update only the last 30 days of prices:

```bash
python backend/fetch_korea_stocks.py --update-only --days 30
```

### 3. Custom Time Range
Fetch specific years of data:

```bash
python backend/fetch_korea_stocks.py --years 3
```

## Database Schema

### Extended Stock Table
```sql
stocks
- ticker (PK)
- company_name
- market_type (KOSPI/KOSDAQ)
- sector
- industry
- market_cap
- isin_code
- updated_at
```

### Stock Prices Table
```sql
stock_prices
- ticker (FK)
- date
- open_price
- high_price
- low_price
- close_price
- volume
```

## API Integration

### Using in Your Application

```python
from stock_service.korea_stock_fetcher import KoreaStockFetcher

# Initialize fetcher
fetcher = KoreaStockFetcher()

# Get all tickers
tickers = fetcher.get_all_tickers()
print(f"KOSPI: {len(tickers['KOSPI'])} stocks")
print(f"KOSDAQ: {len(tickers['KOSDAQ'])} stocks")

# Fetch specific stock data
stock_info = fetcher.get_stock_info('005930', 'KOSPI')  # Samsung Electronics

# Update recent prices
fetcher.update_recent_prices(days=7)
```

### FastAPI Endpoints
The fetched data can be accessed through the existing FastAPI endpoints:

```python
GET /api/stocks/list?market=KOSPI
GET /api/stocks/list?market=KOSDAQ
GET /api/stocks/{ticker}/prices?start_date=2020-01-01&end_date=2024-12-31
```

## Performance Considerations

### Data Volume
- KOSPI: ~900 stocks
- KOSDAQ: ~1,600 stocks
- Total: ~2,500 stocks
- 5 years of daily data: ~1,250 trading days per stock
- Total records: ~3.1 million price records

### Execution Time
- Full fetch: 4-8 hours (depending on network speed)
- Daily update: 10-30 minutes
- Rate limiting: 0.1 seconds between API calls

### Database Optimization
- Indexed on (ticker, date) for fast queries
- Materialized views for market summaries
- Partitioning recommended for large datasets

## Monitoring

### Log Files
Logs are saved with timestamps:
```
korea_stock_fetch_20240101_120000.log
```

### Progress Tracking
- Real-time progress bars using tqdm
- Detailed logging of processed stocks
- Error handling with recovery

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check internet connection
   - Verify pykrx API is accessible
   - Try reducing MAX_WORKERS in config

2. **Database Errors**
   - Ensure database is running
   - Check connection string in .env
   - Verify table migrations are applied

3. **Memory Issues**
   - Process in smaller batches
   - Increase system RAM
   - Use database pagination

### Error Recovery
The fetcher automatically:
- Skips already fetched data
- Logs failed tickers
- Continues with next stock on error

## Scheduled Updates

### Using Cron (Linux/Mac)
```bash
# Daily update at 6 PM KST
0 18 * * * /path/to/python /path/to/fetch_korea_stocks.py --update-only
```

### Using Task Scheduler (Windows)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger: Daily at 6 PM
4. Set action: Run fetch_korea_stocks.bat --update-only

## Data Quality

### Validation
- Checks for missing dates
- Validates price ranges
- Ensures volume is positive
- Logs anomalies for review

### Data Sources
- Primary: PyKRX (Korea Exchange official data)
- Backup: yfinance (Yahoo Finance)
- Cross-validation between sources

## Future Enhancements

- [ ] Real-time price updates using WebSocket
- [ ] Intraday data collection
- [ ] Foreign ownership data
- [ ] Sector/industry analysis
- [ ] Market breadth indicators
- [ ] Options and futures data

## Support

For issues or questions:
1. Check the log files for detailed error messages
2. Verify all dependencies are installed
3. Ensure database connectivity
4. Review the troubleshooting section

## License

This module is part of the Stock Trading System and follows the same license terms.