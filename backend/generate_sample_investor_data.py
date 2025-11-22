#!/usr/bin/env python
"""
투자자별 매매량 샘플 데이터 생성 스크립트
테스트용으로 랜덤 데이터를 생성합니다.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import random

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import Stock, InvestorTrade

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def generate_sample_investor_data():
    """투자자별 매매량 샘플 데이터 생성"""
    logger.info("=" * 70)
    logger.info("투자자별 매매량 샘플 데이터 생성 시작")
    logger.info("=" * 70)

    db = SessionLocal()

    try:
        # 한국 주식만 조회 (6자리 숫자 종목 코드)
        stocks = db.query(Stock).filter(Stock.is_active == True).all()
        korean_stocks = [s for s in stocks if s.ticker.split('.')[0].isdigit()]

        logger.info(f"한국 주식 {len(korean_stocks)}개에 대해 샘플 데이터 생성")

        # 2025년 1월 1일부터 최근 30일간의 데이터 생성
        end_date = datetime.now().date()
        start_date = datetime(2025, 1, 1).date()

        total_saved = 0

        for stock in korean_stocks:  # 전체 종목
            ticker = stock.ticker
            company_name = stock.company_name or ticker

            logger.info(f"{ticker} ({company_name}) 샘플 데이터 생성 중...")

            current_date = start_date

            while current_date <= end_date:
                # 주말 제외
                if current_date.weekday() < 5:  # 월~금
                    # 랜덤 매매량 생성 (단위: 주)
                    # 외인
                    foreign_buy = random.randint(0, 1000000)
                    foreign_sell = random.randint(0, 1000000)

                    # 기관
                    institution_buy = random.randint(0, 800000)
                    institution_sell = random.randint(0, 800000)

                    # 개인 (외인+기관의 반대로)
                    net_foreign = foreign_buy - foreign_sell
                    net_institution = institution_buy - institution_sell
                    net_individual = -(net_foreign + net_institution)

                    if net_individual > 0:
                        individual_buy = abs(net_individual)
                        individual_sell = 0
                    else:
                        individual_buy = 0
                        individual_sell = abs(net_individual)

                    # 기존 데이터 확인
                    existing = db.query(InvestorTrade).filter(
                        InvestorTrade.ticker == ticker,
                        InvestorTrade.date == current_date
                    ).first()

                    if existing:
                        # 업데이트
                        existing.foreign_buy = foreign_buy
                        existing.foreign_sell = foreign_sell
                        existing.institution_buy = institution_buy
                        existing.institution_sell = institution_sell
                        existing.individual_buy = individual_buy
                        existing.individual_sell = individual_sell
                    else:
                        # 새로 삽입
                        new_trade = InvestorTrade(
                            ticker=ticker,
                            date=current_date,
                            foreign_buy=foreign_buy,
                            foreign_sell=foreign_sell,
                            institution_buy=institution_buy,
                            institution_sell=institution_sell,
                            individual_buy=individual_buy,
                            individual_sell=individual_sell
                        )
                        db.add(new_trade)

                    total_saved += 1

                current_date += timedelta(days=1)

            if total_saved % 100 == 0:
                logger.info(f"  {total_saved}건 저장 완료...")
                db.commit()

        db.commit()

        logger.info("=" * 70)
        logger.info(f"샘플 데이터 생성 완료! 총 {total_saved}건 저장")
        logger.info("=" * 70)

    except Exception as e:
        logger.error(f"오류 발생: {e}", exc_info=True)
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    generate_sample_investor_data()
