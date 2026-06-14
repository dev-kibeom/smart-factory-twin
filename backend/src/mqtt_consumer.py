import paho.mqtt.client as mqtt
import json
import logging

logger = logging.getLogger("uvicorn.error")

LATEST_AMR_TELEMETRY = {
    "robot_id": "amr_01",
    "inertia": 0.0,
    "friction": 0.0,
    "torque_nm": 0.0,
    "system_status": "OFFLINE"
}

def on_connect(client, userdata, flags, rc, properties=None):
    logger.info("[IT 백엔드] MQTT 분산 브로커 정합성 체결 완료. 수신 대기 가동.")
    client.subscribe("smart_factory/telemetry/dynamics", qos=1)

def on_message(client, userdata, msg):
    global LATEST_AMR_TELEMETRY
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        LATEST_AMR_TELEMETRY.update(payload)
        logger.info(f"[IT 백엔드] 실시간 로봇 패킷 수입 전사 완정 -> {LATEST_AMR_TELEMETRY}")
    except Exception as e:
        logger.error(f"[IT 백엔드] 패킷 역직렬화 실패: {str(e)}")

def init_mqtt_consumer():
    broker_ip = "172.20.0.10"
    port = 1883
    
    if hasattr(mqtt, 'CallbackApiVersion'):
        client = mqtt.Client(callback_api_version=mqtt.CallbackApiVersion.VERSION2)
    else:
        client = mqtt.Client()

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(broker_ip, port, 60)
        client.loop_start()
        return client
    except Exception as e:
        logger.error(f"[IT 백엔드] MQTT 통전 결함 터짐: {str(e)}")
        return None
