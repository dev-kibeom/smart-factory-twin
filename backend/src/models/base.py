# backend/src/models/base.py
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func

Base = declarative_base()


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
