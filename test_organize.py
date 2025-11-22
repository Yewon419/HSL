#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
organize_md_files.py 테스트 스크립트
"""
import sys
import codecs
from pathlib import Path

# Windows 콘솔 인코딩 설정
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 예외 파일 목록
EXCLUDED_FILES = {
    "README.md",
    "README_KOREA_STOCKS.md",
    "start_hsl.md",
}

def test_exclusion():
    """예외 파일 테스트"""
    test_files = [
        "README.md",
        "README_KOREA_STOCKS.md",
        "start_hsl.md",
        "some_other_file.md",
    ]

    print("=" * 60)
    print("예외 파일 테스트")
    print("=" * 60)

    for filename in test_files:
        is_excluded = filename in EXCLUDED_FILES
        status = "⊘ 제외됨" if is_excluded else "✓ 처리 대상"
        print(f"{status}: {filename}")

    print("=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_exclusion()
