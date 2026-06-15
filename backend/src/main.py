import os
import jwt
import time
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
from src.mqtt_consumer import init_mqtt_consumer, mqtt_backend_client


# ===========================================================================
# 🛡️ [Eager Execution] 부팅 blocking 동기화 가드 (Lazy 런타임 우회)
# ===========================================================================
print("=========================================================================")
print(" [DDL 인프라 엔진] 단일 메타데이터 컨텍스트 기반 스키마 동기화를 시작합니다.")
db_ready = False
for i in range(10):
    try:
        # 단일 통합된 Base의 메타데이터를 사용하여 DDL 강제 인가
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
    # 🚨 [자산 직격 인서트 레이어] ORM 컬럼 파편화 리스크를 우회하는 강제 징검다리 락
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    SessionInit = sessionmaker(bind=engine)
    init_db_session = SessionInit()
    try:
        # 1. 로봇 장부 테이블이 물리적으로 완전히 존재함을 최종 실증하기 위한 DDL 강제 재확정
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

        # 2. 외래키 위반을 원천 차단하기 위해 amr_01 하드웨어 에이전트 강제 주입 (UPSERT 아키텍처)
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """부팅 시 MQTT 분산 브로커 연결 인가 및 셧다운 자원 회제 생명주기 관리"""
    global mqtt_backend_client
    # 테이블 안전마진을 재확인하기 위해 한번 더 수행
    Base.metadata.create_all(bind=engine)
    mqtt_backend_client = init_mqtt_consumer()
    yield
    if mqtt_backend_client:
        mqtt_backend_client.loop_stop()
        mqtt_backend_client.disconnect()


app = FastAPI(
    title="Smart Factory Digital Twin Core IT Gateway",
    version="1.0.0",
    lifespan=lifespan,
)


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
    """[FRS-08.1] Bearer Token 인증 필터를 통한 API 인입 차단 및 다계층 보안 무결성 실증"""
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
    """에지 단말 또는 UI 클라이언트용 인가 토큰 발행 관문"""
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
    """
    [URS-05/FRS-05.2] Carbon Web UI에서 제출된 생산 오더 수신 및 VDA 5050 하향 송출 트리거
    """
    # 1. 비즈니스 무결성을 위한 ACID 트랜잭션 수립
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

    # 차순위 세부 라우팅 시퀀스 적재 (sequence_number=1, AMR_Fetch 무조건 강제 점화)
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

    # 2. VDA 5050 스키마 구조 정합 및 MQTT 하향 전포 발행
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
# [비즈니스 평면] [Task 1-2] 라우팅 마감용 REST API 게이트웨이 전용 라우터
# ---------------------------------------------------------------------------
@app.post("/api/routings/complete", tags=["Factory Production Operations"])
def complete_routing_step(
    routing_id: str,
    db: Session = Depends(get_db),
    current_edge_node: str = Depends(verify_jwt_token),
):
    """
    [Task 1-2/1-4] 클로즈드 루프 피드백 무결성 완정을 위한 데이터베이스 갱신 게이트웨이
    외부 단말의 직접 DB 접근을 완전 차단하고, Bearer Token 유효성 검증을 통과해야만 트랜잭션 수행 권한 인가
    """
    # API 쓰기 큐 및 커넥션 풀 안전 마진 확보를 위한 컨텍스트 진입
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

    # 토큰에서 추출된 소유권 검증 (Heterogeneous 로봇 플릿 권한 격리 기법 준수)
    if routing.target_equipment_id != current_edge_node:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The credentials do not match the assigned equipment for this routing step.",
        )

    # 1. 현재 공정 마감 처리 수행 (ACID 트랜잭션 보장)
    routing.status = "Completed"

    # 2. 연계된 상위 WorkOrder 마스터 테이블 상태 자동 추적 차감 로직 연격
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
