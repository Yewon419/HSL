#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import json
from datetime import datetime
import pandas as pd
import numpy as np

class PortfolioDashboard:
    def __init__(self, db_path='stock_demo.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

    def get_stock_prices(self):
        """최신 주가 데이터 조회"""
        query = """
        SELECT ticker, date, close_price, volume
        FROM stock_prices
        ORDER BY ticker, date DESC
        """
        df = pd.read_sql_query(query, self.conn)

        # 각 종목별 최신 데이터만 추출
        latest_prices = df.groupby('ticker').first().reset_index()
        return latest_prices

    def get_technical_indicators(self):
        """기술 지표 데이터 조회"""
        query = """
        SELECT ticker, date, rsi, macd, macd_signal, bollinger_upper, bollinger_lower, ma_20
        FROM technical_indicators
        ORDER BY ticker, date DESC
        """
        df = pd.read_sql_query(query, self.conn)
        latest_indicators = df.groupby('ticker').first().reset_index()
        return latest_indicators

    def get_ai_recommendations(self):
        """AI 추천 데이터 조회"""
        query = """
        SELECT ticker, recommendation_type as recommendation, confidence_score as confidence, reason as reasoning
        FROM ai_recommendations
        ORDER BY confidence_score DESC
        """
        df = pd.read_sql_query(query, self.conn)
        return df

    def calculate_portfolio_performance(self):
        """포트폴리오 성과 계산"""
        # 샘플 포트폴리오 데이터 (실제로는 portfolio 테이블에서 가져와야 함)
        portfolio = {
            '005930.KS': {'shares': 100, 'avg_price': 70000, 'name': 'Samsung Electronics'},
            'AAPL': {'shares': 50, 'avg_price': 150, 'name': 'Apple Inc.'},
            'NVDA': {'shares': 20, 'avg_price': 250, 'name': 'NVIDIA Corporation'},
            'TSLA': {'shares': 30, 'avg_price': 200, 'name': 'Tesla Inc.'},
        }

        prices = self.get_stock_prices()
        price_dict = dict(zip(prices['ticker'], prices['close_price']))

        portfolio_data = []
        total_investment = 0
        total_current_value = 0

        for ticker, holding in portfolio.items():
            if ticker in price_dict:
                current_price = price_dict[ticker]
                investment = holding['shares'] * holding['avg_price']
                current_value = holding['shares'] * current_price
                pnl = current_value - investment
                pnl_pct = (pnl / investment) * 100 if investment > 0 else 0

                portfolio_data.append({
                    'ticker': ticker,
                    'name': holding['name'],
                    'shares': holding['shares'],
                    'avg_price': holding['avg_price'],
                    'current_price': current_price,
                    'investment': investment,
                    'current_value': current_value,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })

                total_investment += investment
                total_current_value += current_value

        total_pnl = total_current_value - total_investment
        total_pnl_pct = (total_pnl / total_investment) * 100 if total_investment > 0 else 0

        return {
            'portfolio': portfolio_data,
            'total_investment': total_investment,
            'total_current_value': total_current_value,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct
        }

    def generate_html_dashboard(self):
        """HTML 대시보드 생성"""
        portfolio_data = self.calculate_portfolio_performance()
        indicators = self.get_technical_indicators()
        recommendations = self.get_ai_recommendations()

        # 지표 데이터를 딕셔너리로 변환
        indicator_dict = {}
        for _, row in indicators.iterrows():
            indicator_dict[row['ticker']] = {
                'rsi': row['rsi'] if pd.notna(row['rsi']) else 50,
                'macd': row['macd'] if pd.notna(row['macd']) else 0,
                'bb_upper': row['bollinger_upper'] if pd.notna(row['bollinger_upper']) else 0,
                'bb_lower': row['bollinger_lower'] if pd.notna(row['bollinger_lower']) else 0
            }

        html_content = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>주식 포트폴리오 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}

        .stats-overview {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}

        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
            transition: transform 0.3s ease;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
        }}

        .stat-card h3 {{
            margin: 0 0 15px 0;
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .stat-card .value {{
            font-size: 2em;
            font-weight: 700;
            margin: 10px 0;
        }}

        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}

        .portfolio-section {{
            padding: 30px;
        }}

        .section-title {{
            font-size: 1.8em;
            margin-bottom: 25px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}

        .portfolio-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}

        .portfolio-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 15px;
            font-weight: 600;
            text-align: left;
        }}

        .portfolio-table td {{
            padding: 15px;
            border-bottom: 1px solid #eee;
        }}

        .portfolio-table tr:hover {{
            background: #f8f9fa;
        }}

        .charts-section {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
            padding: 30px;
            background: #f8f9fa;
        }}

        .chart-container {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}

        .recommendations {{
            padding: 30px;
        }}

        .recommendation-card {{
            background: white;
            margin: 15px 0;
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid #667eea;
            box-shadow: 0 5px 15px rgba(0,0,0,0.08);
        }}

        .recommendation-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}

        .confidence-badge {{
            background: #667eea;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: 600;
        }}

        .buy {{ border-left-color: #28a745; }}
        .sell {{ border-left-color: #dc3545; }}
        .hold {{ border-left-color: #ffc107; }}

        .refresh-btn {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 25px;
            border-radius: 50px;
            font-size: 1em;
            cursor: pointer;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}

        .refresh-btn:hover {{
            transform: scale(1.05);
        }}

        .timestamp {{
            text-align: center;
            padding: 20px;
            color: #6c757d;
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 주식 포트폴리오 대시보드</h1>
            <p>실시간 투자 현황 및 AI 추천</p>
        </div>

        <div class="stats-overview">
            <div class="stat-card">
                <h3>총 투자금액</h3>
                <div class="value">${portfolio_data['total_investment']:,.0f}</div>
            </div>
            <div class="stat-card">
                <h3>현재 자산가치</h3>
                <div class="value">${portfolio_data['total_current_value']:,.0f}</div>
            </div>
            <div class="stat-card">
                <h3>손익</h3>
                <div class="value {'positive' if portfolio_data['total_pnl'] >= 0 else 'negative'}">
                    ${portfolio_data['total_pnl']:+,.0f}
                </div>
            </div>
            <div class="stat-card">
                <h3>수익률</h3>
                <div class="value {'positive' if portfolio_data['total_pnl_pct'] >= 0 else 'negative'}">
                    {portfolio_data['total_pnl_pct']:+.2f}%
                </div>
            </div>
        </div>

        <div class="portfolio-section">
            <h2 class="section-title">📊 보유 종목 현황</h2>
            <table class="portfolio-table">
                <thead>
                    <tr>
                        <th>종목명</th>
                        <th>보유량</th>
                        <th>평균단가</th>
                        <th>현재가</th>
                        <th>투자금액</th>
                        <th>평가금액</th>
                        <th>손익</th>
                        <th>수익률</th>
                        <th>RSI</th>
                    </tr>
                </thead>
                <tbody>
"""

        for stock in portfolio_data['portfolio']:
            ticker = stock['ticker']
            rsi = indicator_dict.get(ticker, {}).get('rsi', 50)
            rsi_status = "과매수" if rsi > 70 else "과매도" if rsi < 30 else "보통"
            rsi_color = "#dc3545" if rsi > 70 else "#28a745" if rsi < 30 else "#6c757d"

            html_content += f"""
                    <tr>
                        <td><strong>{stock['name']}</strong><br><small>{stock['ticker']}</small></td>
                        <td>{stock['shares']:,}주</td>
                        <td>${stock['avg_price']:,.0f}</td>
                        <td>${stock['current_price']:,.0f}</td>
                        <td>${stock['investment']:,.0f}</td>
                        <td>${stock['current_value']:,.0f}</td>
                        <td class="{'positive' if stock['pnl'] >= 0 else 'negative'}">${stock['pnl']:+,.0f}</td>
                        <td class="{'positive' if stock['pnl_pct'] >= 0 else 'negative'}">{stock['pnl_pct']:+.2f}%</td>
                        <td style="color: {rsi_color}"><strong>{rsi:.1f}</strong><br><small>{rsi_status}</small></td>
                    </tr>
"""

        html_content += """
                </tbody>
            </table>
        </div>

        <div class="charts-section">
            <div class="chart-container">
                <h3>자산 배분</h3>
                <canvas id="assetAllocationChart"></canvas>
            </div>
            <div class="chart-container">
                <h3>수익률 분포</h3>
                <canvas id="returnsChart"></canvas>
            </div>
        </div>
"""

        # AI 추천 섹션
        if not recommendations.empty:
            html_content += f"""
        <div class="recommendations">
            <h2 class="section-title">🤖 AI 투자 추천</h2>
"""
            for _, rec in recommendations.iterrows():
                rec_class = rec['recommendation'].lower()
                confidence = float(rec['confidence']) if pd.notna(rec['confidence']) else 0
                html_content += f"""
            <div class="recommendation-card {rec_class}">
                <div class="recommendation-header">
                    <h4>{rec['ticker']} - {rec['recommendation'].upper()}</h4>
                    <span class="confidence-badge">신뢰도 {confidence:.1f}%</span>
                </div>
                <p>{rec['reasoning'] if pd.notna(rec['reasoning']) else '분석 중...'}</p>
            </div>
"""
            html_content += """
        </div>
"""

        # 차트 데이터 준비
        chart_labels = [stock['name'] for stock in portfolio_data['portfolio']]
        chart_values = [stock['current_value'] for stock in portfolio_data['portfolio']]
        returns_data = [stock['pnl_pct'] for stock in portfolio_data['portfolio']]

        html_content += f"""
        <div class="timestamp">
            마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>

    <button class="refresh-btn" onclick="location.reload()">🔄 새로고침</button>

    <script>
        // 자산 배분 차트
        const assetCtx = document.getElementById('assetAllocationChart').getContext('2d');
        new Chart(assetCtx, {{
            type: 'doughnut',
            data: {{
                labels: {chart_labels},
                datasets: [{{
                    data: {chart_values},
                    backgroundColor: [
                        '#FF6384',
                        '#36A2EB',
                        '#FFCE56',
                        '#4BC0C0',
                        '#9966FF',
                        '#FF9F40'
                    ],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 20,
                            font: {{
                                size: 12
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 수익률 차트
        const returnsCtx = document.getElementById('returnsChart').getContext('2d');
        new Chart(returnsCtx, {{
            type: 'bar',
            data: {{
                labels: {chart_labels},
                datasets: [{{
                    label: '수익률 (%)',
                    data: {returns_data},
                    backgroundColor: {returns_data}.map(value => value >= 0 ? '#28a745' : '#dc3545'),
                    borderRadius: 8,
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: false
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return value + '%';
                            }}
                        }}
                    }}
                }}
            }}
        }});

        // 5초마다 자동 새로고침 (선택사항)
        // setInterval(() => location.reload(), 5000);
    </script>
</body>
</html>
"""

        return html_content

    def close(self):
        self.conn.close()

if __name__ == "__main__":
    dashboard = PortfolioDashboard()

    print("Portfolio dashboard generating...")
    html_content = dashboard.generate_html_dashboard()

    with open('portfolio_dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

    print("Dashboard created successfully: portfolio_dashboard.html")
    print("Open the file in your browser!")

    dashboard.close()