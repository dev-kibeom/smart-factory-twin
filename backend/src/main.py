from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.mqtt_consumer import init_mqtt_consumer, LATEST_AMR_TELEMETRY

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
