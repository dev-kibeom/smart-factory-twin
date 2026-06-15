from src.database import Base  # database.py의 글로벌 싱글톤 Base 인입
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func


# 이제 하부의 TimestampMixin을 상속받는 모든 테이블 모델들이
# 단 하나의 정격 메타데이터 링커(src.database.Base)로 정합됩니다.
class TimestampMixin:
    """모든 비즈니스 트랜잭션 행위의 추적 무결성을 사수하기 위한 시간 믹스인"""

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
