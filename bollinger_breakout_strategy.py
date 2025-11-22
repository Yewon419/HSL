"""
볼린저밴드 하단 반발 후 이평선 돌파 패턴 스크리닝 전략
현대로템 패턴: 20일/60일 이평 하향돌파 → 볼린저밴드 하단 반발 → 이평선들과 볼린저상단 돌파
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import talib
import warnings
warnings.filterwarnings('ignore')

class BollingerBreakoutStrategy:
    def __init__(self, ma_short=20, ma_long=60, bb_period=20, bb_std=2):
        """
        Parameters:
        - ma_short: 단기 이동평균 (기본 20일)
        - ma_long: 장기 이동평균 (기본 60일)
        - bb_period: 볼린저밴드 기간 (기본 20일)
        - bb_std: 볼린저밴드 표준편차 (기본 2)
        """
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.bb_period = bb_period
        self.bb_std = bb_std

    def calculate_indicators(self, data):
        """기술적 지표 계산"""
        df = data.copy()

        # 이동평균
        df[f'MA{self.ma_short}'] = talib.SMA(df['Close'], timeperiod=self.ma_short)
        df[f'MA{self.ma_long}'] = talib.SMA(df['Close'], timeperiod=self.ma_long)

        # 볼린저밴드
        df['BB_upper'], df['BB_middle'], df['BB_lower'] = talib.BBANDS(
            df['Close'], timeperiod=self.bb_period, nbdevup=self.bb_std,
            nbdevdn=self.bb_std, matype=0
        )

        # RSI
        df['RSI'] = talib.RSI(df['Close'], timeperiod=14)

        # 거래량 이동평균
        df['Volume_MA'] = talib.SMA(df['Volume'], timeperiod=20)

        return df

    def detect_pattern(self, data):
        """
        현대로템 패턴 감지:
        1. 이평선 하향돌파 (20일선 < 60일선, 주가 < 20일선)
        2. 볼린저밴드 하단 근처 터치 후 반발
        3. 20일선, 60일선, 볼린저밴드 상단 돌파
        """
        df = self.calculate_indicators(data)

        if len(df) < max(self.ma_long, self.bb_period) + 10:
            return None

        # 최근 데이터로 패턴 분석
        recent_data = df.tail(30)  # 최근 30일

        results = {
            'ticker': '',
            'current_price': df['Close'].iloc[-1],
            'pattern_score': 0,
            'signals': [],
            'current_date': df.index[-1].strftime('%Y-%m-%d'),
            'technical_data': {}
        }

        # 현재 기술적 지표 값
        current = df.iloc[-1]
        prev = df.iloc[-2]

        results['technical_data'] = {
            'price': current['Close'],
            'ma20': current[f'MA{self.ma_short}'],
            'ma60': current[f'MA{self.ma_long}'],
            'bb_upper': current['BB_upper'],
            'bb_lower': current['BB_lower'],
            'rsi': current['RSI'],
            'volume_ratio': current['Volume'] / current['Volume_MA']
        }

        score = 0

        # 1. 볼린저밴드 하단 반발 확인 (최근 5-10일 내)
        bb_bounce_detected = False
        for i in range(2, min(11, len(recent_data))):
            past_price = recent_data['Close'].iloc[-i]
            past_bb_lower = recent_data['BB_lower'].iloc[-i]

            # 볼린저밴드 하단 근처 터치 (하단의 102% 이내)
            if past_price <= past_bb_lower * 1.02:
                bb_bounce_detected = True
                results['signals'].append(f"{i}일 전 볼린저밴드 하단 터치")
                score += 25
                break

        # 2. 이평선 배열 확인 (과거 하향돌파 → 현재 상향돌파)
        ma_breakthrough = False

        # 과거 하향돌파 상태였는지 확인
        past_bearish = False
        for i in range(5, min(16, len(recent_data))):
            past_data = recent_data.iloc[-i]
            if (past_data['Close'] < past_data[f'MA{self.ma_short}'] and
                past_data[f'MA{self.ma_short}'] < past_data[f'MA{self.ma_long}']):
                past_bearish = True
                break

        # 현재 상향돌파 상태인지 확인
        current_bullish = (current['Close'] > current[f'MA{self.ma_short}'] and
                          current['Close'] > current[f'MA{self.ma_long}'])

        if past_bearish and current_bullish:
            ma_breakthrough = True
            results['signals'].append("이평선 상향돌파 완료")
            score += 30

        # 3. 볼린저밴드 상단 돌파
        bb_upper_break = current['Close'] > current['BB_upper']
        if bb_upper_break:
            results['signals'].append("볼린저밴드 상단 돌파")
            score += 25

        # 4. 거래량 증가 확인
        volume_surge = current['Volume'] > current['Volume_MA'] * 1.2
        if volume_surge:
            results['signals'].append(f"거래량 급증 ({current['Volume']/current['Volume_MA']:.1f}배)")
            score += 10

        # 5. RSI 상승 모멘텀
        if 30 < current['RSI'] < 70 and current['RSI'] > prev['RSI']:
            results['signals'].append(f"RSI 상승 모멘텀 ({current['RSI']:.1f})")
            score += 10

        # 6. 추가 보너스 점수
        if bb_bounce_detected and ma_breakthrough:
            score += 20  # 핵심 패턴 완성 보너스

        results['pattern_score'] = score
        return results if score >= 50 else None

    def screen_stocks(self, tickers, days=100):
        """여러 종목을 스크리닝"""
        results = []

        for ticker in tickers:
            try:
                print(f"분석 중: {ticker}")

                # 데이터 가져오기
                stock = yf.Ticker(ticker)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                data = stock.history(start=start_date, end=end_date)

                if len(data) < self.ma_long + 10:
                    continue

                # 패턴 분석
                pattern_result = self.detect_pattern(data)

                if pattern_result:
                    pattern_result['ticker'] = ticker
                    results.append(pattern_result)
                    print(f"✅ {ticker}: 패턴 점수 {pattern_result['pattern_score']}")
                else:
                    print(f"❌ {ticker}: 패턴 미발견")

            except Exception as e:
                print(f"❌ {ticker}: 오류 - {str(e)}")
                continue

        # 점수순 정렬
        results.sort(key=lambda x: x['pattern_score'], reverse=True)
        return results

    def generate_report(self, results):
        """결과 리포트 생성"""
        print("\n" + "="*80)
        print("볼린저밴드 하단 반발 + 이평선 돌파 패턴 스크리닝 결과")
        print("="*80)

        if not results:
            print("패턴을 만족하는 종목이 없습니다.")
            return

        print(f"\n발견된 종목 수: {len(results)}\n")

        for i, result in enumerate(results, 1):
            print(f"{i}. {result['ticker']} (점수: {result['pattern_score']})")
            print(f"   현재가: {result['current_price']:,.0f}원")
            print(f"   분석일: {result['current_date']}")

            tech_data = result['technical_data']
            print(f"   MA20: {tech_data['ma20']:,.0f} | MA60: {tech_data['ma60']:,.0f}")
            print(f"   BB상단: {tech_data['bb_upper']:,.0f} | BB하단: {tech_data['bb_lower']:,.0f}")
            print(f"   RSI: {tech_data['rsi']:.1f} | 거래량비: {tech_data['volume_ratio']:.1f}배")

            print("   신호:")
            for signal in result['signals']:
                print(f"     • {signal}")
            print()

def main():
    """메인 실행 함수"""
    strategy = BollingerBreakoutStrategy()

    # 한국 주요 종목들 (예시)
    korean_stocks = [
        '005930.KS',  # 삼성전자
        '000660.KS',  # SK하이닉스
        '035420.KS',  # NAVER
        '051910.KS',  # LG화학
        '006400.KS',  # 삼성SDI
        '035720.KS',  # 카카오
        '207940.KS',  # 삼성바이오로직스
        '068270.KS',  # 셀트리온
        '323410.KS',  # 카카오뱅크
        '064350.KS',  # 현대로템 (기준 종목)
        '012330.KS',  # 현대모비스
        '034730.KS',  # SK
        '003670.KS',  # 포스코홀딩스
        '096770.KS',  # SK이노베이션
        '017670.KS',  # SK텔레콤
    ]

    print("볼린저밴드 하단 반발 + 이평선 돌파 패턴 스크리닝 시작")
    print(f"대상 종목 수: {len(korean_stocks)}")
    print("-" * 50)

    # 스크리닝 실행
    results = strategy.screen_stocks(korean_stocks)

    # 결과 리포트
    strategy.generate_report(results)

    # 결과를 JSON으로 저장
    import json
    output_file = 'bollinger_breakout_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n결과가 {output_file}에 저장되었습니다.")

if __name__ == "__main__":
    main()