#!/usr/bin/env python
"""
투자자별 매매량 데이터 수집 스크립트
네이버 증권에서 외인/기관/개인 매매량 데이터를 수집합니다.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import re

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Stock, InvestorTrade
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'investor_trades_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def fetch_investor_data_from_naver(ticker, start_date, end_date):
    """
    네이버 증권에서 투자자별 매매 데이터를 가져옵니다.

    Args:
        ticker: 종목 코드
        start_date: 시작 날짜 (YYYYMMDD)
        end_date: 종료 날짜 (YYYYMMDD)

    Returns:
        list: [{date, foreign_buy, foreign_sell, institution_buy, institution_sell, individual_buy, individual_sell}, ...]
    """
    # 종목 코드에서 .KS, .KQ 등 접미사 제거
    clean_ticker = ticker.split('.')[0]

    # 한국 주식이 아닌 경우 (숫자가 아니면) 스킵
    if not clean_ticker.isdigit():
        return []

    url = f"https://finance.naver.com/item/frgn.naver?code={clean_ticker}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 테이블에서 데이터 추출
        table = soup.find('table', {'class': 'type2'})
        if not table:
            logger.warning(f"No data table found for {ticker}")
            return []

        rows = table.find_all('tr')
        data = []

        for row in rows[2:]:  # 헤더 스킵
            cols = row.find_all('td')
            if len(cols) < 9:
                continue

            try:
                # 날짜 파싱
                date_str = cols[0].get_text(strip=True)
                if not date_str or date_str == '':
                    continue

                date_obj = datetime.strptime(date_str, '%Y.%m.%d')

                # 날짜 필터링
                if start_date and date_obj < datetime.strptime(start_date, '%Y%m%d'):
                    continue
                if end_date and date_obj > datetime.strptime(end_date, '%Y%m%d'):
                    continue

                # 투자자별 데이터 파싱 (단위: 주)
                def parse_number(text):
                    """숫자 문자열을 정수로 변환"""
                    text = text.strip().replace(',', '')
                    if text == '' or text == '-':
                        return 0
                    return int(text)

                foreign_buy = parse_number(cols[1].get_text(strip=True))
                foreign_sell = parse_number(cols[2].get_text(strip=True))
                institution_buy = parse_number(cols[4].get_text(strip=True))
                institution_sell = parse_number(cols[5].get_text(strip=True))
                individual_buy = parse_number(cols[7].get_text(strip=True))
                individual_sell = parse_number(cols[8].get_text(strip=True))

                data.append({
                    'date': date_obj.date(),
                    'foreign_buy': foreign_buy,
                    'foreign_sell': foreign_sell,
                    'institution_buy': institution_buy,
                    'institution_sell': institution_sell,
                    'individual_buy': individual_buy,
                    'individual_sell': individual_sell
                })

            except Exception as e:
                logger.debug(f"Error parsing row for {ticker}: {e}")
                continue

        return data

    except requests.RequestException as e:
        logger.error(f"Request error for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error for {ticker}: {e}")
        return []


def save_investor_trades(db, ticker, trades_data):
    """
    투자자별 매매 데이터를 데이터베이스에 저장합니다.

    Args:
        db: Database session
        ticker: 종목 코드
        trades_data: 투자자별 매매 데이터 리스트
    """
    if not trades_data:
        return 0

    saved_count = 0

    for trade in trades_data:
        try:
            # 기존 데이터 확인
            existing = db.query(InvestorTrade).filter(
                InvestorTrade.ticker == ticker,
                InvestorTrade.date == trade['date']
            ).first()

            if existing:
                # 업데이트
                existing.foreign_buy = trade['foreign_buy']
                existing.foreign_sell = trade['foreign_sell']
                existing.institution_buy = trade['institution_buy']
                existing.institution_sell = trade['institution_sell']
                existing.individual_buy = trade['individual_buy']
                existing.individual_sell = trade['individual_sell']
            else:
                # 새로 삽입
                new_trade = InvestorTrade(
                    ticker=ticker,
                    date=trade['date'],
                    foreign_buy=trade['foreign_buy'],
                    foreign_sell=trade['foreign_sell'],
                    institution_buy=trade['institution_buy'],
                    institution_sell=trade['institution_sell'],
                    individual_buy=trade['individual_buy'],
                    individual_sell=trade['individual_sell']
                )
                db.add(new_trade)

            saved_count += 1

        except Exception as e:
            logger.error(f"Error saving trade data for {ticker} on {trade['date']}: {e}")
            continue

    try:
        db.commit()
        return saved_count
    except Exception as e:
        logger.error(f"Error committing trades for {ticker}: {e}")
        db.rollback()
        return 0


def main():
    """메인 함수"""
    logger.info("=" * 70)
    logger.info("투자자별 매매량 데이터 수집 시작")
    logger.info("=" * 70)

    # 2025년 1월 1일부터 현재까지
    start_date = "20250101"
    end_date = datetime.now().strftime("%Y%m%d")

    logger.info(f"수집 기간: {start_date} ~ {end_date}")

    db = SessionLocal()

    try:
        # 활성화된 모든 종목 조회
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        logger.info(f"총 {len(stocks)}개 종목 데이터 수집 시작")

        total_saved = 0
        success_count = 0
        failed_count = 0

        for idx, stock in enumerate(stocks, 1):
            ticker = stock.ticker
            company_name = stock.company_name or ticker

            # 한국 주식만 처리 (6자리 숫자 또는 .KS/.KQ 형식)
            clean_ticker = ticker.split('.')[0]
            if not clean_ticker.isdigit():
                logger.debug(f"[{idx}/{len(stocks)}] {ticker} - 한국 주식 아님, 스킵")
                continue

            logger.info(f"[{idx}/{len(stocks)}] {ticker} ({company_name}) 처리 중...")

            try:
                # 투자자별 매매 데이터 가져오기
                trades_data = fetch_investor_data_from_naver(ticker, start_date, end_date)

                if trades_data:
                    saved = save_investor_trades(db, ticker, trades_data)
                    total_saved += saved
                    success_count += 1
                    logger.info(f"  ✓ {ticker}: {saved}건 저장 완료")
                else:
                    logger.warning(f"  ✗ {ticker}: 데이터 없음")
                    failed_count += 1

                # API 호출 제한 방지를 위한 대기
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"  ✗ {ticker}: 오류 발생 - {e}")
                failed_count += 1
                continue

        logger.info("=" * 70)
        logger.info("데이터 수집 완료!")
        logger.info(f"총 종목 수: {len(stocks)}")
        logger.info(f"성공: {success_count}, 실패: {failed_count}")
        logger.info(f"총 저장 건수: {total_saved}")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"메인 프로세스 오류: {e}", exc_info=True)

    finally:
        db.close()


if __name__ == "__main__":
    main()
