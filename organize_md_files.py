#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MD 파일 정리 스크립트

사용법:
    python organize_md_files.py

기능:
    - 프로젝트 내 MD 파일을 docs 폴더의 카테고리별 하위 폴더로 이동
    - 파일명을 통일된 형식으로 변경: {파일내용}-{문서유형}-{날짜}.md
    - 예외 파일 목록에 있는 파일은 이동하지 않음

예외 파일:
    - README.md: 프로젝트 메인 README
    - README_KOREA_STOCKS.md: 한국 주식 README
    - start_hsl.md: HSL 시작 가이드 (루트 위치 유지)
"""
import os
import sys
import shutil
from datetime import datetime
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 기준 경로
BASE_DIR = Path(r"F:\hhstock")
DOCS_DIR = BASE_DIR / "docs"

# 날짜 형식 (yyyyMMdd)
DATE_STR = "20251007"

# 예외 파일 목록 (정리 대상에서 제외)
EXCLUDED_FILES = {
    "README.md",              # 프로젝트 메인 README
    "README_KOREA_STOCKS.md", # 한국 주식 README
    "start_hsl.md",           # HSL 시작 가이드 (루트 유지)
}

# 파일 이동 매핑
file_mappings = {
    # Architecture
    "ARCHITECTURE.md": "docs/architecture/시스템아키텍처-개발-20251007.md",
    "아키텍처정의서.md": "docs/architecture/아키텍처정의서-개발-20251007.md",
    "운영서버분산아키텍처.md": "docs/architecture/운영서버분산아키텍처-개발-20251007.md",

    # Development Logs
    "CREATE_WORK_20250829_Init.md": "docs/development-logs/초기설정-개발-20250829.md",
    "CREATE_WORK_20250830_5year_StockData.md": "docs/development-logs/5년주가데이터-개발-20250830.md",
    "CREATE_WORK_20250830_ALL_KOSPI.md": "docs/development-logs/코스피전종목-개발-20250830.md",
    "CREATE_WORK_20250830_Backend.md": "docs/development-logs/백엔드개발-개발-20250830.md",
    "DEBUG_WORK_20250831_Crawling_DB.md": "docs/development-logs/크롤링DB-수정-20250831.md",
    "DEBUG_WORK_20250831_DASHBOARDS_WEBAPP.md": "docs/development-logs/대시보드웹앱-수정-20250831.md",
    "DEBUG_WORK_20250901_Chart.md": "docs/development-logs/차트-수정-20250901.md",
    "DASHBOARD_FIXES_LOG.md": "docs/development-logs/대시보드수정-수정-20251007.md",
    "docs/GRAFANA_BUGFIX_20250924.md": "docs/development-logs/그라파나버그픽스-수정-20250924.md",

    # User Manuals
    "USER_MANUAL_20250829_Grafana.md": "docs/user-manuals/그라파나-가이드-20250829.md",
    "USER_MANUAL_20250829_Init.md": "docs/user-manuals/초기설정-가이드-20250829.md",
    "USER_MANUAL_20250830_KoreanStockGrafana.md": "docs/user-manuals/한국주식그라파나-가이드-20250830.md",
    "USER_MANUAL_20250831.md": "docs/user-manuals/시스템-가이드-20250831.md",
    "USER_MANUAL_20250831_INDICATOR_ADDED.md": "docs/user-manuals/지표추가-가이드-20250831.md",
    "USER_MANUAL_20250901_Grafana.md": "docs/user-manuals/그라파나고급-가이드-20250901.md",
    "start_guide_20251004.md": "docs/user-manuals/시작가이드-가이드-20251004.md",
    # "start_guide_hsl_for_claude.md": 이미 start_hsl.md로 루트에 이동됨 (예외 파일)
    "auto_trading_guide_20251004.md": "docs/user-manuals/자동매매-가이드-20251004.md",
    "rsi_ma_trading_system_guide_20251004.md": "docs/user-manuals/RSIMA트레이딩-가이드-20251004.md",
    "docs/DATABASE_USER_MANUAL.md": "docs/user-manuals/데이터베이스-가이드-20251007.md",
    "docs/SCREENING_BACKTESTING_USER_MANUAL_KO.md": "docs/user-manuals/스크리닝백테스팅-가이드-20251007.md",

    # Work Summaries
    "work_summary_2025-09-23.md": "docs/work-summaries/작업요약-개발-20250923.md",
    "WORK_SUMMARY_2025-09-25.md": "docs/work-summaries/작업요약-개발-20250925.md",
    "WORK_SUMMARY_2025-09-26.md": "docs/work-summaries/작업요약-개발-20250926.md",
    "Technical_Indicators_Dashboard_Development_Summary.md": "docs/work-summaries/기술지표대시보드-개발-20251007.md",

    # Planning
    "이관계획서.md": "docs/planning/이관계획서-개발-20251007.md",
    "인터페이스정의서.md": "docs/planning/인터페이스정의서-개발-20251007.md",
    "20251005_지표분석.md": "docs/planning/지표분석-개발-20251005.md",
    "2025-10-01_RSI투자프로그램.md": "docs/planning/RSI투자프로그램-개발-20251001.md",
    "2025-10-01_종목수집작업.md": "docs/planning/종목수집작업-개발-20251001.md",

    # Strategies
    "strategies/BB_BREAKOUT_MA_TOUCH_STRATEGY_GUIDE.md": "docs/strategies/볼린저밴드전략-가이드-20251007.md",
    "docs/STOCK_SCREENING_BACKTESTING_SYSTEM_20250924.md": "docs/strategies/스크리닝백테스팅시스템-개발-20250924.md",
    "docs/SCREENING_STRATEGY_SYSTEM_DEVELOPMENT_20250924.md": "docs/strategies/스크리닝전략시스템-개발-20250924.md",

    # Deployment
    "docs/COMPREHENSIVE_INDICATORS_DEPLOYMENT_20250924.md": "docs/deployment/포괄적지표배포-개발-20250924.md",

    # Guides
    "claude_working_hang.md": "docs/guides/claude_working_hang-가이드-20251007.md",
}

def create_directory_if_not_exists(file_path):
    """디렉토리가 없으면 생성"""
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        print(f"✓ 디렉토리 생성: {directory}")

def move_file(source, destination):
    """파일 이동"""
    # 예외 파일 체크
    source_filename = os.path.basename(source)
    if source_filename in EXCLUDED_FILES:
        print(f"⊘ 제외됨 (예외 파일): {source}")
        return None  # 예외 처리된 파일

    source_path = BASE_DIR / source
    dest_path = BASE_DIR / destination

    if not source_path.exists():
        print(f"✗ 파일 없음: {source}")
        return False

    create_directory_if_not_exists(dest_path)

    try:
        shutil.move(str(source_path), str(dest_path))
        print(f"✓ 이동: {source} → {destination}")
        return True
    except Exception as e:
        print(f"✗ 오류: {source} - {e}")
        return False

def move_claude_guide_folder():
    """claude-code-expert-guide 폴더 이동"""
    source = BASE_DIR / "claude-code-expert-guide"
    destination = DOCS_DIR / "guides" / "claude-code-expert-guide"

    if not source.exists():
        print(f"✗ 폴더 없음: claude-code-expert-guide")
        return False

    try:
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(source), str(destination))
        print(f"✓ 폴더 이동: claude-code-expert-guide → docs/guides/")
        return True
    except Exception as e:
        print(f"✗ 폴더 이동 오류: {e}")
        return False

def create_deployment_directory():
    """deployment 디렉토리 생성"""
    deployment_dir = DOCS_DIR / "deployment"
    if not deployment_dir.exists():
        deployment_dir.mkdir(parents=True)
        print(f"✓ 디렉토리 생성: {deployment_dir}")

def main():
    print("=" * 80)
    print("MD 파일 정리 시작")
    print("=" * 80)

    # deployment 디렉토리 생성
    create_deployment_directory()

    # 개별 파일 이동
    success_count = 0
    fail_count = 0
    excluded_count = 0

    for source, destination in file_mappings.items():
        result = move_file(source, destination)
        if result is True:
            success_count += 1
        elif result is None:
            excluded_count += 1
        else:
            fail_count += 1

    # claude-code-expert-guide 폴더 이동
    if move_claude_guide_folder():
        success_count += 1
    else:
        fail_count += 1

    print("=" * 80)
    print(f"작업 완료: 성공 {success_count}개, 실패 {fail_count}개, 제외 {excluded_count}개")
    print("=" * 80)

if __name__ == "__main__":
    main()
