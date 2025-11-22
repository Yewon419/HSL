"""
Trading Signal Detector
매매 시그널 감지 및 생성
"""

from sqlalchemy import create_engine, text
from datetime import datetime, date
import logging
from typing import List, Dict, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SignalDetector:
    """
    매매 시그널 감지기

    매수 조건: (RSI < 30) AND (MA20 > MA50)
    매도 조건: RSI > 70
    손절 조건: 현재가 < 매수가 * 0.95 (5% 손실)
    """

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def detect_buy_signals(self, target_date: Optional[date] = None) -> List[Dict]:
        """
        매수 시그널 감지

        조건: RSI < 30 AND MA20 > MA50
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Detecting buy signals for {target_date}")

        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT
                        s.ticker,
                        s.company_name,
                        sp.close_price as current_price,
                        ti.rsi,
                        ti.ma_20,
                        ti.ma_50,
                        ti.ma_200,
                        ti.macd,
                        ti.macd_signal,
                        sp.volume
                    FROM stocks s
                    JOIN stock_prices sp ON s.ticker = sp.ticker
                    JOIN technical_indicators ti ON s.ticker = ti.ticker AND sp.date = ti.date
                    WHERE sp.date = :target_date
                        AND s.currency = 'KRW'
                        AND s.is_active = true
                        AND ti.rsi IS NOT NULL
                        AND ti.rsi < 30
                        AND ti.ma_20 IS NOT NULL
                        AND ti.ma_50 IS NOT NULL
                        AND ti.ma_20 > ti.ma_50
                        AND sp.close_price > 1000
                        AND sp.volume > 10000
                    ORDER BY ti.rsi ASC
                    LIMIT 50
                """)

                result = conn.execute(query, {'target_date': target_date})
                signals = []

                for row in result:
                    # 목표가: 현재가 + 10%
                    target_price = float(row.current_price) * 1.10
                    # 손절가: 현재가 - 5%
                    stop_loss_price = float(row.current_price) * 0.95

                    signal = {
                        'ticker': row.ticker,
                        'company_name': row.company_name,
                        'signal_type': 'BUY',
                        'signal_date': datetime.now(),
                        'current_price': float(row.current_price),
                        'target_price': target_price,
                        'stop_loss_price': stop_loss_price,
                        'rsi': float(row.rsi) if row.rsi else None,
                        'ma_20': float(row.ma_20) if row.ma_20 else None,
                        'ma_50': float(row.ma_50) if row.ma_50 else None,
                        'volume': int(row.volume),
                        'reason': f"RSI={row.rsi:.2f} < 30 AND MA20={row.ma_20:.2f} > MA50={row.ma_50:.2f}"
                    }
                    signals.append(signal)

                logger.info(f"Found {len(signals)} buy signals")
                return signals

        except Exception as e:
            logger.error(f"Error detecting buy signals: {e}")
            raise

    def detect_sell_signals(self, target_date: Optional[date] = None) -> List[Dict]:
        """
        매도 시그널 감지

        조건:
        1. 보유 포지션이 있는 종목 중
        2. RSI > 70
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Detecting sell signals for {target_date}")

        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT
                        tp.id as position_id,
                        tp.ticker,
                        s.company_name,
                        tp.buy_price,
                        tp.quantity,
                        sp.close_price as current_price,
                        ti.rsi,
                        ti.ma_20,
                        ti.ma_50,
                        ((sp.close_price - tp.buy_price) / tp.buy_price * 100) as profit_rate
                    FROM trading_positions tp
                    JOIN stocks s ON tp.ticker = s.ticker
                    JOIN stock_prices sp ON tp.ticker = sp.ticker
                    JOIN technical_indicators ti ON tp.ticker = ti.ticker AND sp.date = ti.date
                    WHERE tp.status = 'OPEN'
                        AND sp.date = :target_date
                        AND ti.rsi IS NOT NULL
                        AND ti.rsi > 70
                    ORDER BY profit_rate DESC
                """)

                result = conn.execute(query, {'target_date': target_date})
                signals = []

                for row in result:
                    profit_loss = (float(row.current_price) - float(row.buy_price)) * row.quantity
                    profit_rate = float(row.profit_rate)

                    signal = {
                        'position_id': row.position_id,
                        'ticker': row.ticker,
                        'company_name': row.company_name,
                        'signal_type': 'SELL',
                        'signal_date': datetime.now(),
                        'buy_price': float(row.buy_price),
                        'current_price': float(row.current_price),
                        'quantity': row.quantity,
                        'profit_loss': profit_loss,
                        'profit_rate': profit_rate,
                        'rsi': float(row.rsi) if row.rsi else None,
                        'reason': f"RSI={row.rsi:.2f} > 70 (과매수), 수익률={profit_rate:.2f}%"
                    }
                    signals.append(signal)

                logger.info(f"Found {len(signals)} sell signals")
                return signals

        except Exception as e:
            logger.error(f"Error detecting sell signals: {e}")
            raise

    def detect_stop_loss_signals(self, target_date: Optional[date] = None) -> List[Dict]:
        """
        손절 시그널 감지

        조건: 현재가 < 매수가 * 0.95 (5% 손실)
        """
        if target_date is None:
            target_date = date.today()

        logger.info(f"Detecting stop-loss signals for {target_date}")

        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT
                        tp.id as position_id,
                        tp.ticker,
                        s.company_name,
                        tp.buy_price,
                        tp.buy_date,
                        tp.quantity,
                        tp.stop_loss_price,
                        sp.close_price as current_price,
                        ti.rsi,
                        ((sp.close_price - tp.buy_price) / tp.buy_price * 100) as loss_rate
                    FROM trading_positions tp
                    JOIN stocks s ON tp.ticker = s.ticker
                    JOIN stock_prices sp ON tp.ticker = sp.ticker
                    JOIN technical_indicators ti ON tp.ticker = ti.ticker AND sp.date = ti.date
                    WHERE tp.status = 'OPEN'
                        AND sp.date = :target_date
                        AND sp.close_price <= tp.stop_loss_price
                    ORDER BY loss_rate ASC
                """)

                result = conn.execute(query, {'target_date': target_date})
                signals = []

                for row in result:
                    profit_loss = (float(row.current_price) - float(row.buy_price)) * row.quantity
                    loss_rate = float(row.loss_rate)

                    signal = {
                        'position_id': row.position_id,
                        'ticker': row.ticker,
                        'company_name': row.company_name,
                        'signal_type': 'STOP_LOSS',
                        'signal_date': datetime.now(),
                        'buy_price': float(row.buy_price),
                        'buy_date': row.buy_date,
                        'current_price': float(row.current_price),
                        'stop_loss_price': float(row.stop_loss_price),
                        'quantity': row.quantity,
                        'profit_loss': profit_loss,
                        'loss_rate': loss_rate,
                        'rsi': float(row.rsi) if row.rsi else None,
                        'reason': f"손절가 도달: 현재가={row.current_price} <= 손절가={row.stop_loss_price} (손실률={loss_rate:.2f}%)"
                    }
                    signals.append(signal)

                logger.info(f"Found {len(signals)} stop-loss signals")
                return signals

        except Exception as e:
            logger.error(f"Error detecting stop-loss signals: {e}")
            raise

    def save_signal(self, signal: Dict) -> int:
        """시그널 저장"""
        try:
            with self.engine.begin() as conn:
                result = conn.execute(text("""
                    INSERT INTO trading_signals (
                        ticker, signal_type, signal_date,
                        current_price, target_price, stop_loss_price,
                        rsi, ma_20, ma_50,
                        status, reason, created_at
                    ) VALUES (
                        :ticker, :signal_type, :signal_date,
                        :current_price, :target_price, :stop_loss_price,
                        :rsi, :ma_20, :ma_50,
                        'PENDING', :reason, :created_at
                    ) RETURNING id
                """), {
                    'ticker': signal['ticker'],
                    'signal_type': signal['signal_type'],
                    'signal_date': signal['signal_date'],
                    'current_price': signal['current_price'],
                    'target_price': signal.get('target_price'),
                    'stop_loss_price': signal.get('stop_loss_price'),
                    'rsi': signal.get('rsi'),
                    'ma_20': signal.get('ma_20'),
                    'ma_50': signal.get('ma_50'),
                    'reason': signal['reason'],
                    'created_at': datetime.now()
                })

                signal_id = result.fetchone()[0]
                logger.info(f"Signal saved: {signal_id}")
                return signal_id

        except Exception as e:
            logger.error(f"Error saving signal: {e}")
            raise

    def detect_all_signals(self, target_date: Optional[date] = None) -> Dict[str, List[Dict]]:
        """모든 시그널 감지"""
        try:
            buy_signals = self.detect_buy_signals(target_date)
        except Exception as e:
            logger.warning(f"Error detecting buy signals: {e}")
            buy_signals = []

        try:
            sell_signals = self.detect_sell_signals(target_date)
        except Exception as e:
            logger.warning(f"Error detecting sell signals (trading_positions table may not exist): {e}")
            sell_signals = []

        try:
            stop_loss_signals = self.detect_stop_loss_signals(target_date)
        except Exception as e:
            logger.warning(f"Error detecting stop-loss signals (trading_positions table may not exist): {e}")
            stop_loss_signals = []

        return {
            'buy': buy_signals,
            'sell': sell_signals,
            'stop_loss': stop_loss_signals
        }
