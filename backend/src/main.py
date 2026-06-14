from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from src.database import engine, Base, get_db
from src.models import RobotMaster
from src.mqtt_consumer import init_mqtt_consumer, LATEST_AMR_TELEMETRY

# 부팅 시 SQLAlchemy 엔티티 모델을 기반으로 PostgreSQL(carbon_db) 내 테이블 자동 빌드
Base.metadata.create_all(bind=engine)

mqtt_backend_client = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global mqtt_backend_client
    mqtt_backend_client = init_mqtt_consumer()
    yield
    if mqtt_backend_client:
        mqtt_backend_client.loop_stop()
        mqtt_backend_client.disconnect()

app = FastAPI(
    title="Smart Factory Digital Twin Core IT Gateway",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"status": "IT_GATEWAY_OPERATIONAL", "layer": "ISA-95 Layer 3 (MES)"}

@app.get("/api/v1/telemetry/robot")
def get_realtime_robot_telemetry():
    return LATEST_AMR_TELEMETRY

@app.get("/api/v1/db/robot-master")
def get_db_robot_master(db: Session = Depends(get_db)):
    """[Task 4-1 검증용] PostgreSQL 내부의 로봇 마스터 테이블 상태를 스캔하는 엔드포인트"""
    robots = db.query(RobotMaster).all()
    return robots
