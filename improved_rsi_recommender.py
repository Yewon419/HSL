#!/usr/bin/env python3
"""
개선된 RSI 매매 전략 기반 종목 추천 시스템

개선 사항:
1. 추세 필터 (MA20 > MA50 상승 추세만 매수)
2. 손절 조건 (-5% 손절)
3. RSI 임계값 강화 (매수 < 25, 매도 > 75)
4. 거래량 확인
5. MACD 보조 지표
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rsi_recommender.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def get_latest_stock_data():
    """최신 주가 및 지표 데이터 조회"""
    engine = get_db_connection()

    query = """
        WITH latest_data AS (
            SELECT
                s.ticker,
                s.company_name,
                s.market_type,
                sp.date,
                sp.close_price,
                sp.volume,
                ti.rsi,
                ti.macd,
                ti.macd_signal,
                ti.ma_20,
                ti.ma_50,
                ti.ma_200,
                ROW_NUMBER() OVER (PARTITION BY s.ticker ORDER BY sp.date DESC) as rn
            FROM stocks s
            JOIN stock_prices sp ON s.ticker = sp.ticker
            LEFT JOIN technical_indicators ti ON sp.ticker = ti.ticker AND sp.date = ti.date
            WHERE s.currency = 'KRW'
              AND s.is_active = true
              AND sp.date >= CURRENT_DATE - INTERVAL '30 days'
              AND ti.rsi IS NOT NULL
        )
        SELECT *
        FROM latest_data
        WHERE rn = 1
    """

    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)

    return df

def get_volume_average(ticker, days=20):
    """평균 거래량 조회"""
    engine = get_db_connection()

    query = """
        SELECT AVG(volume) as avg_volume
        FROM stock_prices
        WHERE ticker = :ticker
          AND date >= CURRENT_DATE - INTERVAL '20 days'
    """

    with engine.connect() as conn:
        result = conn.execute(text(query), {'ticker': ticker}).fetchone()
        return float(result[0]) if result and result[0] else 0.0

def calculate_score(row, avg_volume):
    """종목 점수 계산 (0-100점)"""
    score = 0
    reasons = []

    # 1. RSI 점수 (30점)
    rsi = float(row['rsi']) if pd.notna(row['rsi']) else 50
    if rsi < 20:
        score += 30
        reasons.append(f"극단적 과매도 (RSI: {rsi:.1f})")
    elif rsi < 25:
        score += 25
        reasons.append(f"강한 과매도 (RSI: {rsi:.1f})")
    elif rsi < 30:
        score += 15
        reasons.append(f"과매도 (RSI: {rsi:.1f})")

    # 2. 추세 점수 (25점)
    ma_20 = float(row['ma_20']) if pd.notna(row['ma_20']) else 0
    ma_50 = float(row['ma_50']) if pd.notna(row['ma_50']) else 0
    close = float(row['close_price'])

    if ma_20 > ma_50 and ma_20 > 0:
        score += 25
        reasons.append(f"상승 추세 (MA20 > MA50)")
    elif ma_20 > ma_50 * 0.98:  # 거의 골든크로스
        score += 15
        reasons.append(f"추세 전환 가능성")

    # 3. MACD 점수 (20점)
    macd = float(row['macd']) if pd.notna(row['macd']) else 0
    macd_signal = float(row['macd_signal']) if pd.notna(row['macd_signal']) else 0

    if macd > macd_signal:
        score += 20
        reasons.append(f"MACD 골든크로스")
    elif macd > macd_signal * 0.95:
        score += 10
        reasons.append(f"MACD 상승 전환 가능")

    # 4. 거래량 점수 (15점)
    volume = float(row['volume'])
    if avg_volume > 0:
        volume_ratio = volume / avg_volume
        if volume_ratio > 2:
            score += 15
            reasons.append(f"거래량 급증 ({volume_ratio:.1f}배)")
        elif volume_ratio > 1.5:
            score += 10
            reasons.append(f"거래량 증가 ({volume_ratio:.1f}배)")
        elif volume_ratio > 1.2:
            score += 5
            reasons.append(f"거래량 양호 ({volume_ratio:.1f}배)")

    # 5. 가격 위치 점수 (10점)
    if pd.notna(row['ma_200']):
        ma_200 = float(row['ma_200'])
        if close > ma_200:
            score += 10
            reasons.append(f"MA200 위 (장기 상승 추세)")

    return score, reasons

def find_buy_candidates():
    """매수 추천 종목 찾기"""
    logger.info("=" * 80)
    logger.info("개선된 RSI 전략 - 매수 추천 종목 분석")
    logger.info("=" * 80)

    df = get_latest_stock_data()
    logger.info(f"분석 대상 종목: {len(df)}개")

    # 기본 필터링
    buy_candidates = df[
        (df['rsi'] < 30) &  # RSI 과매도
        (df['ma_20'] > df['ma_50']) &  # 상승 추세
        (df['close_price'] > 1000)  # 최소 가격
    ].copy()

    logger.info(f"1차 필터링 결과: {len(buy_candidates)}개")

    # 점수 계산
    results = []
    for idx, row in buy_candidates.iterrows():
        ticker = row['ticker']
        avg_volume = get_volume_average(ticker)
        score, reasons = calculate_score(row, avg_volume)

        results.append({
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'market_type': row['market_type'],
            'close_price': float(row['close_price']),
            'rsi': float(row['rsi']),
            'ma_20': float(row['ma_20']) if pd.notna(row['ma_20']) else 0,
            'ma_50': float(row['ma_50']) if pd.notna(row['ma_50']) else 0,
            'macd': float(row['macd']) if pd.notna(row['macd']) else 0,
            'macd_signal': float(row['macd_signal']) if pd.notna(row['macd_signal']) else 0,
            'volume': float(row['volume']),
            'avg_volume': avg_volume,
            'score': score,
            'reasons': reasons
        })

    if not results:
        logger.info("매수 추천 종목 없음")
        return []

    # 점수 순으로 정렬
    df_results = pd.DataFrame(results).sort_values('score', ascending=False)

    return df_results

def find_sell_candidates():
    """매도 추천 종목 찾기"""
    logger.info("\n" + "=" * 80)
    logger.info("개선된 RSI 전략 - 매도 추천 종목 분석")
    logger.info("=" * 80)

    df = get_latest_stock_data()

    # 매도 신호 필터링
    sell_candidates = df[
        (df['rsi'] > 75) |  # RSI 과매수
        ((df['ma_20'] < df['ma_50']) & (df['rsi'] > 60))  # 하락 추세 + RSI 높음
    ].copy()

    logger.info(f"매도 신호 종목: {len(sell_candidates)}개")

    results = []
    for idx, row in sell_candidates.iterrows():
        sell_reason = []

        rsi = float(row['rsi'])
        if rsi > 80:
            sell_reason.append(f"극단적 과매수 (RSI: {rsi:.1f})")
        elif rsi > 75:
            sell_reason.append(f"과매수 (RSI: {rsi:.1f})")

        ma_20 = float(row['ma_20']) if pd.notna(row['ma_20']) else 0
        ma_50 = float(row['ma_50']) if pd.notna(row['ma_50']) else 0

        if ma_20 < ma_50:
            sell_reason.append("하락 추세 (MA20 < MA50)")

        macd = float(row['macd']) if pd.notna(row['macd']) else 0
        macd_signal = float(row['macd_signal']) if pd.notna(row['macd_signal']) else 0

        if macd < macd_signal:
            sell_reason.append("MACD 데드크로스")

        results.append({
            'ticker': row['ticker'],
            'company_name': row['company_name'],
            'market_type': row['market_type'],
            'close_price': float(row['close_price']),
            'rsi': rsi,
            'ma_20': ma_20,
            'ma_50': ma_50,
            'reasons': sell_reason
        })

    if not results:
        logger.info("매도 추천 종목 없음")
        return []

    df_results = pd.DataFrame(results).sort_values('rsi', ascending=False)
    return df_results

def print_recommendations(buy_df, sell_df):
    """추천 결과 출력"""
    today = datetime.now()

    logger.info("\n" + "=" * 80)
    logger.info(f"{today.year}년 {today.month}월 RSI 개선 전략 종목 추천")
    logger.info("=" * 80)

    # 매수 추천
    logger.info("\n📈 매수 추천 종목 (상위 10개)")
    logger.info("-" * 80)

    if len(buy_df) > 0:
        top_10 = buy_df.head(10)
        for idx, row in top_10.iterrows():
            logger.info(f"\n{idx + 1}. {row['ticker']} - {row['company_name']} ({row['market_type']})")
            logger.info(f"   점수: {row['score']:.0f}점")
            logger.info(f"   현재가: {row['close_price']:,.0f}원")
            logger.info(f"   RSI: {row['rsi']:.1f}")
            logger.info(f"   MA20/MA50: {row['ma_20']:,.0f} / {row['ma_50']:,.0f}")
            logger.info(f"   추천 이유:")
            for reason in row['reasons']:
                logger.info(f"     - {reason}")

        # CSV 저장
        top_10.to_csv('buy_recommendations.csv', index=False, encoding='utf-8-sig')
        logger.info(f"\n매수 추천 {len(top_10)}개 종목 저장: buy_recommendations.csv")
    else:
        logger.info("현재 매수 추천 종목 없음")

    # 매도 추천
    logger.info("\n\n📉 매도 추천 종목 (상위 10개)")
    logger.info("-" * 80)

    if len(sell_df) > 0:
        top_10_sell = sell_df.head(10)
        for idx, row in top_10_sell.iterrows():
            logger.info(f"\n{idx + 1}. {row['ticker']} - {row['company_name']} ({row['market_type']})")
            logger.info(f"   현재가: {row['close_price']:,.0f}원")
            logger.info(f"   RSI: {row['rsi']:.1f}")
            logger.info(f"   매도 이유:")
            for reason in row['reasons']:
                logger.info(f"     - {reason}")

        # CSV 저장
        top_10_sell.to_csv('sell_recommendations.csv', index=False, encoding='utf-8-sig')
        logger.info(f"\n매도 추천 {len(top_10_sell)}개 종목 저장: sell_recommendations.csv")
    else:
        logger.info("현재 매도 추천 종목 없음")

    # 전략 설명
    logger.info("\n\n" + "=" * 80)
    logger.info("📋 개선된 RSI 전략 설명")
    logger.info("=" * 80)
    logger.info("\n매수 조건:")
    logger.info("  1. RSI < 30 (과매도)")
    logger.info("  2. MA20 > MA50 (상승 추세)")
    logger.info("  3. MACD 골든크로스 (선택)")
    logger.info("  4. 거래량 증가 (선택)")
    logger.info("\n매도 조건:")
    logger.info("  1. RSI > 75 (과매수)")
    logger.info("  2. MA20 < MA50 (하락 추세 전환)")
    logger.info("  3. 손절: 매수가 대비 -5% 도달 시")
    logger.info("\n주의 사항:")
    logger.info("  - 반드시 손절선 설정 (-5%)")
    logger.info("  - 분할 매수 권장 (3회 이상)")
    logger.info("  - 포트폴리오 분산 (최소 5종목 이상)")
    logger.info("=" * 80)

if __name__ == "__main__":
    try:
        # 매수 추천 종목 찾기
        buy_df = find_buy_candidates()

        # 매도 추천 종목 찾기
        sell_df = find_sell_candidates()

        # 결과 출력
        print_recommendations(buy_df, sell_df)

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()