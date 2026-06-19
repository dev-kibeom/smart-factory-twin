# backend/src/routers/fault_injection.py
import asyncio
import logging
import json  # 🔌 [인프라 수복] JSON 패킷 직렬화용 빌인더 인입
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from src.services.oee_calculator import oee_engine

logger = logging.getLogger("uvicorn.error")

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
    [Task 4-1 / FRS-07.1] 원격 진단 인터페이스 기반 실시간 센서 고장 주입 API
    """
    try:
        is_fault = request.intensity > 0.0

        # 1. 기존 실시간 OEE 물리 연산 엔진에 결함 상태 즉각 반영 [사수]
        oee_engine.update_fault_state(is_fault=is_fault, intensity=request.intensity)

        # 2. 🔌 [IT-OT 핵심 연격 통전]: 가짜 고장을 넘어 실제 MQTT 브로커망으로 고장 패킷 사출
        try:
            import paho.mqtt.client as mqtt

            # paho-mqtt 1.x / 2.x 전천후 버전 안전 가드 매핑
            if hasattr(mqtt, "CallbackApiVersion"):
                mqtt_client = mqtt.Client(
                    callback_api_version=mqtt.CallbackApiVersion.VERSION2
                )
            else:
                mqtt_client = mqtt.Client()

            # docker-compose로 묶여 있는 통합 MQTT 브로커 세션에 직격 결착
            mqtt_client.connect("172.20.0.10", 1883, 60)

            # 하부 bridge_node.py 가 낚아챌 정격 JSON 규격 명세 조립
            fault_payload = {
                "Target": component_id,
                "Fault_Code": request.fault_code,
                "Intensity": request.intensity,
            }

            # 브릿지가 대기 중인 채널 주소로 전포 사출
            mqtt_client.publish(
                "smart_factory/fault/inject", json.dumps(fault_payload), qos=1
            )
            mqtt_client.disconnect()
            logger.info(
                f"📡 [IT ➔ OT FIELD DISPATCH] MQTT 고장 사출 완정: {fault_payload}"
            )
        except Exception as mqtt_err:
            logger.error(
                f"⚠️ [OT LINK BLOCKED] MQTT 필드망 사출 단계 실패: {str(mqtt_err)}"
            )

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
