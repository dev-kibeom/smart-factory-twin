# backend/src/main.py
import os
import jwt
import time
import math
import random
import asyncio

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from contextlib import asynccontextmanager
import json

from src.database import engine, Base, get_db

import src.models.core_assets
import src.models.factory_operations
from src.models import RobotMaster, WorkOrder, WorkOrderRouting
from src.mqtt_consumer import init_mqtt_consumer
from src.api.v1.signaling import router as signaling_router
from src.api.v1.signaling import (
    manager as signaling_manager,
)  # 기존 시그널 허브 연동 추가

# Phase 4 비동기 TSDB 클라이언트 인입
from src.influx_client import influx_async_manager
from influxdb_client import Point

# ===========================================================================
# 🛡️ [Eager Execution] 부팅 blocking 동기화 가드 (Lazy 런타임 우회) [cite: 562]
# ===========================================================================
print("=========================================================================")
print(" [DDL 인프라 엔진] 단일 메타데이터 컨텍스트 기반 스키마 동기화를 시작합니다.")
db_ready = False
for i in range(10):
    try:
        Base.metadata.create_all(bind=engine)
        db_ready = True
        print(
            " ✔ [물리 안착 대성공] work_orders 및 work_order_routings 테이블 생성 완정."
        )
        break
    except OperationalError:
        print(f" ⏳ PostgreSQL 엔진 준비 대기 중... ({i + 1}/10)")
        time.sleep(2)

if not db_ready:
    print(" ❌ 데이터베이스 인프라 통전 최종 실패.")
else:
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    SessionInit = sessionmaker(bind=engine)
    init_db_session = SessionInit()
    try:
        init_db_session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS robot_master (
                robot_id VARCHAR(50) PRIMARY KEY,
                system_status VARCHAR(50),
                inertia DOUBLE PRECISION,
                friction DOUBLE PRECISION,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        )
        init_db_session.commit()

        init_db_session.execute(
            text("""
            INSERT INTO robot_master (robot_id, system_status, inertia, friction)
            VALUES ('amr_01', 'OPERATIONAL', 4.5, 0.8)
            ON CONFLICT (robot_id) DO NOTHING;
        """)
        )
        init_db_session.commit()
        print(
            " 🤖 [자산 시딩 완정] PostgreSQL 물리 엔진 평면에 'amr_01' 기준 정보를 강제 박제했습니다."
        )
    except Exception as seed_err:
        print(f" ❌ [시딩 최종 실패] 인프라 롤백: {str(seed_err)}")
        init_db_session.rollback()
    finally:
        init_db_session.close()

print("=========================================================================")

# JWT 및 보안 구성 프로파일
SECRET_KEY = "carbon_super_secure_secret_key_for_jwt_tokens_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security_jwt_bearer = HTTPBearer()

# 실시간 동적 OEE 상태 전역 메모리 스냅샷 버퍼 선언 [cite: 584]
current_fault_intensity = 0.0
calculated_oee = 100.0

# 백그라운드 태스크 생명주기 제어 변수
oee_streaming_task: Optional[asyncio.Task] = None
keep_streaming: bool = False


