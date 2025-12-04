"""
Performance Scoring System (100-point scale)
백테스트 전략 성과 평가 시스템

평가 항목:
- 수익률 (30%): CAGR, 알파, 정보비율
- 리스크 (25%): 샤프비율, 칼마비율, MDD
- 안정성 (20%): 변동성, VaR, 베타
- 일관성 (15%): 승률, 월간 수익률, 연속 손실
- 효율성 (10%): 손익비, 회전율
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import math


@dataclass
class PerformanceMetrics:
    """백테스트 성과 지표"""
    # 수익률 지표
    total_return: float = 0.0
    cagr: float = 0.0

    # 리스크 조정 수익률
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: Optional[float] = None

    # 리스크 지표
    max_drawdown: float = 0.0
    volatility: float = 0.0
    downside_volatility: float = 0.0
    var_95: float = 0.0
    var_99: float = 0.0
    cvar_95: float = 0.0
    beta: float = 1.0

    # 거래 지표
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_holding_period: float = 0.0
    turnover: float = 0.0

    # 일관성 지표
    winning_months_pct: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    # 기타
    num_trades: int = 0
    final_value: float = 0.0

    # 벤치마크 비교 (선택)
    alpha: Optional[float] = None


@dataclass
class PerformanceScore:
    """성과 평가 결과"""
    # 카테고리별 점수 (각 0-100)
    return_score: float = 0.0
    risk_score: float = 0.0
    stability_score: float = 0.0
    consistency_score: float = 0.0
    efficiency_score: float = 0.0

    # 종합 점수
    total_score: float = 0.0
    grade: str = 'F'

    # 분석 결과
    strengths: List[str] = None
    weaknesses: List[str] = None
    recommendations: List[str] = None
    summary: str = ""

    def __post_init__(self):
        if self.strengths is None:
            self.strengths = []
        if self.weaknesses is None:
            self.weaknesses = []
        if self.recommendations is None:
            self.recommendations = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "return_score": round(self.return_score, 1),
            "risk_score": round(self.risk_score, 1),
            "stability_score": round(self.stability_score, 1),
            "consistency_score": round(self.consistency_score, 1),
            "efficiency_score": round(self.efficiency_score, 1),
            "total_score": round(self.total_score, 1),
            "grade": self.grade,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
            "summary": self.summary
        }


class PerformanceScorer:
    """전략 성과 평가 클래스"""

    # 가중치 설정
    WEIGHTS = {
        'return': 0.30,      # 30%
        'risk': 0.25,        # 25%
        'stability': 0.20,   # 20%
        'consistency': 0.15, # 15%
        'efficiency': 0.10   # 10%
    }

    # 등급 기준
    GRADE_THRESHOLDS = {
        'S': 90,
        'A': 80,
        'B': 70,
        'C': 60,
        'D': 50,
        'F': 0
    }

    def score(self, metrics: PerformanceMetrics) -> PerformanceScore:
        """성과 지표를 평가하고 점수 산출"""

        # 카테고리별 점수 계산
        return_score = self._score_returns(metrics)
        risk_score = self._score_risk(metrics)
        stability_score = self._score_stability(metrics)
        consistency_score = self._score_consistency(metrics)
        efficiency_score = self._score_efficiency(metrics)

        # 가중 평균으로 종합 점수 계산
        total_score = (
            return_score * self.WEIGHTS['return'] +
            risk_score * self.WEIGHTS['risk'] +
            stability_score * self.WEIGHTS['stability'] +
            consistency_score * self.WEIGHTS['consistency'] +
            efficiency_score * self.WEIGHTS['efficiency']
        )

        # 등급 부여
        grade = self._assign_grade(total_score)

        # 강점/약점 분석
        component_scores = {
            '수익률': return_score,
            '리스크 관리': risk_score,
            '안정성': stability_score,
            '일관성': consistency_score,
            '거래 효율': efficiency_score
        }
        strengths, weaknesses = self._analyze_strengths_weaknesses(component_scores)

        # 개선 권장사항 생성
        recommendations = self._generate_recommendations(metrics, {
            'return': return_score,
            'risk': risk_score,
            'stability': stability_score,
            'consistency': consistency_score,
            'efficiency': efficiency_score
        })

        # 종합 요약 생성
        summary = self._generate_summary(total_score, grade, metrics)

        return PerformanceScore(
            return_score=return_score,
            risk_score=risk_score,
            stability_score=stability_score,
            consistency_score=consistency_score,
            efficiency_score=efficiency_score,
            total_score=round(total_score, 1),
            grade=grade,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            summary=summary
        )

    def _score_returns(self, metrics: PerformanceMetrics) -> float:
        """수익률 점수 (0-100)"""
        cagr = metrics.cagr

        # 1. 절대 수익률 점수 (70점 만점)
        if cagr >= 0.15:
            absolute_score = 70
        elif cagr >= 0.10:
            absolute_score = 56 + (cagr - 0.10) / 0.05 * 14
        elif cagr >= 0.05:
            absolute_score = 42 + (cagr - 0.05) / 0.05 * 14
        elif cagr >= 0:
            absolute_score = 28 + cagr / 0.05 * 14
        else:
            absolute_score = max(0, 28 + cagr / 0.10 * 28)

        # 2. 상대 성과 점수 (30점 만점)
        relative_score = 0
        if metrics.alpha is not None:
            alpha = metrics.alpha
            ir = metrics.information_ratio or 0

            # 알파 기반 점수 (20점)
            if alpha >= 0.05:
                alpha_score = 20
            elif alpha >= 0:
                alpha_score = 10 + alpha / 0.05 * 10
            else:
                alpha_score = max(0, 10 + alpha / 0.05 * 10)

            # 정보비율 점수 (10점)
            if ir >= 1.0:
                ir_score = 10
            elif ir >= 0:
                ir_score = ir / 1.0 * 10
            else:
                ir_score = max(0, 5 + ir * 5)

            relative_score = alpha_score + ir_score
        else:
            # 벤치마크 없을 경우 절대 점수로 스케일링
            absolute_score = absolute_score / 0.7

        total_return_score = absolute_score + relative_score
        return min(100, max(0, total_return_score))

    def _score_risk(self, metrics: PerformanceMetrics) -> float:
        """리스크 점수 (0-100)"""
        sharpe = metrics.sharpe_ratio
        calmar = metrics.calmar_ratio
        mdd = metrics.max_drawdown

        # 샤프 비율 점수 (50점)
        if sharpe >= 2.0:
            sharpe_score = 50
        elif sharpe >= 1.0:
            sharpe_score = 35 + (sharpe - 1.0) / 1.0 * 15
        elif sharpe >= 0.5:
            sharpe_score = 20 + (sharpe - 0.5) / 0.5 * 15
        else:
            sharpe_score = max(0, sharpe / 0.5 * 20)

        # 칼마 비율 점수 (30점)
        if calmar >= 2.0:
            calmar_score = 30
        elif calmar >= 1.0:
            calmar_score = 20 + (calmar - 1.0) / 1.0 * 10
        elif calmar >= 0.5:
            calmar_score = 10 + (calmar - 0.5) / 0.5 * 10
        else:
            calmar_score = max(0, calmar / 0.5 * 10)

        # MDD 점수 (20점)
        if mdd >= -0.10:
            mdd_score = 20
        elif mdd >= -0.20:
            mdd_score = 10 + (mdd + 0.20) / 0.10 * 10
        else:
            mdd_score = max(0, 10 + (mdd + 0.30) / 0.10 * 10)

        total_risk_score = sharpe_score + calmar_score + mdd_score
        return min(100, max(0, total_risk_score))

    def _score_stability(self, metrics: PerformanceMetrics) -> float:
        """안정성 점수 (0-100)"""
        volatility = metrics.volatility
        var_95 = abs(metrics.var_95)
        beta = metrics.beta

        # 변동성 점수 (40점)
        if volatility <= 0.15:
            vol_score = 40
        elif volatility <= 0.25:
            vol_score = 30 + (0.25 - volatility) / 0.10 * 10
        elif volatility <= 0.40:
            vol_score = 15 + (0.40 - volatility) / 0.15 * 15
        else:
            vol_score = max(0, 15 - (volatility - 0.40) / 0.20 * 15)

        # VaR 점수 (40점)
        if var_95 <= 0.03:
            var_score = 40
        elif var_95 <= 0.05:
            var_score = 30 + (0.05 - var_95) / 0.02 * 10
        elif var_95 <= 0.08:
            var_score = 15 + (0.08 - var_95) / 0.03 * 15
        else:
            var_score = max(0, 15 - (var_95 - 0.08) / 0.05 * 15)

        # 베타 점수 (20점)
        if beta <= 0.8:
            beta_score = 20
        elif beta <= 1.0:
            beta_score = 15 + (1.0 - beta) / 0.2 * 5
        elif beta <= 1.2:
            beta_score = 10 + (1.2 - beta) / 0.2 * 5
        else:
            beta_score = max(0, 10 - (beta - 1.2) / 0.3 * 10)

        total_stability_score = vol_score + var_score + beta_score
        return min(100, max(0, total_stability_score))

    def _score_consistency(self, metrics: PerformanceMetrics) -> float:
        """일관성 점수 (0-100)"""
        win_rate = metrics.win_rate
        winning_months_pct = metrics.winning_months_pct
        max_consecutive_losses = metrics.max_consecutive_losses

        # 승률 점수 (50점)
        if win_rate >= 0.60:
            win_rate_score = 50
        elif win_rate >= 0.50:
            win_rate_score = 40 + (win_rate - 0.50) / 0.10 * 10
        elif win_rate >= 0.40:
            win_rate_score = 25 + (win_rate - 0.40) / 0.10 * 15
        else:
            win_rate_score = max(0, win_rate / 0.40 * 25)

        # 월간 수익률 점수 (30점)
        if winning_months_pct >= 0.70:
            winning_months_score = 30
        elif winning_months_pct >= 0.60:
            winning_months_score = 25 + (winning_months_pct - 0.60) / 0.10 * 5
        elif winning_months_pct >= 0.50:
            winning_months_score = 15 + (winning_months_pct - 0.50) / 0.10 * 10
        else:
            winning_months_score = max(0, winning_months_pct / 0.50 * 15)

        # 연속 손실 점수 (20점) - 낮을수록 좋음
        if max_consecutive_losses <= 2:
            consecutive_score = 20
        elif max_consecutive_losses <= 5:
            consecutive_score = 15 - (max_consecutive_losses - 2) / 3 * 5
        elif max_consecutive_losses <= 10:
            consecutive_score = 10 - (max_consecutive_losses - 5) / 5 * 10
        else:
            consecutive_score = 0

        total_consistency_score = win_rate_score + winning_months_score + consecutive_score
        return min(100, max(0, total_consistency_score))

    def _score_efficiency(self, metrics: PerformanceMetrics) -> float:
        """효율성 점수 (0-100)"""
        profit_factor = metrics.profit_factor
        turnover = metrics.turnover

        # 손익비 점수 (60점)
        if profit_factor >= 2.0:
            pf_score = 60
        elif profit_factor >= 1.5:
            pf_score = 50 + (profit_factor - 1.5) / 0.5 * 10
        elif profit_factor >= 1.0:
            pf_score = 30 + (profit_factor - 1.0) / 0.5 * 20
        else:
            pf_score = max(0, profit_factor / 1.0 * 30)

        # 회전율 점수 (40점) - 적정 수준이 최적
        if turnover <= 0.5:
            # 너무 낮은 회전율
            turnover_score = 20 + turnover / 0.5 * 10
        elif turnover <= 2.0:
            # 최적 범위
            turnover_score = 40
        elif turnover <= 4.0:
            # 높은 회전율
            turnover_score = 40 - (turnover - 2.0) / 2.0 * 15
        else:
            # 과도한 거래
            turnover_score = max(0, 25 - (turnover - 4.0) / 2.0 * 25)

        total_efficiency_score = pf_score + turnover_score
        return min(100, max(0, total_efficiency_score))

    def _assign_grade(self, score: float) -> str:
        """점수에 따른 등급 부여"""
        if score >= self.GRADE_THRESHOLDS['S']:
            return 'S'
        elif score >= self.GRADE_THRESHOLDS['A']:
            return 'A'
        elif score >= self.GRADE_THRESHOLDS['B']:
            return 'B'
        elif score >= self.GRADE_THRESHOLDS['C']:
            return 'C'
        elif score >= self.GRADE_THRESHOLDS['D']:
            return 'D'
        else:
            return 'F'

    def _analyze_strengths_weaknesses(self, scores: Dict[str, float]):
        """강점/약점 분석"""
        strengths = []
        weaknesses = []

        for category, score in scores.items():
            if score >= 80:
                strengths.append(f"{category} 우수 ({score:.1f}점)")
            elif score < 60:
                weaknesses.append(f"{category} 개선 필요 ({score:.1f}점)")

        if not strengths:
            strengths.append("전반적으로 균형잡힌 성과")

        if not weaknesses:
            weaknesses.append("특별한 약점 없음")

        return strengths, weaknesses

    def _generate_recommendations(self, metrics: PerformanceMetrics, scores: Dict[str, float]) -> List[str]:
        """개선 권장사항 생성"""
        recommendations = []

        # 수익률 관련
        if scores['return'] < 60:
            if metrics.cagr < 0.05:
                recommendations.append("수익률 개선: 더 공격적인 전략 또는 진입 조건 강화 고려")
            else:
                recommendations.append("수익률 개선: 포지션 사이징 최적화 검토")

        # 리스크 관련
        if scores['risk'] < 60:
            if metrics.sharpe_ratio < 1.0:
                recommendations.append("리스크 관리: 손절매 기준 강화 또는 포지션 크기 축소")
            if metrics.max_drawdown < -0.20:
                recommendations.append("최대 낙폭 관리: 분산 투자 또는 헤지 전략 도입")

        # 안정성 관련
        if scores['stability'] < 60:
            if metrics.volatility > 0.30:
                recommendations.append("안정성 개선: 변동성이 낮은 종목 또는 전략 혼합")

        # 일관성 관련
        if scores['consistency'] < 60:
            if metrics.win_rate < 0.50:
                recommendations.append("일관성 향상: 진입 신호 정확도 개선 또는 시장 환경 필터링")
            if metrics.max_consecutive_losses > 5:
                recommendations.append("연속 손실 방지: Circuit Breaker 도입 (예: 3연패 시 거래 일시 중단)")

        # 효율성 관련
        if scores['efficiency'] < 60:
            if metrics.profit_factor < 1.5:
                recommendations.append("거래 효율: 익절 목표 상향 또는 진입 조건 엄격화")
            if metrics.turnover > 4.0:
                recommendations.append("거래 빈도 감소: 수수료 절감을 위한 보유 기간 연장 고려")

        if not recommendations:
            recommendations.append("현재 성과 유지 - 지속적 모니터링")
            recommendations.append("시장 환경 변화 대응을 위한 정기적 백테스트 수행")

        return recommendations

    def _generate_summary(self, score: float, grade: str, metrics: PerformanceMetrics) -> str:
        """종합 요약 생성"""
        grade_emojis = {
            'S': '💎',
            'A': '🌟',
            'B': '✨',
            'C': '⚠️',
            'D': '📉',
            'F': '🚨'
        }

        emoji = grade_emojis.get(grade, '')
        sharpe = metrics.sharpe_ratio

        if score >= 90:
            return f"{emoji} 최상급 전략입니다. 샤프 비율 {sharpe:.2f}로 탁월한 리스크 대비 수익을 달성했습니다."
        elif score >= 80:
            return f"{emoji} 우수한 전략입니다. 샤프 비율 {sharpe:.2f}로 리스크 대비 높은 수익을 달성했습니다."
        elif score >= 70:
            return f"{emoji} 양호한 전략입니다. 전반적으로 안정적인 성과를 보였으나 일부 개선 여지가 있습니다."
        elif score >= 60:
            return f"{emoji} 보통 수준의 전략입니다. 일부 지표에서 개선이 필요합니다."
        elif score >= 50:
            return f"{emoji} 개선이 필요한 전략입니다. 리스크 관리 및 수익률 최적화가 시급합니다."
        else:
            return f"{emoji} 재검토가 필요한 전략입니다. 전면적인 전략 수정을 권장합니다."


def calculate_metrics_from_backtest(backtest_result: Dict[str, Any]) -> PerformanceMetrics:
    """
    백테스트 결과에서 성과 지표 계산
    """
    trades = backtest_result.get('trades', [])
    equity_curve = backtest_result.get('equity_curve', [])
    initial_capital = backtest_result.get('initial_capital', 1000000)
    final_value = backtest_result.get('final_value', initial_capital)

    # 기본 지표 계산
    total_return = (final_value - initial_capital) / initial_capital if initial_capital > 0 else 0

    # 거래 기간 (년)
    if equity_curve:
        days = len(equity_curve)
        years = max(days / 252, 0.01)  # 거래일 기준
    else:
        years = 1

    # CAGR
    if total_return > -1:
        cagr = (1 + total_return) ** (1 / years) - 1
    else:
        cagr = -1

    # 거래 통계
    if trades:
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]

        win_rate = len(winning_trades) / len(trades) if trades else 0

        total_win = sum(t.get('pnl', 0) for t in winning_trades)
        total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))

        avg_win = total_win / len(winning_trades) if winning_trades else 0
        avg_loss = total_loss / len(losing_trades) if losing_trades else 0

        profit_factor = total_win / total_loss if total_loss > 0 else float('inf')

        # 연속 손익 계산
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in trades:
            if trade.get('pnl', 0) > 0:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)
    else:
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0

    # 변동성 및 리스크 지표
    if equity_curve and len(equity_curve) > 1:
        returns = []
        for i in range(1, len(equity_curve)):
            prev_val = equity_curve[i-1].get('value', equity_curve[i-1]) if isinstance(equity_curve[i-1], dict) else equity_curve[i-1]
            curr_val = equity_curve[i].get('value', equity_curve[i]) if isinstance(equity_curve[i], dict) else equity_curve[i]
            if prev_val > 0:
                returns.append((curr_val - prev_val) / prev_val)

        if returns:
            volatility = (sum((r - sum(returns)/len(returns))**2 for r in returns) / len(returns)) ** 0.5 * (252 ** 0.5)

            # VaR 95%
            sorted_returns = sorted(returns)
            var_idx = int(len(sorted_returns) * 0.05)
            var_95 = sorted_returns[var_idx] if var_idx < len(sorted_returns) else 0

            # 샤프 비율 (무위험 수익률 3% 가정)
            risk_free_rate = 0.03
            excess_return = cagr - risk_free_rate
            sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        else:
            volatility = 0
            var_95 = 0
            sharpe_ratio = 0
    else:
        volatility = 0
        var_95 = 0
        sharpe_ratio = 0

    # MDD 계산
    if equity_curve:
        peak = 0
        max_drawdown = 0
        for point in equity_curve:
            val = point.get('value', point) if isinstance(point, dict) else point
            if val > peak:
                peak = val
            drawdown = (val - peak) / peak if peak > 0 else 0
            max_drawdown = min(max_drawdown, drawdown)
    else:
        max_drawdown = 0

    # 칼마 비율
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0

    return PerformanceMetrics(
        total_return=total_return,
        cagr=cagr,
        sharpe_ratio=sharpe_ratio,
        calmar_ratio=calmar_ratio,
        max_drawdown=max_drawdown,
        volatility=volatility,
        var_95=var_95,
        beta=1.0,  # 기본값
        win_rate=win_rate,
        profit_factor=profit_factor if profit_factor != float('inf') else 10,
        avg_win=avg_win,
        avg_loss=avg_loss,
        winning_months_pct=0.5,  # 기본값
        max_consecutive_wins=max_consecutive_wins,
        max_consecutive_losses=max_consecutive_losses,
        num_trades=len(trades) if trades else 0,
        final_value=final_value,
        turnover=len(trades) / years if trades and years > 0 else 0
    )


def generate_performance_report(backtest_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    백테스트 결과에서 전체 성과 보고서 생성
    """
    # 지표 계산
    metrics = calculate_metrics_from_backtest(backtest_result)

    # 점수 평가
    scorer = PerformanceScorer()
    score = scorer.score(metrics)

    return {
        "metrics": {
            "total_return": f"{metrics.total_return * 100:.2f}%",
            "cagr": f"{metrics.cagr * 100:.2f}%",
            "sharpe_ratio": round(metrics.sharpe_ratio, 2),
            "calmar_ratio": round(metrics.calmar_ratio, 2),
            "max_drawdown": f"{metrics.max_drawdown * 100:.2f}%",
            "volatility": f"{metrics.volatility * 100:.2f}%",
            "win_rate": f"{metrics.win_rate * 100:.1f}%",
            "profit_factor": round(metrics.profit_factor, 2),
            "num_trades": metrics.num_trades,
            "final_value": round(metrics.final_value, 0)
        },
        "score": score.to_dict()
    }
