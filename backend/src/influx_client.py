import os
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
import logging

logger = logging.getLogger("uvicorn.error")

# [가상 DNS 매핑] docker-compose.yml 내 서비스 네임(influxdb:8086) 지목 라우팅
INFLUX_URL = "http://influxdb:8086"
INFLUX_TOKEN = "super_secret_influxdb_token_12345"
INFLUX_ORG = "smart_factory_org"
INFLUX_BUCKET = "robot_telemetry_bucket"

try:
    # InfluxDB v2 클라이언트 엔진 초기화
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    # 런타임 쓰기 파이프라인 개통 (동기 모드로 즉시 직격 사출 설정)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    logger.info("[IT 백엔드] InfluxDB(TSDB) 시계열 파이프라인 초기화 완정.")
except Exception as e:
    logger.error(f"[IT 백엔드] InfluxDB 연결 링커 실패: {str(e)}")
    write_api = None

def stream_to_influxdb(robot_id: str, inertia: float, friction: float, torque_nm: float):
    """[핵심 파이프라인] 실시간 로봇 동역학 패킷을 시계열 데이터 포인트로 변환하여 사출"""
    if write_api is None:
        return

    try:
        # InfluxDB 표준 시계열 데이터 포인트 생성 (Measurement: amr_dynamics)
        point = Point("amr_dynamics") \
            .tag("robot_id", robot_id) \
            .field("inertia", float(inertia)) \
            .field("friction", float(friction)) \
            .field("torque_nm", float(torque_nm))

        # TSDB 버킷 내부에 스트림 데이터 직격 박제 (타임스탬프는 서버 입력 시점 자동 마킹)
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    except Exception as e:
        logger.error(f"[IT 백엔드] InfluxDB 스트림 사출 결함: {str(e)}")
