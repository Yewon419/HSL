"""
Daily Email Report DAG
매일 오후 5시에 주식 기술지표 리포트를 이메일로 자동 발송
"""
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# 기본 설정
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 13),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def send_daily_email_report(**context):
    """일일 이메일 리포트 발송"""
    import smtplib
    import psycopg2
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from datetime import datetime, timedelta

    logger.info("Starting email report generation...")

    # DB 연결
    conn = psycopg2.connect(
        host='postgres',
        port=5432,
        database='stocktrading',
        user='admin',
        password='admin123'
    )
    cursor = conn.cursor()

    # 최신 데이터 날짜 확인
    cursor.execute("SELECT MAX(date) FROM stock_prices")
    latest_date = cursor.fetchone()[0]

    if not latest_date:
        logger.warning("No stock price data found")
        cursor.close()
        conn.close()
        return

    logger.info(f"Using data from {latest_date}")

    # 최신 데이터 조회
    cursor.execute("""
        SELECT
            s.ticker,
            s.company_name,
            sp.close_price as current_price,
            ti.rsi,
            ti.ma_20,
            ti.ma_50,
            ti.macd,
            CASE
                WHEN ti.rsi < 30 THEN '과매도 (매수고려)'
                WHEN ti.rsi > 70 THEN '과매수 (매도고려)'
                ELSE '중립'
            END as rsi_status
        FROM stocks s
        JOIN stock_prices sp ON s.ticker = sp.ticker
        JOIN technical_indicators ti ON s.ticker = ti.ticker AND sp.date = ti.date
        WHERE sp.date = %s
        ORDER BY ti.rsi ASC
    """, (latest_date,))

    data = cursor.fetchall()
    cursor.close()
    conn.close()

    if not data:
        logger.warning("No data to send")
        return

    logger.info(f"Found {len(data)} stocks to report")

    # 이메일 본문 생성
    html_content = f"""
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
    <p><strong>날짜:</strong> {latest_date}</p>
    <p><strong>총 종목 수:</strong> {len(data)}</p>

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
"""

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
    oversold = [row for row in data if row[3] and row[3] < 30]
    overbought = [row for row in data if row[3] and row[3] > 70]

    if oversold:
        html_content += f"        <li><strong>과매도 종목 ({len(oversold)}개):</strong> "
        html_content += ", ".join([f"{row[1]}({row[0]})" for row in oversold])
        html_content += "</li>\n"

    if overbought:
        html_content += f"        <li><strong>과매수 종목 ({len(overbought)}개):</strong> "
        html_content += ", ".join([f"{row[1]}({row[0]})" for row in overbought])
        html_content += "</li>\n"

    html_content += f"""
    </ul>

    <hr>
    <p style="color: gray; font-size: 12px;">
        Happy Stock Life 자동매매 시스템<br>
        발송 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        이 메일은 자동으로 생성되었습니다.
    </p>
</body>
</html>
"""

    # 이메일 설정
    sender_email = "windgarden419@gmail.com"
    sender_password = "qcchscmwicwaeyzt"
    recipient_email = "windgarden05@gmail.com"

    # 이메일 작성
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📊 주식 기술지표 리포트 - {latest_date}"
    msg['From'] = sender_email
    msg['To'] = recipient_email

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    # 이메일 전송
    logger.info("Sending email...")
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {recipient_email}")
        logger.info(f"Stocks: {len(data)}, Oversold: {len(oversold)}, Overbought: {len(overbought)}")

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise

# DAG 정의
dag = DAG(
    'daily_email_report',
    default_args=default_args,
    description='매일 오후 5시에 주식 기술지표 리포트를 이메일로 발송',
    schedule_interval='0 8 * * *',  # 매일 08:00 UTC (17:00 KST)
    catchup=False,
    tags=['email', 'report', 'daily'],
)

# Task 정의
send_email_task = PythonOperator(
    task_id='send_daily_email_report',
    python_callable=send_daily_email_report,
    dag=dag,
)

send_email_task
