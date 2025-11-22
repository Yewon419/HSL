"""
Application Configuration
환경별 설정 자동 로드 및 관리
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    """
    환경 변수 기반 설정 클래스

    사용법:
        from config import settings

        # DATABASE_URL 자동 생성
        engine = create_engine(settings.DATABASE_URL)

        # 환경 확인
        if settings.is_production():
            # 운영 환경 로직
    """

    # ========================================
    # Environment
    # ========================================
    ENVIRONMENT: str = "development"

    # ========================================
    # Database (개별 값으로 받아서 조합)
    # ========================================
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str = "stocktrading"
    DB_USER: str
    DB_PASSWORD: str

    # ========================================
    # Redis
    # ========================================
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None

    # ========================================
    # InfluxDB
    # ========================================
    INFLUXDB_URL: str
    INFLUXDB_TOKEN: str
    INFLUXDB_ORG: str = "stocktrading"
    INFLUXDB_BUCKET: str = "metrics"

    # ========================================
    # Application URLs
    # ========================================
    BACKEND_URL: str
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str
    GRAFANA_URL: str
    AIRFLOW_URL: str

    # ========================================
    # Security
    # ========================================
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # ========================================
    # External APIs
    # ========================================
    YAHOO_FINANCE_API_KEY: Optional[str] = None

    # ========================================
    # Logging
    # ========================================
    LOG_LEVEL: str = "INFO"

    # ========================================
    # CORS (추가 Origin 지원)
    # ========================================
    EXTRA_CORS_ORIGINS: Optional[str] = None  # 쉼표로 구분된 추가 Origin

    # ========================================
    # 조합된 URL 속성 (자동 생성)
    # ========================================

    @property
    def DATABASE_URL(self) -> str:
        """PostgreSQL 연결 URL"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        """Redis 연결 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    @property
    def CELERY_BROKER_URL(self) -> str:
        """Celery Broker URL (Redis)"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        """Celery Result Backend URL (Redis)"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/0"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def CORS_ORIGINS(self) -> list:
        """
        CORS 허용 Origin 목록
        개발: 모든 origin 허용
        운영: 특정 URL만 허용 + EXTRA_CORS_ORIGINS
        """
        if self.ENVIRONMENT == "production":
            origins = [
                self.FRONTEND_URL,
                self.GRAFANA_URL,
                self.AIRFLOW_URL,
            ]

            # 추가 CORS Origin 지원 (환경 변수로 설정)
            # .env.production에 EXTRA_CORS_ORIGINS=http://example.com,https://app.com 형태로 추가
            if self.EXTRA_CORS_ORIGINS:
                extra = [origin.strip() for origin in self.EXTRA_CORS_ORIGINS.split(',')]
                origins.extend(extra)

            return origins
        else:
            # 개발 환경: 모든 origin 허용
            return ["*"]

    # ========================================
    # 환경 확인 헬퍼 메서드
    # ========================================

    def is_production(self) -> bool:
        """운영 환경 여부"""
        return self.ENVIRONMENT == "production"

    def is_development(self) -> bool:
        """개발 환경 여부"""
        return self.ENVIRONMENT == "development"

    def is_staging(self) -> bool:
        """스테이징 환경 여부"""
        return self.ENVIRONMENT == "staging"

    class Config:
        # 환경별 .env 파일 자동 선택
        # ENVIRONMENT 환경변수에 따라 .env.{ENVIRONMENT} 파일 로드
        # backend 디렉토리의 상위 디렉토리(프로젝트 루트)에서 .env 파일 찾기
        env_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            f".env.{os.getenv('ENVIRONMENT', 'development')}"
        )
        case_sensitive = True

        # .env 파일이 없어도 에러 발생하지 않음 (환경변수로 대체 가능)
        env_file_encoding = 'utf-8'


# ========================================
# 싱글톤 인스턴스
# ========================================
settings = Settings()


# ========================================
# 환경 확인 함수 (편의성)
# ========================================

def is_production() -> bool:
    """운영 환경 여부 확인"""
    return settings.is_production()


def is_development() -> bool:
    """개발 환경 여부 확인"""
    return settings.is_development()


def is_staging() -> bool:
    """스테이징 환경 여부 확인"""
    return settings.is_staging()


# ========================================
# 환경 정보 출력 (디버깅용)
# ========================================

def print_config_info():
    """현재 설정 정보 출력 (민감 정보 제외)"""
    print(f"""
========================================
Stock Trading System Configuration
========================================
Environment: {settings.ENVIRONMENT}
Database: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}
Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}
InfluxDB: {settings.INFLUXDB_URL}
Backend: {settings.BACKEND_URL}
Frontend: {settings.FRONTEND_URL}
Grafana: {settings.GRAFANA_URL}
Airflow: {settings.AIRFLOW_URL}
Log Level: {settings.LOG_LEVEL}
========================================
    """)


# 모듈 로드 시 환경 정보 출력 (개발 환경에서만)
if __name__ == "__main__":
    print_config_info()
