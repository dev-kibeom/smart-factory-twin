import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# [정격 교정] docker-compose.yml 명세와 100% 일치하는 프로덕션 연결 사양 인가
# 유저: carbon_admin / 암호: secure_password_1234 / 호스트: postgres (서비스 네임) / DB명: carbon_db
DATABASE_URL = "postgresql://carbon_admin:secure_password_1234@postgres:5432/carbon_db"

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # 런타임 연결 가용성 상시 체크 옵션
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
