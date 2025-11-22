"""
지표 데이터 이메일 전송 스크립트
"""
import smtplib
import psycopg2
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# DB 연결
conn = psycopg2.connect(
    host='postgres',
    port=5432,
    database='stocktrading',
    user='admin',
    password='admin123'
)
cursor = conn.cursor()

# 최신 데이터 조회
cursor.execute("""
    SELECT
        s.ticker,
        s.company_name,
        sp.close_price as 현재가,
        ti.rsi as RSI,
        ti.ma_20 as MA20,
        ti.ma_50 as MA50,
        ti.macd as MACD,
        CASE
            WHEN ti.rsi < 30 THEN '과매도 (매수고려)'
            WHEN ti.rsi > 70 THEN '과매수 (매도고려)'
            ELSE '중립'
        END as RSI상태
    FROM stocks s
    JOIN stock_prices sp ON s.ticker = sp.ticker
    JOIN technical_indicators ti ON s.ticker = ti.ticker AND sp.date = ti.date
    WHERE sp.date = '2025-11-12'
    ORDER BY ti.rsi ASC
""")

data = cursor.fetchall()
cursor.close()
conn.close()

# 이메일 본문 생성
html_content = """
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        h1 {{ color: #2c3e50; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; }}
        td {{ border: 1px solid #ddd; padding: 10px; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .oversold {{ color: #e74c3c; font-weight: bold; }}
        .overbought {{ color: #3498db; font-weight: bold; }}
        .neutral {{ color: #95a5a6; }}
    </style>
</head>
<body>
    <h1>📊 주식 기술지표 일일 리포트</h1>
    <p><strong>날짜:</strong> 2025-11-12</p>
    <p><strong>총 종목 수:</strong> {}</p>

    <h2>📈 지표 데이터</h2>
    <table>
        <thead>
            <tr>
                <th>종목코드</th>
                <th>종목명</th>
                <th>현재가</th>
                <th>RSI</th>
                <th>MA20</th>
                <th>MA50</th>
                <th>MACD</th>
                <th>상태</th>
            </tr>
        </thead>
        <tbody>
""".format(len(data))

for row in data:
    ticker, name, price, rsi, ma20, ma50, macd, status = row

    # RSI 상태에 따라 클래스 지정
    if '과매도' in status:
        status_class = 'oversold'
    elif '과매수' in status:
        status_class = 'overbought'
    else:
        status_class = 'neutral'

    html_content += f"""
            <tr>
                <td>{ticker}</td>
                <td><strong>{name}</strong></td>
                <td>{price:,.0f}원</td>
                <td><strong>{rsi:.2f}</strong></td>
                <td>{ma20:,.0f}원</td>
                <td>{ma50:,.0f}원</td>
                <td>{macd:,.2f}</td>
                <td class="{status_class}">{status}</td>
            </tr>
    """

html_content += """
        </tbody>
    </table>

    <h2>📌 분석 요약</h2>
    <ul>
"""

# 과매도/과매수 종목 요약
oversold = [row for row in data if row[3] < 30]
overbought = [row for row in data if row[3] > 70]

if oversold:
    html_content += f"        <li><strong>과매도 종목 ({len(oversold)}개):</strong> "
    html_content += ", ".join([f"{row[1]}({row[0]})" for row in oversold])
    html_content += "</li>\n"

if overbought:
    html_content += f"        <li><strong>과매수 종목 ({len(overbought)}개):</strong> "
    html_content += ", ".join([f"{row[1]}({row[0]})" for row in overbought])
    html_content += "</li>\n"

html_content += """
    </ul>

    <hr>
    <p style="color: gray; font-size: 12px;">
        Happy Stock Life 자동매매 시스템<br>
        발송 시각: {}<br>
        이 메일은 자동으로 생성되었습니다.
    </p>
</body>
</html>
""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# 이메일 설정
sender_email = "windgarden419@gmail.com"
sender_password = "qcchscmwicwaeyzt"  # 공백 제거
recipient_email = "windgarden05@gmail.com"

# 이메일 작성
msg = MIMEMultipart('alternative')
msg['Subject'] = f"📊 주식 기술지표 리포트 - 2025-11-12"
msg['From'] = sender_email
msg['To'] = recipient_email

part = MIMEText(html_content, 'html')
msg.attach(part)

# 이메일 전송
print('📧 이메일 전송 중...')
try:
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

    print(f'✅ 이메일 전송 완료!')
    print(f'   수신자: {recipient_email}')
    print(f'   종목 수: {len(data)}개')
    print(f'   과매도: {len(oversold)}개')
    print(f'   과매수: {len(overbought)}개')
except Exception as e:
    print(f'❌ 이메일 전송 실패: {e}')
