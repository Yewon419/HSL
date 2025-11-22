#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
중복 MD 파일 정리 스크립트
"""
import os
import sys
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 기준 경로
BASE_DIR = Path(r"F:\hhstock")
STOCK_SYS_DIR = BASE_DIR / "stock-trading-system"

# stock-trading-system에서 삭제할 파일들 (docs로 이미 이동됨)
files_to_remove = [
    "2025-10-01_RSI투자프로그램.md",
    "2025-10-01_종목수집작업.md",
    "CREATE_WORK_20250829_Init.md",
    "CREATE_WORK_20250830_5year_StockData.md",
    "CREATE_WORK_20250830_ALL_KOSPI.md",
    "CREATE_WORK_20250830_Backend.md",
    "DASHBOARD_FIXES_LOG.md",
    "DEBUG_WORK_20250831_Crawling_DB.md",
    "DEBUG_WORK_20250831_DASHBOARDS_WEBAPP.md",
    "DEBUG_WORK_20250901_Chart.md",
    "USER_MANUAL_20250829_Grafana.md",
    "USER_MANUAL_20250829_Init.md",
    "USER_MANUAL_20250830_KoreanStockGrafana.md",
    "USER_MANUAL_20250831.md",
    "USER_MANUAL_20250831_INDICATOR_ADDED.md",
    "USER_MANUAL_20250901_Grafana.md",
    "work_summary_2025-09-23.md",
    "WORK_SUMMARY_2025-09-25.md",
    "WORK_SUMMARY_2025-09-26.md",
]

# stock-trading-system/docs 에서 삭제할 파일들
stock_docs_to_remove = [
    "COMPREHENSIVE_INDICATORS_DEPLOYMENT_20250924.md",
    "DATABASE_USER_MANUAL.md",
    "GRAFANA_BUGFIX_20250924.md",
    "SCREENING_BACKTESTING_USER_MANUAL_KO.md",
    "SCREENING_STRATEGY_SYSTEM_DEVELOPMENT_20250924.md",
    "STOCK_SCREENING_BACKTESTING_SYSTEM_20250924.md",
]

# stock-trading-system/strategies 에서 삭제할 파일
strategies_to_remove = [
    "BB_BREAKOUT_MA_TOUCH_STRATEGY_GUIDE.md",
]

def remove_file(file_path):
    """파일 삭제"""
    if file_path.exists():
        try:
            os.remove(file_path)
            print(f"✓ 삭제: {file_path.relative_to(BASE_DIR)}")
            return True
        except Exception as e:
            print(f"✗ 삭제 실패: {file_path.relative_to(BASE_DIR)} - {e}")
            return False
    else:
        print(f"- 파일 없음: {file_path.relative_to(BASE_DIR)}")
        return False

def main():
    print("=" * 80)
    print("중복 MD 파일 정리 시작")
    print("=" * 80)

    success_count = 0
    skip_count = 0

    # stock-trading-system 루트의 중복 파일 삭제
    print("\n[stock-trading-system 루트 정리]")
    for filename in files_to_remove:
        file_path = STOCK_SYS_DIR / filename
        if remove_file(file_path):
            success_count += 1
        else:
            skip_count += 1

    # stock-trading-system/docs의 중복 파일 삭제
    print("\n[stock-trading-system/docs 정리]")
    for filename in stock_docs_to_remove:
        file_path = STOCK_SYS_DIR / "docs" / filename
        if remove_file(file_path):
            success_count += 1
        else:
            skip_count += 1

    # stock-trading-system/strategies의 중복 파일 삭제
    print("\n[stock-trading-system/strategies 정리]")
    for filename in strategies_to_remove:
        file_path = STOCK_SYS_DIR / "strategies" / filename
        if remove_file(file_path):
            success_count += 1
        else:
            skip_count += 1

    print("=" * 80)
    print(f"작업 완료: 삭제 {success_count}개, 건너뜀 {skip_count}개")
    print("=" * 80)

if __name__ == "__main__":
    main()
