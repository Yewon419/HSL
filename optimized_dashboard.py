#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Enhanced Portfolio Dashboard with Optimization Results
포트폴리오 최적화 결과를 포함한 향상된 대시보드
"""

import json
import sqlite3
import pandas as pd
from datetime import datetime
from portfolio_optimizer import PortfolioOptimizer

class OptimizedDashboard:
    def __init__(self, db_path='stock_demo.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def load_optimization_results(self):
        """최적화 결과 로드"""
        try:
            with open('optimized_portfolio.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print("No optimization results found. Running optimization...")
            optimizer = PortfolioOptimizer(self.db_path)
            result = optimizer.generate_optimal_portfolio()
            optimizer.close()
            return result

    def generate_enhanced_dashboard(self):
        """향상된 대시보드 생성"""
        optimization_data = self.load_optimization_results()

        if 'error' in optimization_data:
            return f"<h1>Error loading optimization data: {optimization_data['error']}</h1>"

        # 차트 데이터 준비
        allocation = optimization_data.get('share_allocation', {})
        stock_scores = optimization_data.get('stock_scores', {})
        metrics = optimization_data.get('expected_metrics', {})

        # 종목별 데이터
        tickers = list(allocation.keys())
        names = [allocation[t]['name'] for t in tickers]
        weights = [allocation[t]['weight'] * 100 for t in tickers]
        amounts = [allocation[t]['actual_amount'] for t in tickers]
        shares = [allocation[t]['shares'] for t in tickers]
        prices = [allocation[t]['current_price'] for t in tickers]

        # 점수 데이터
        score_tickers = list(stock_scores.keys())
        score_values = list(stock_scores.values())

        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 최적화 포트폴리오 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0,0,0,0.15);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.8em;
            font-weight: 300;
            margin-bottom: 10px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }}

        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}

        .optimization-status {{
            background: {'#28a745' if optimization_data.get('optimization_success') else '#ffc107'};
            color: white;
            padding: 15px;
            text-align: center;
            font-weight: 600;
            font-size: 1.1em;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 25px;
            padding: 40px;
            background: #f8f9fa;
        }}

        .stat-card {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }}

        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(135deg, #667eea, #764ba2);
        }}

        .stat-card:hover {{
            transform: translateY(-8px);
            box-shadow: 0 15px 35px rgba(0,0,0,0.15);
        }}

        .stat-card .icon {{
            font-size: 2.5em;
            margin-bottom: 15px;
            opacity: 0.8;
        }}

        .stat-card h3 {{
            color: #6c757d;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        .stat-card .value {{
            font-size: 2.2em;
            font-weight: 700;
            color: #333;
            margin-bottom: 5px;
        }}

        .stat-card .change {{
            font-size: 0.9em;
            font-weight: 600;
        }}

        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .neutral {{ color: #6c757d; }}

        .content-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            padding: 40px;
        }}

        .section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        }}

        .section-title {{
            font-size: 1.6em;
            font-weight: 600;
            margin-bottom: 25px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}

        .allocation-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        .allocation-table th {{
            background: #f8f9fa;
            color: #333;
            padding: 15px;
            font-weight: 600;
            text-align: left;
            border-bottom: 2px solid #dee2e6;
        }}

        .allocation-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        .allocation-table tr:hover {{
            background: #f8f9fa;
        }}

        .weight-bar {{
            height: 6px;
            background: #e9ecef;
            border-radius: 3px;
            overflow: hidden;
            margin-top: 5px;
        }}

        .weight-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 3px;
            transition: width 0.3s ease;
        }}

        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin: 20px 0;
            box-shadow: 0 10px 25px rgba(0,0,0,0.08);
        }}

        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            padding: 0 40px 40px;
        }}

        .performance-metrics {{
            background: linear-gradient(135deg, #28a745, #20c997);
            color: white;
            border-radius: 15px;
            padding: 30px;
            margin: 20px 40px;
        }}

        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 25px;
            margin-top: 20px;
        }}

        .metric-item {{
            text-align: center;
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
        }}

        .metric-item .label {{
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 5px;
        }}

        .metric-item .value {{
            font-size: 1.8em;
            font-weight: 700;
        }}

        .footer {{
            background: #f8f9fa;
            padding: 30px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #dee2e6;
        }}

        .refresh-btn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 18px 25px;
            border-radius: 50px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
            transition: all 0.3s ease;
        }}

        .refresh-btn:hover {{
            transform: scale(1.05);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.6);
        }}

        @media (max-width: 768px) {{
            .content-grid {{
                grid-template-columns: 1fr;
            }}
            .stats-grid {{
                grid-template-columns: 1fr;
                padding: 20px;
            }}
            .chart-grid {{
                grid-template-columns: 1fr;
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI 최적화 포트폴리오</h1>
            <div class="subtitle">자동 종목 선택 및 포트폴리오 최적화 시스템</div>
        </div>

        <div class="optimization-status">
            {'최적화 성공: 수학적 최적 비중 적용' if optimization_data.get('optimization_success') else '동일 비중 적용: 데이터 부족으로 인한 대안'}
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="icon">💰</div>
                <h3>총 투자금액</h3>
                <div class="value">{optimization_data.get('investment_amount', 0):,}</div>
                <div class="change neutral">KRW</div>
            </div>
            <div class="stat-card">
                <div class="icon">📊</div>
                <h3>선택된 종목 수</h3>
                <div class="value">{len(allocation)}</div>
                <div class="change neutral">개 종목</div>
            </div>
            <div class="stat-card">
                <div class="icon">🎯</div>
                <h3>기대 연간수익률</h3>
                <div class="value positive">{metrics.get('annual_return', 0)*100:.1f}%</div>
                <div class="change neutral">연율화</div>
            </div>
            <div class="stat-card">
                <div class="icon">📈</div>
                <h3>샤프 비율</h3>
                <div class="value {'positive' if metrics.get('sharpe_ratio', 0) > 1 else 'neutral'}">{metrics.get('sharpe_ratio', 0):.2f}</div>
                <div class="change neutral">위험대비수익</div>
            </div>
            <div class="stat-card">
                <div class="icon">⚠️</div>
                <h3>기대 변동성</h3>
                <div class="value neutral">{metrics.get('annual_volatility', 0)*100:.1f}%</div>
                <div class="change neutral">연율화</div>
            </div>
            <div class="stat-card">
                <div class="icon">📉</div>
                <h3>최대 손실</h3>
                <div class="value negative">{metrics.get('max_drawdown', 0)*100:.1f}%</div>
                <div class="change neutral">최대 낙폭</div>
            </div>
        </div>

        <div class="performance-metrics">
            <h2 style="margin-bottom: 10px;">📊 포트폴리오 성과 예측</h2>
            <p style="opacity: 0.9;">과거 데이터 기반 수학적 최적화 결과</p>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="label">연간 기대수익률</div>
                    <div class="value">{metrics.get('annual_return', 0)*100:.1f}%</div>
                </div>
                <div class="metric-item">
                    <div class="label">연간 변동성</div>
                    <div class="value">{metrics.get('annual_volatility', 0)*100:.1f}%</div>
                </div>
                <div class="metric-item">
                    <div class="label">샤프 비율</div>
                    <div class="value">{metrics.get('sharpe_ratio', 0):.2f}</div>
                </div>
                <div class="metric-item">
                    <div class="label">최대 낙폭</div>
                    <div class="value">{metrics.get('max_drawdown', 0)*100:.1f}%</div>
                </div>
            </div>
        </div>

        <div class="content-grid">
            <div class="section">
                <h2 class="section-title">🏆 종목 선택 점수</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    <table class="allocation-table">
                        <thead>
                            <tr>
                                <th>종목</th>
                                <th>점수</th>
                                <th>등급</th>
                            </tr>
                        </thead>
                        <tbody>
"""

        # 종목별 점수 테이블
        for ticker, score in stock_scores.items():
            name = optimization_data.get('share_allocation', {}).get(ticker, {}).get('name', ticker)
            grade = 'S' if score >= 3.5 else 'A' if score >= 3.0 else 'B' if score >= 2.5 else 'C'
            grade_color = '#28a745' if grade == 'S' else '#17a2b8' if grade == 'A' else '#ffc107' if grade == 'B' else '#dc3545'

            html_content += f"""
                            <tr>
                                <td><strong>{ticker}</strong><br><small>{name}</small></td>
                                <td>{score:.2f}</td>
                                <td><span style="background: {grade_color}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{grade}</span></td>
                            </tr>
"""

        html_content += f"""
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">💼 최적 포트폴리오 배분</h2>
                <div style="max-height: 400px; overflow-y: auto;">
                    <table class="allocation-table">
                        <thead>
                            <tr>
                                <th>종목</th>
                                <th>비중</th>
                                <th>주식수</th>
                                <th>투자금액</th>
                            </tr>
                        </thead>
                        <tbody>
"""

        # 포트폴리오 배분 테이블
        for ticker in tickers:
            data = allocation[ticker]
            html_content += f"""
                            <tr>
                                <td>
                                    <strong>{ticker}</strong><br>
                                    <small>{data['name']}</small>
                                </td>
                                <td>
                                    {data['weight']*100:.1f}%
                                    <div class="weight-bar">
                                        <div class="weight-fill" style="width: {data['weight']*100}%"></div>
                                    </div>
                                </td>
                                <td>{data['shares']:,}</td>
                                <td>{data['actual_amount']:,.0f} KRW</td>
                            </tr>
"""

        total_allocated = sum(allocation[t]['actual_amount'] for t in tickers)

        html_content += f"""
                        </tbody>
                    </table>
                    <div style="margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                        <strong>총 배분금액: {total_allocated:,} KRW ({total_allocated/optimization_data.get('investment_amount', 1)*100:.1f}%)</strong>
                    </div>
                </div>
            </div>
        </div>

        <div class="chart-grid">
            <div class="chart-container">
                <h3 style="margin-bottom: 20px;">자산 배분 현황</h3>
                <canvas id="allocationChart"></canvas>
            </div>
            <div class="chart-container">
                <h3 style="margin-bottom: 20px;">종목별 투자금액</h3>
                <canvas id="amountChart"></canvas>
            </div>
            <div class="chart-container">
                <h3 style="margin-bottom: 20px;">종목 선택 점수</h3>
                <canvas id="scoreChart"></canvas>
            </div>
            <div class="chart-container">
                <h3 style="margin-bottom: 20px;">리스크-수익 프로필</h3>
                <canvas id="riskReturnChart"></canvas>
            </div>
        </div>

        <div class="footer">
            <p>최적화 일시: {optimization_data.get('timestamp', datetime.now().isoformat())}</p>
            <p>이 결과는 과거 데이터 기반 수학적 모델링 결과이며, 실제 투자 성과를 보장하지 않습니다.</p>
        </div>
    </div>

    <button class="refresh-btn" onclick="location.reload()">🔄 새로고침</button>

    <script>
        // 차트 데이터
        const tickers = {tickers};
        const names = {names};
        const weights = {weights};
        const amounts = {amounts};
        const scores = {score_values};
        const scoreLabels = {score_tickers};

        // 색상 팔레트
        const colors = [
            '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
            '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
        ];

        // 1. 자산 배분 차트
        const allocationCtx = document.getElementById('allocationChart').getContext('2d');
        new Chart(allocationCtx, {{
            type: 'doughnut',
            data: {{
                labels: names,
                datasets: [{{
                    data: weights,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverBorderWidth: 3
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20,
                            usePointStyle: true,
                            font: {{ size: 12 }}
                        }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.label + ': ' + context.parsed.toFixed(1) + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 2. 투자금액 차트
        const amountCtx = document.getElementById('amountChart').getContext('2d');
        new Chart(amountCtx, {{
            type: 'bar',
            data: {{
                labels: tickers,
                datasets: [{{
                    label: '투자금액 (KRW)',
                    data: amounts,
                    backgroundColor: 'rgba(102, 126, 234, 0.8)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return new Intl.NumberFormat('ko-KR').format(context.parsed.y) + ' KRW';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return new Intl.NumberFormat('ko-KR', {{notation: 'compact'}}).format(value);
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 3. 종목 점수 차트
        const scoreCtx = document.getElementById('scoreChart').getContext('2d');
        new Chart(scoreCtx, {{
            type: 'radar',
            data: {{
                labels: scoreLabels,
                datasets: [{{
                    label: '종목 점수',
                    data: scores,
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2,
                    pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                    pointRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 4,
                        ticks: {{
                            stepSize: 0.5
                        }}
                    }}
                }}
            }}
        }});

        // 4. 리스크-수익 차트
        const riskReturnCtx = document.getElementById('riskReturnChart').getContext('2d');
        new Chart(riskReturnCtx, {{
            type: 'scatter',
            data: {{
                datasets: [{{
                    label: '포트폴리오',
                    data: [{{
                        x: {metrics.get('annual_volatility', 0)*100:.1f},
                        y: {metrics.get('annual_return', 0)*100:.1f}
                    }}],
                    backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    borderColor: 'rgba(40, 167, 69, 1)',
                    pointRadius: 12,
                    pointHoverRadius: 15
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return `수익률: ${{context.parsed.y.toFixed(1)}}%, 변동성: ${{context.parsed.x.toFixed(1)}}%`;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        title: {{
                            display: true,
                            text: '변동성 (%)'
                        }}
                    }},
                    y: {{
                        title: {{
                            display: true,
                            text: '기대수익률 (%)'
                        }}
                    }}
                }}
            }}
        }});

        // 자동 새로고침 (10분마다)
        // setInterval(() => location.reload(), 600000);
    </script>
</body>
</html>
"""

        return html_content

    def close(self):
        self.conn.close()


def main():
    dashboard = OptimizedDashboard()

    print("Generating enhanced optimization dashboard...")
    html_content = dashboard.generate_enhanced_dashboard()

    with open('optimized_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("Enhanced dashboard created: optimized_dashboard.html")
    dashboard.close()


if __name__ == "__main__":
    main()