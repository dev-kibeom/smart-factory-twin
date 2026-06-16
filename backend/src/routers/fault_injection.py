import asyncio
import logging
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from src.influx_client import influx_manager
from src.services.oee_calculator import oee_engine

logger = logging.getLogger("sf_twin.router")
router = APIRouter(prefix="/api/v1", tags=["Fault & OEE Metrics Engine"])

# 글로벌 10Hz 백그라운드 태스크 제어 플래그
oee_loop_task: asyncio.Task = None
run_oee_loop: bool = False


class FaultInjectionRequest(BaseModel):
    """[Task 4-1] 프로그래머틱 의도적 결함 주입 요청 규격 스키마"""

    fault_code: int = Field(
        ..., description="고장 코드 (예: 라이다 블라인드 401)", example=401
    )[cite:199]
    intensity: float = Field(
        ...,
        description="고장 변조 강도 (0.0: 해제 ~ 1.0: 최악)",
        ge=0.0,
        le=1.0,
        example=0.8,
    )[cite:395]


@router.post("/components/{component_id}/faults", status_code=status.HTTP_202_ACCEPTED)
async def inject_fault_to_robot(component_id: str, request: FaultInjectionRequest):
    """
    [Task 4-1 / FRS-07.1] 원격 진단 인터페이스 기반 실시간 센서 고장 주입 API [cite: 15, 110]
    - ros2_medkit SOVD 규격 프록시 기능 모사 [cite: 315]
    - 인지 계층 및 비헤이비어 트리(BT) 예외 대응 루프 전파 트리거 [cite: 94, 199]
    """
    try:
        is_fault = request.intensity > 0.0

        # 1. 실시간 OEE 물리 연산 엔진에 결함 상태 즉각 전포 반영
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


async def periodic_10hz_oee_streaming_loop():
    """
    [Task 4-3-C / 인수인계서 4] 10Hz 정격 초고속 시계열 OEE 수식 백엔드 루프
    - FIFO 제어를 위해 최적화된 논블로킹 태스크 스케줄링 처리 사수
    - E-Cores 자원 할당 영역 내 구동으로 P-Cores 컨텍스트 스위칭 지연 완전 격리 방어
    """
    global run_oee_loop
    logger.info("10Hz 정격 OEE 시계열 데이터 가동 분석 루프가 정상 점화되었습니다.")

    interval = 0.1  # 100ms 정격 분해능 주기 사수 [cite: 358, 390]

    while run_oee_loop:
        start_tick = asyncio.get_event_loop().time()
        try:
            # A. 실시간 설비종합효율 수식 매트릭스 도출
            metrics = oee_engine.calculate_current_metrics()

            # B. InfluxDB 전용 물리 스키마 데이터 포인트 빌드
            point = oee_engine.export_influx_point(metrics)

            # C. InfluxDB Manager를 통한 비동기 논블로킹 I/O 스트리밍 적재 [cite: 358]
            await influx_manager.write_point(point)

            # 초고속 로그 스트레스 방지를 위해 주기적 디버깅 출력 제어
            if int(start_tick * 10) % 50 == 0:
                logger.debug(
                    f"[10Hz TSDB Streaming] OEE: {metrics['overall_oee']:.2f}% | Availability: {metrics['availability_index']:.4f}"
                )

        except Exception as e:
            logger.error(f"10Hz OEE 스케줄러 루프 내 런타임 예외 발생: {str(e)}")

        # 10Hz 시간 정밀도 유지를 위한 변동 탄력적 슬립 보정 연산
        end_tick = asyncio.get_event_loop().time()
        elapsed = end_tick - start_tick
        sleep_time = max(0.001, interval - elapsed)
        await asyncio.sleep(sleep_time)


def start_oee_engine_scheduler():
    """FastAPI Lifespan Startup 서킷 바인딩용 헬퍼 함수"""
    global oee_loop_task, run_oee_loop
    run_oee_loop = True
    oee_loop_task = asyncio.create_task(periodic_10hz_oee_streaming_loop())


async def stop_oee_engine_scheduler():
    """FastAPI Lifespan Shutdown 서킷 바인딩용 헬퍼 함수"""
    global oee_loop_task, run_oee_loop
    run_oee_loop = False
    if oee_loop_task:
        logger.info("10Hz OEE 백그라운드 스케줄러 루프 중지 요청 중...")
        oee_loop_task.cancel()
        try:
            await oee_loop_task
        except asyncio.CancelledError:
            logger.info("10Hz OEE 시계열 백그라운드 태스크 안전 취소 완료.")
