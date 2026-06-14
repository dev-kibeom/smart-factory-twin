from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.sql import func
from src.database import Base

class RobotMaster(Base):
    """[ISA-95 Layer 3] AMR 가상 물리 상태 마스터 엔티티 명세"""
    __tablename__ = "robot_master"

    robot_id = Column(String, primary_key=True, index=True, comment="로봇 고유 식별 번호")
    system_status = Column(String, nullable=False, default="OFFLINE", comment="현재 통신 및 가동 제어 상태")
    inertia = Column(Float, nullable=False, default=4.5, comment="최종 최적화된 관성 수치")
    friction = Column(Float, nullable=False, default=0.8, comment="최종 최적화된 마찰 계수")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), default=func.now(), comment="최종 데이터 동기화 시점")
