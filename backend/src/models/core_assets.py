# backend/src/models/core_assets.py
from sqlalchemy import Column, String, Float
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class RobotMaster(Base, TimestampMixin):
    """[ISA-95 Layer 3] AMR 가상 물리 상태 마스터 엔티티 명세"""

    __tablename__ = "robot_master"

    robot_id = Column(
        String, primary_key=True, index=True, comment="로봇 고유 식별 번호"
    )
    system_status = Column(
        String,
        nullable=False,
        default="OFFLINE",
        comment="현재 통신 및 가동 제어 상태",
    )
    inertia = Column(
        Float,
        nullable=False,
        default=4.5,
        comment="최종 최적화된 관성 수치",
    )
    friction = Column(
        Float,
        nullable=False,
        default=0.8,
        comment="최종 최적화된 마찰 계수",
    )

    # 순환 참조 방어: 문자열 지연 평가 기법으로 factory_operations 배정 [relationship]
    work_order_routings = relationship(
        "WorkOrderRouting", back_populates="target_equipment"
    )


class Parts(Base, TimestampMixin):
    """자재 및 제품 마스터 엔티티 (ISA-95 자재 장부 사양)"""

    __tablename__ = "parts"

    id = Column(String, primary_key=True, index=True)
    part_number = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(
        String(50), nullable=False
    )  # Raw Material, WIP, Finished Good
