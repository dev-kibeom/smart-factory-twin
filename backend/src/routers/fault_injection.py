# backend/src/routers/fault_injection.py
import asyncio
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from src.services.oee_calculator import oee_engine

logger = logging.getLogger("uvicorn.error")

# 🔌 [핫픽스 수복] main.py의 관문 패스와의 중복 꼬임을 방어하기 위해 프리픽스 체계를 단일화
router = APIRouter(prefix="/api/v1", tags=["Fault & OEE Metrics Engine"])


class FaultInjectionRequest(BaseModel):
    fault_code: int = Field(
        ..., description="고장 코드 (예: 라이다 블라인드 401)", example=401
    )
    intensity: float = Field(
        ...,
        description="고장 변조 강도 (0.0: 해제 ~ 1.0: 최악)",
        ge=0.0,
        le=1.0,
        example=0.8,
    )


@router.post("/components/{component_id}/faults", status_code=status.HTTP_202_ACCEPTED)
async def inject_fault_to_robot(component_id: str, request: FaultInjectionRequest):
    """
    [Task 4-1 / FRS-07.1] 원격 진단 인터페이스 기반 실시간 센서 고장 주입 API [cite: 199]
    """
    try:
        is_fault = request.intensity > 0.0

        # 실시간 OEE 물리 연산 엔진에 결함 상태 즉각 전포 반영
        oee_engine.update_fault_state(is_fault=is_fault, intensity=request.intensity)

        logger.info(
            f"[고장 주입 성공] Target: {component_id} | "
            f"Fault Code: {request.fault_code} | Intensity: {request.intensity}"
        )

        return {
            "status": "FAULT_PROVOKED_SUCCESSFULLY",
            "target_component": component_id,
            "fault_code": request.fault_code,
            "current_intensity": request.intensity,
            "impact_on_oee": "Downtime counter is running proportionally.",
        }
    except Exception as e:
        logger.critical(f"고장 주입 API 내부 처리 파괴: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Fault Matrix Crack: {str(e)}",
        )
