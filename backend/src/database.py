import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 환경 변수로부터 격리된 VLAN 내 PostgreSQL 주소 수수
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://carbon_admin:secure_password_1234@postgres:5432/carbon_db",
)

# [FRS-08.1] 커넥션 풀 고갈 및 부하 마진 제어를 위한 QueuePool 엔진 튜닝
engine = create_engine(
    DATABASE_URL,
    pool_size=20,  # 기본 유지 커넥션 수 수식 제한
    max_overflow=10,  # 트래픽 병목 시 순간 확장 임계치
    pool_timeout=30,  # 데드락 방지용 타임아웃(초)
    pool_pre_ping=True,  # Liveliness 자동 유실 검사 활성화
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
