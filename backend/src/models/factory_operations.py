# backend/src/models/factory_operations.py
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin


class WorkOrder(Base, TimestampMixin):
    """Carbon MES 작업 지시서 엔티티"""

    __tablename__ = "work_orders"

    id = Column(String, primary_key=True, index=True)
    work_order_number = Column(String(100), unique=True, nullable=False)
    quantity_target = Column(Integer, nullable=False)
    quantity_completed = Column(Integer, default=0)
    status = Column(
        String, default="Draft"
    )  # Draft, In-Progress, Completed


class WorkOrderRouting(Base, TimestampMixin):
    """로봇 및 설비 단위 세부 라우팅 시퀀스 제어 스키마 """

    __tablename__ = "work_order_routings"

    id = Column(String, primary_key=True, index=True)
    work_order_id = Column(String, ForeignKey("work_orders.id", ondelete="CASCADE"))
    sequence_number = Column(Integer, nullable=False)
    operation_name = Column(
        String(255), nullable=False
    )  # AMR_Fetch, OpenPLC_Assemble 

    # 외래키 연격 및 순환 참조 방어
    target_equipment_id = Column(String, ForeignKey("robot_master.robot_id"))
    status = Column(
        String, default="Pending"
    )  # Pending, In-Progress, Completed 

    target_equipment = relationship("RobotMaster", back_populates="work_order_routings")