async def periodic_10hz_oee_loop():
    """
    [URS-12/FRS-12.2] 설비종합효율(OEE) 동적 실시간 하락 수식 모델 연산 컴포넌트
    - 기존 동기식 @repeat_every 블로킹 루프를 완벽한 비동기 논블로킹 태스크로 개전
    - 인플럭스 시계열 적재와 동시에 Next.js OeeChart 단말로 패킷 실시간 멀티캐스팅
    """
    global current_fault_intensity, calculated_oee, keep_streaming

    interval = 0.1  # 10Hz 정격 분해능 주기 사수 [cite: 175, 403, 690]
    print(
        " 📊 [OEE ENGINE] 10Hz 주기 초고속 시계열 OEE 수식 모델 루프가 기동되었습니다."
    )

    while keep_streaming:
        start_tick = asyncio.get_event_loop().time()
        try:
            # 1. 가동률 지수 (Availability): 고장 강도가 임계치 돌파 시 가선형 하락 유도 [cite: 584]
            availability = (
                1.0
                if current_fault_intensity < 0.5
                else max(0.4, 1.0 - (current_fault_intensity * 0.4))
            )

            # 2. 성능 효율 지수 (Performance): 변조된 마찰계수 손실에 비례하여 사이클 타임 지연 모사 [cite: 585]
            performance = max(0.3, 1.0 - (current_fault_intensity * 0.6))

            # 3. 품질 지수 (Quality): 동역학 흔들림 모델 비선형 맵핑 [cite: 585]
            quality = max(
                0.9, 1.0 - (current_fault_intensity * random.uniform(0.01, 0.05))
            )

            # 4. 종합 동적 OEE 수학적 체결 ($OEE = A \times P \times Q \times 100$) [cite: 585]
            calculated_oee = float(availability * performance * quality * 100.0)

            # 5. [Task 4-3-A] InfluxDB(TSDB) 비동기 클라이언트를 통한 실시간 논블로킹 사출 [cite: 586]
            point = (
                Point("factory_oee_metrics")
                .tag("line_id", "amr_fleet_01")
                .field("fault_intensity", float(current_fault_intensity))
                .field("availability_index", float(availability))
                .field("performance_index", float(performance))
                .field("quality_index", float(quality))
                .field("overall_oee", float(calculated_oee))
            )
            # 메인 루프 지연을 원천 차단하기 위해 Task로 분리 비동기 실행
            asyncio.create_task(influx_async_manager.write_point_async(point))

            # 6. [인프라 인터록 통전 완성] 프론트엔드 OeeChart 웹소켓 단말로 실시간 패킷 전포 사출
            oee_packet = {
                "measurement": "factory_oee_metrics",
                "fault_intensity": float(current_fault_intensity),
                "availability_index": float(availability),
                "performance_index": float(performance),
                "quality_index": float(quality),
                "overall_oee": float(calculated_oee),
            }
            # 기존 시그널링 허브에 연결된 모든 클라이언트(web_chart_console 포함)에게 스트리밍 전송 [cite: 550, 680]
            asyncio.create_task(
                signaling_manager.broadcast_payload(
                    "oee_calculator_engine", json.dumps(oee_packet)
                )
            )

            if random.getrandbits(4) == 0:
                print(
                    f" 📊 [TSDB STREAM] OEE(t): {calculated_oee:.2f}% (A:{availability:.2f}, P:{performance:.2f}) ➔ TSDB & WS 완전 동기화."
                )
        except Exception as e:
            pass

        # 10Hz 정밀 루프 분해능 유지를 위한 변동 탄력적 슬립 연산
        end_tick = asyncio.get_event_loop().time()
        elapsed = end_tick - start_tick
        await asyncio.sleep(max(0.001, interval - elapsed))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """부팅 시 MQTT 분산 브로커 연결 인가, InfluxDB 비동기 시동 및 셧다운 자원 회제 생명주기 관리"""
    global mqtt_backend_client, oee_streaming_task, keep_streaming

    # 1. 기존 DDL 동기화 재확인 가드 사수 [cite: 568]
    Base.metadata.create_all(bind=engine)

    # 2. 기존 MQTT 컨슈머 스핀업 [cite: 568]
    mqtt_backend_client = init_mqtt_consumer()

    # 3. [Phase 4 / TSDB 비동기 시동 및 10Hz 태스크 점화]
    keep_streaming = True
    oee_streaming_task = asyncio.create_task(periodic_10hz_oee_loop())

    yield

    # 셧다운 백그라운드 자원 역순 클린 다운 마감
    keep_streaming = False
    if oee_streaming_task:
        oee_streaming_task.cancel()
        try:
            await oee_streaming_task
        except asyncio.CancelledError:
            pass

    if mqtt_backend_client:
        mqtt_backend_client.loop_stop()
        mqtt_backend_client.disconnect()

    await influx_async_manager.shutdown()


app = FastAPI(
    title="Smart Factory Digital Twin Core IT Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

# 기존 라우터 전격 복원 수복 완료 [cite: 569]
app.include_router(signaling_router)


# ---------------------------------------------------------------------------
# [보안 레이어] JWT Bearer Token 검증 및 발급엔진 [cite: 569]
# ---------------------------------------------------------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Security(security_jwt_bearer),
):
    """[FRS-08.1] Bearer Token 인증 필터를 통한 API 인입 차단 및 다계층 보안 무결성 실증 [cite: 570]"""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        equipment_id: str = payload.get("sub")
        if equipment_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims: sub is missing.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return equipment_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials, token expired or forged.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post("/api/auth/token", tags=["Authentication"])
