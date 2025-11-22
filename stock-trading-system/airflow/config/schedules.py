#!/usr/bin/env python3
"""
Airflow DAG 스케줄 설정

모든 DAG의 스케줄을 중앙에서 관리합니다.
크론 표현식 형식: 분 시 일 월 요일

예시:
- '0 19 * * *' : 매일 오후 7시
- '0 19 * * 1-5' : 평일(월-금) 오후 7시
- '0 9 * * *' : 매일 오전 9시
"""

# ========================================
# 데이터 수집 관련 스케줄
# ========================================

# 누락된 거래일 감지 및 수집 DAG 트리거
# 장 마감 후(오후 3:30) 충분한 시간이 지난 뒤 수행
MISSING_DATE_DETECTION = '0 19 * * *'  # 매일 오후 7시

# 한국 주식 데이터 수집 (주가, 지수, 지표)
# generate_collection_dates DAG에 의해 동적으로 트리거됨
# 스케줄은 참고용 (실제로는 수동/트리거 실행)
DATA_COLLECTION = '0 19 * * 1-5'  # 평일 오후 7시 (참고용)

# 기술적 지표 재계산 DAG
# 수동 실행용 (스케줄 없음)
REBUILD_INDICATORS = None  # 수동 실행 전용

# ========================================
# 모니터링 및 유지보수 스케줄
# ========================================

# 데이터베이스 정합성 체크
DB_HEALTH_CHECK = '0 8 * * *'  # 매일 오전 8시

# 시스템 성능 모니터링
SYSTEM_MONITORING = '*/30 * * * *'  # 30분마다

# ========================================
# 스케줄 딕셔너리 (코드에서 접근용)
# ========================================
SCHEDULES = {
    'missing_date_detection': MISSING_DATE_DETECTION,
    'data_collection': DATA_COLLECTION,
    'rebuild_indicators': REBUILD_INDICATORS,
    'db_health_check': DB_HEALTH_CHECK,
    'system_monitoring': SYSTEM_MONITORING,
}

def get_schedule(schedule_name: str) -> str:
    """
    스케줄 이름으로 크론 표현식 조회

    Args:
        schedule_name: 스케줄 이름 (예: 'data_collection')

    Returns:
        크론 표현식 문자열 또는 None
    """
    return SCHEDULES.get(schedule_name)
