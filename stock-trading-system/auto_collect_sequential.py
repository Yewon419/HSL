#!/usr/bin/env python3
"""
연도별 데이터 수집을 순차적으로 자동 실행하는 스크립트
2021 완료 -> 2023 시작
2022 완료 -> 2024 시작
2023 완료 -> 2025 시작
"""

import subprocess
import time
import os
import sys
from datetime import datetime

def is_process_running(process):
    """프로세스가 실행 중인지 확인"""
    if process is None:
        return False
    return process.poll() is None

def get_progress_from_log(year):
    """로그 파일에서 진척율 확인"""
    log_file = f"collect_missing_{year}.log"
    if not os.path.exists(log_file):
        return None

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines[-50:]):  # 마지막 50줄에서 검색
                if '데이터 수집 완료' in line:
                    return 'COMPLETED'
                if '진척율:' in line:
                    # 진척율: 123/456 (27.0%) 형식에서 추출
                    parts = line.split('진척율:')
                    if len(parts) > 1:
                        return parts[1].strip()
        return None
    except:
        return None

def monitor_and_launch():
    """프로세스 모니터링 및 자동 실행"""
    print("=" * 80)
    print("자동 연도별 데이터 수집 모니터링 시작")
    print("=" * 80)
    print("매핑:")
    print("  2021 완료 -> 2023 시작")
    print("  2022 완료 -> 2024 시작")
    print("  2023 완료 -> 2025 시작")
    print("=" * 80)
    print()

    # 초기 상태
    status = {
        2021: {'next': 2023, 'completed': False, 'started_next': False},
        2022: {'next': 2024, 'completed': False, 'started_next': False},
        2023: {'next': 2025, 'completed': False, 'started_next': False}
    }

    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{current_time}] 상태 확인 중...")

        all_done = True

        for year, info in status.items():
            if info['completed'] and info['started_next']:
                continue  # 이미 완료하고 다음도 시작함

            all_done = False

            # 현재 연도 진척율 확인
            progress = get_progress_from_log(year)

            if progress == 'COMPLETED' and not info['completed']:
                info['completed'] = True
                print(f"  ✓ {year}년 수집 완료!")

                # 다음 연도 시작
                if not info['started_next']:
                    next_year = info['next']
                    print(f"  -> {next_year}년 수집 시작...")

                    # 백그라운드로 다음 연도 수집 시작
                    subprocess.Popen(
                        ['python', 'collect_missing_year_data.py', str(next_year)],
                        cwd=os.getcwd(),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )

                    info['started_next'] = True
                    print(f"  ✓ {next_year}년 수집 프로세스 시작됨")

            elif progress and progress != 'COMPLETED':
                print(f"  {year}년: {progress}")
            elif not info['completed']:
                print(f"  {year}년: 진행 중 (로그 확인 중...)")

        # 다음 연도들의 상태도 확인
        for next_year in [2023, 2024, 2025]:
            next_progress = get_progress_from_log(next_year)
            if next_progress:
                if next_progress == 'COMPLETED':
                    print(f"  ✓ {next_year}년 수집 완료!")
                else:
                    print(f"  {next_year}년: {next_progress}")

        # 모든 작업 완료 확인
        completed_2023 = get_progress_from_log(2023) == 'COMPLETED'
        completed_2024 = get_progress_from_log(2024) == 'COMPLETED'
        completed_2025 = get_progress_from_log(2025) == 'COMPLETED'

        if (status[2021]['completed'] and status[2022]['completed'] and
            status[2023]['completed'] and completed_2023 and
            completed_2024 and completed_2025):
            print("\n" + "=" * 80)
            print("모든 연도 데이터 수집 완료!")
            print("=" * 80)
            break

        # 10초 대기 후 다시 확인
        time.sleep(10)

if __name__ == "__main__":
    try:
        monitor_and_launch()
    except KeyboardInterrupt:
        print("\n모니터링 중단됨")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)