def generate_token_for_equipment(equipment_id: str):
    """에지 단말 또는 UI 클라이언트용 인가 토큰 발행 관문 [cite: 572]"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": equipment_id, "role": "edge_node"},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# [비즈니스 평면] Carbon ERP/MES 생산 계획 및 VDA 5050 하향 송출 API [cite: 572]
# ---------------------------------------------------------------------------
@app.post("/api/work-orders/dispatch", tags=["Factory Production Operations"])
def dispatch_work_order(
    work_order_number: str, part_id: str, quantity: int, db: Session = Depends(get_db)
):
    """
    [URS-05/FRS-05.2] Carbon Web UI에서 제출된 생산 오더 수신 및 VDA 5050 하향 송출 트리거 [cite: 573]
    """
    work_order = (
        db.query(WorkOrder)
        .filter(WorkOrder.work_order_number == work_order_number)
        .first()
    )
    if not work_order:
        work_order = WorkOrder(
            id=f"wo_{work_order_number}",
            work_order_number=work_order_number,
            quantity_target=quantity,
            quantity_completed=0,
            status="In-Progress",
        )
        db.add(work_order)
        db.flush()

    routing = (
        db.query(WorkOrderRouting)
        .filter(
            WorkOrderRouting.work_order_id == work_order.id,
            WorkOrderRouting.sequence_number == 1,
        )
        .first()
    )

    if not routing:
        routing = WorkOrderRouting(
            id=f"rt_{work_order_number}_1",
            work_order_id=work_order.id,
            sequence_number=1,
            operation_name="AMR_Fetch",
            target_equipment_id="amr_01",
            status="Pending",
        )
        db.add(routing)
        db.commit()

    vda5050_payload = {
        "orderId": work_order.id,
        "orderUpdateId": 0,
        "serialNumber": "amr_01",
        "nodes": [
            {
                "nodeId": "station_loading_01",
                "sequenceId": 0,
                "released": True,
                "nodePosition": {"x": 3.5, "y": -1.2, "mapId": "factory_map.yaml"},
            }
        ],
        "edges": [],
    }

    if mqtt_backend_client and mqtt_backend_client.is_connected():
        mqtt_backend_client.publish(
            "uagv/v2/EA/vda5050_order", json.dumps(vda5050_payload), qos=1
        )
        routing.status = "In-Progress"
        db.commit()
        return {"status": "DISPATCHED_TO_ROS2_VIA_VDA5050", "order_id": work_order.id}
    else:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Distributed MQTT Broker connection is unavailable.",
        )


# ---------------------------------------------------------------------------
# [비즈니스 평면] [Task 1-2] 라우팅 마감용 REST API 게이트웨이 전용 라우터 [cite: 579]
# ---------------------------------------------------------------------------
@app.post("/api/routings/complete", tags=["Factory Production Operations"])
def complete_routing_step(
    routing_id: str,
    db: Session = Depends(get_db),
    current_edge_node: str = Depends(verify_jwt_token),
):
    """
    [Task 1-2/1-4] 클로즈드 루프 피드백 무결성 완정을 위한 데이터베이스 갱신 게이트웨이 [cite: 580]
    """
    routing = (
        db.query(WorkOrderRouting).filter(WorkOrderRouting.id == routing_id).first()
    )
    if not routing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requested routing step [{routing_id}] database footprint not found.",
        )

    if routing.status == "Completed":
        return {"status": "ALREADY_PROCESSED", "routing_id": routing_id}

    if routing.target_equipment_id != current_edge_node:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The credentials do not match the assigned equipment for this routing step.",
        )

    routing.status = "Completed"

    work_order = (
        db.query(WorkOrder).filter(WorkOrder.id == routing.work_order_id).first()
    )
    if work_order:
        work_order.quantity_completed += 1
        if work_order.quantity_completed >= work_order.quantity_target:
            work_order.status = "Completed"

    db.commit()
    db.refresh(routing)

    return {
        "status": "TRANSACTION_CLOSED_SUCCESSFULLY",
        "routing_id": routing.id,
        "new_routing_status": routing.status,
        "work_order_status": work_order.status if work_order else "N/A",
    }


@app.get("/")
def read_root():
    return {"status": "IT_GATEWAY_OPERATIONAL", "layer": "ISA-95 Layer 3 (MES)"}
