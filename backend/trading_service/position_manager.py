"""
Trading Position Manager
포지션 관리 서비스
"""

from sqlalchemy import create_engine, text
from datetime import datetime
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PositionManager:
    """포지션 관리자"""

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)

    def open_position(
        self,
        ticker: str,
        buy_price: float,
        quantity: int,
        target_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        포지션 오픈 (매수)

        Args:
            ticker: 종목 코드
            buy_price: 매수가
            quantity: 수량
            target_price: 목표가 (기본: 매수가 + 10%)
            stop_loss_price: 손절가 (기본: 매수가 - 5%)
            notes: 메모

        Returns:
            position_id
        """
        if target_price is None:
            target_price = buy_price * 1.10

        if stop_loss_price is None:
            stop_loss_price = buy_price * 0.95

        try:
            with self.engine.begin() as conn:
                result = conn.execute(text("""
                    INSERT INTO trading_positions (
                        ticker, buy_date, buy_price, quantity,
                        target_price, stop_loss_price,
                        status, notes, created_at
                    ) VALUES (
                        :ticker, :buy_date, :buy_price, :quantity,
                        :target_price, :stop_loss_price,
                        'OPEN', :notes, :created_at
                    ) RETURNING id
                """), {
                    'ticker': ticker,
                    'buy_date': datetime.now(),
                    'buy_price': buy_price,
                    'quantity': quantity,
                    'target_price': target_price,
                    'stop_loss_price': stop_loss_price,
                    'notes': notes,
                    'created_at': datetime.now()
                })

                position_id = result.fetchone()[0]
                logger.info(f"Position opened: {position_id} - {ticker} x {quantity} @ {buy_price}")
                return position_id

        except Exception as e:
            logger.error(f"Error opening position: {e}")
            raise

    def close_position(
        self,
        position_id: int,
        sell_price: float,
        notes: Optional[str] = None
    ) -> bool:
        """
        포지션 클로즈 (매도)

        Args:
            position_id: 포지션 ID
            sell_price: 매도가
            notes: 메모

        Returns:
            성공 여부
        """
        try:
            with self.engine.begin() as conn:
                # 포지션 정보 조회
                result = conn.execute(text("""
                    SELECT buy_price, quantity, notes
                    FROM trading_positions
                    WHERE id = :position_id AND status = 'OPEN'
                """), {'position_id': position_id})

                row = result.fetchone()
                if not row:
                    logger.error(f"Position not found or already closed: {position_id}")
                    return False

                buy_price = float(row[0])
                quantity = row[1]
                existing_notes = row[2] or ""

                # 손익 계산
                profit_loss = (sell_price - buy_price) * quantity
                profit_loss_rate = ((sell_price - buy_price) / buy_price) * 100

                # 메모 병합
                combined_notes = f"{existing_notes}\n[매도] {notes}" if notes else existing_notes

                # 포지션 업데이트
                conn.execute(text("""
                    UPDATE trading_positions
                    SET sell_date = :sell_date,
                        sell_price = :sell_price,
                        profit_loss = :profit_loss,
                        profit_loss_rate = :profit_loss_rate,
                        status = 'CLOSED',
                        notes = :notes,
                        updated_at = :updated_at
                    WHERE id = :position_id
                """), {
                    'position_id': position_id,
                    'sell_date': datetime.now(),
                    'sell_price': sell_price,
                    'profit_loss': profit_loss,
                    'profit_loss_rate': profit_loss_rate,
                    'notes': combined_notes,
                    'updated_at': datetime.now()
                })

                logger.info(
                    f"Position closed: {position_id} - "
                    f"Profit: {profit_loss:,.0f}원 ({profit_loss_rate:.2f}%)"
                )
                return True

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            raise

    def get_open_positions(self) -> List[Dict]:
        """열린 포지션 목록 조회"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        tp.id,
                        tp.ticker,
                        s.company_name,
                        tp.buy_date,
                        tp.buy_price,
                        tp.quantity,
                        tp.target_price,
                        tp.stop_loss_price,
                        sp.close_price as current_price,
                        ((sp.close_price - tp.buy_price) / tp.buy_price * 100) as profit_rate,
                        (sp.close_price - tp.buy_price) * tp.quantity as profit_loss,
                        tp.notes
                    FROM trading_positions tp
                    JOIN stocks s ON tp.ticker = s.ticker
                    LEFT JOIN LATERAL (
                        SELECT close_price
                        FROM stock_prices
                        WHERE ticker = tp.ticker
                        ORDER BY date DESC
                        LIMIT 1
                    ) sp ON true
                    WHERE tp.status = 'OPEN'
                    ORDER BY tp.buy_date DESC
                """))

                positions = []
                for row in result:
                    positions.append({
                        'id': row[0],
                        'ticker': row[1],
                        'company_name': row[2],
                        'buy_date': row[3],
                        'buy_price': float(row[4]),
                        'quantity': row[5],
                        'target_price': float(row[6]) if row[6] else None,
                        'stop_loss_price': float(row[7]) if row[7] else None,
                        'current_price': float(row[8]) if row[8] else None,
                        'profit_rate': float(row[9]) if row[9] else 0,
                        'profit_loss': float(row[10]) if row[10] else 0,
                        'notes': row[11]
                    })

                return positions

        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            raise

    def get_position_history(self, limit: int = 100) -> List[Dict]:
        """포지션 이력 조회"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        tp.id,
                        tp.ticker,
                        s.company_name,
                        tp.buy_date,
                        tp.buy_price,
                        tp.sell_date,
                        tp.sell_price,
                        tp.quantity,
                        tp.profit_loss,
                        tp.profit_loss_rate,
                        tp.status,
                        tp.notes
                    FROM trading_positions tp
                    JOIN stocks s ON tp.ticker = s.ticker
                    ORDER BY tp.updated_at DESC
                    LIMIT :limit
                """), {'limit': limit})

                positions = []
                for row in result:
                    positions.append({
                        'id': row[0],
                        'ticker': row[1],
                        'company_name': row[2],
                        'buy_date': row[3],
                        'buy_price': float(row[4]),
                        'sell_date': row[5],
                        'sell_price': float(row[6]) if row[6] else None,
                        'quantity': row[7],
                        'profit_loss': float(row[8]) if row[8] else 0,
                        'profit_loss_rate': float(row[9]) if row[9] else 0,
                        'status': row[10],
                        'notes': row[11]
                    })

                return positions

        except Exception as e:
            logger.error(f"Error getting position history: {e}")
            raise

    def get_performance_summary(self) -> Dict:
        """수익률 요약"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        COUNT(*) as total_trades,
                        COUNT(CASE WHEN profit_loss > 0 THEN 1 END) as winning_trades,
                        COUNT(CASE WHEN profit_loss < 0 THEN 1 END) as losing_trades,
                        COALESCE(SUM(profit_loss), 0) as total_profit_loss,
                        COALESCE(AVG(profit_loss_rate), 0) as avg_profit_rate,
                        COALESCE(MAX(profit_loss_rate), 0) as max_profit_rate,
                        COALESCE(MIN(profit_loss_rate), 0) as max_loss_rate
                    FROM trading_positions
                    WHERE status = 'CLOSED'
                """))

                row = result.fetchone()

                total_trades = row[0]
                winning_trades = row[1]
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

                return {
                    'total_trades': total_trades,
                    'winning_trades': winning_trades,
                    'losing_trades': row[2],
                    'win_rate': win_rate,
                    'total_profit_loss': float(row[3]),
                    'avg_profit_rate': float(row[4]),
                    'max_profit_rate': float(row[5]),
                    'max_loss_rate': float(row[6])
                }

        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            raise
