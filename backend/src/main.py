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
from fastapi.middleware.cors import CORSMiddleware

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
from src.api.v1.signaling import manager as signaling_manager

# Phase 4 비동기 TSDB 인프라 클라이언트 및 고장 주입 라우터 명시적 인입
from src.influx_client import influx_async_manager
from src.routers.fault_injection import router as fault_router
from influxdb_client import Point

# ===========================================================================
# 🛡️ [Eager Execution] 부팅 blocking 동기화 가드
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

SECRET_KEY = "carbon_super_secure_secret_key_for_jwt_tokens_2026"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

security_jwt_bearer = HTTPBearer()

current_fault_intensity = 0.0
calculated_oee = 100.0

keep_streaming = False
oee_streaming_task = None


async def periodic_10hz_oee_loop():
    global current_fault_intensity, calculated_oee, keep_streaming
    interval = 0.1
    print(
        " 📊 [OEE ENGINE] 10Hz 주기 초고속 시계열 OEE 수식 모델 루프가 가동되었습니다."
    )

    while keep_streaming:
        start_tick = asyncio.get_event_loop().time()
        try:
            availability = (
                1.0
                if current_fault_intensity < 0.5
                else max(0.4, 1.0 - (current_fault_intensity * 0.4))
            )
            performance = max(0.3, 1.0 - (current_fault_intensity * 0.6))
            quality = max(
                0.9, 1.0 - (current_fault_intensity * random.uniform(0.01, 0.05))
            )
            calculated_oee = float(availability * performance * quality * 100.0)

            point = (
                Point("factory_oee_metrics")
                .tag("line_id", "amr_fleet_01")
                .field("fault_intensity", float(current_fault_intensity))
                .field("availability_index", float(availability))
                .field("performance_index", float(performance))
                .field("quality_index", float(quality))
                .field("overall_oee", float(calculated_oee))
            )
            asyncio.create_task(influx_async_manager.write_point_async(point))

            oee_packet = {
                "measurement": "factory_oee_metrics",
                "fault_intensity": float(current_fault_intensity),
                "availability_index": float(availability),
                "performance_index": float(performance),
                "quality_index": float(quality),
                "overall_oee": float(calculated_oee),
            }
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

        end_tick = asyncio.get_event_loop().time()
        elapsed = end_tick - start_tick
        await asyncio.sleep(max(0.001, interval - elapsed))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_backend_client, oee_streaming_task, keep_streaming
    mqtt_backend_client = init_mqtt_consumer()
    keep_streaming = True
    oee_streaming_task = asyncio.create_task(periodic_10hz_oee_loop())
    yield
    keep_streaming = False
    if oee_streaming_task:
        oee_streaming_task.cancel()
    if mqtt_backend_client:
        mqtt_backend_client.loop_stop()
        mqtt_backend_client.disconnect()
    await influx_async_manager.shutdown()


app = FastAPI(
    title="Smart Factory Digital Twin Core IT Gateway",
    version="1.0.0",
    lifespan=lifespan,
)

# 🛡️ [CORS 정책 무결성 개통] 사전 비행 요청(OPTIONS) 프리플라이트 필터 통과 가드
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 🔌 [관문 라우터 정격 결착 파이프라인]
# ---------------------------------------------------------------------------
app.include_router(signaling_router)

# 🚨 [핫픽스 직격 편입]: 장부 누락을 해제하기 위해 고장 주입 라우터를 명시적으로 마운트 선언합니다.
app.include_router(fault_router)


# ---------------------------------------------------------------------------
# [보안 레이어] JWT Bearer Token 검증 및 발급엔진
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
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": equipment_id, "role": "edge_node"},
        expires_delta=access_token_expires,
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# [비즈니스 평면] Carbon ERP/MES 생산 계획 및 VDA 5050 하향 송출 API
# ---------------------------------------------------------------------------
@app.post("/api/work-orders/dispatch", tags=["Factory Production Operations"])
def dispatch_work_order(
    work_order_number: str, part_id: str, quantity: int, db: Session = Depends(get_db)
):
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


@app.post("/api/routings/complete", tags=["Factory Production Operations"])
def complete_routing_step(
    routing_id: str,
    db: Session = Depends(get_db),
    current_edge_node: str = Depends(verify_jwt_token),
):
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
