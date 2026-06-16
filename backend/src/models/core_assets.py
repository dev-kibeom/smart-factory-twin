# backend/src/models/core_assets.py
from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class RobotMaster(Base):
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

    # [정격 수복] 시딩 엔진의 정합성 통전을 위한 생성/수정 시점 컬럼 강제 인가
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="최초 자산 등록 시점",
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        default=func.now(),
        comment="최종 데이터 동기화 시점",
    )

    # 타 모델(WorkOrderRouting)에서 전제하고 있는 역참조 관계 포인터를 완벽히 노출
    work_order_routings = relationship(
        "WorkOrderRouting",
        back_populates="target_equipment",
        cascade="all, delete-orphan",
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
