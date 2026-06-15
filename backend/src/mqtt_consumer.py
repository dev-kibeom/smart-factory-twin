# backend/src/mqtt_consumer.py (MOM 데이터 고속도로 수전 가드 완성본)

import sys
import paho.mqtt.client as mqtt
import json
import logging

logger = logging.getLogger("uvicorn.error")


def on_connect_callback(client, userdata, flags, rc, properties=None):
    """MOM 계층 분산 브로커 연결 체결 즉시 정격 토픽 전방위 구독 등록"""
    if rc == 0:
        logger.info(" 📡 [MQTT CONSUMER] 분산 브로커와 정식 커넥션 체결 완정.")

        # 1. 기존 비즈니스 레이어 피드백 토픽 구독 사수
        client.subscribe("uagv/v2/EA/vda5050_state")

        # 🚨 [Phase 4 핫픽스] JAX/SysID 엔진이 사출하는 고장 주입 텔레메트리 토픽 공식 구독 락인!
        client.subscribe("smart_factory/telemetry/fault_state")
        logger.info(
            " 🤖 [MQTT SUBSCRIPTION] 'smart_factory/telemetry/fault_state' 토픽 채널 구독 개통 완료."
        )
    else:
        logger.error(f" ❌ MQTT 브로커 연결 실패 (Code: {rc})")


def on_message_callback(client, userdata, msg):
    """분산 브로커로부터 인입되는 텔레메트리 고속 파싱 및 IT 전역 메모리 유전"""
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode("utf-8"))

        # 고장 상태 감지 즉시 main.py의 전역 스냅샷 변수로 직격 인서트
        if topic == "smart_factory/telemetry/fault_state":
            intensity = float(payload.get("injected_fault_intensity", 0.0))

            # sys.modules 에 적재된 메인 컨텍스트 런타임 힙 메모리에 다이렉트 융합
            if "src.main" in sys.modules:
                sys.modules["src.main"].current_fault_intensity = intensity
                logger.info(
                    f" 📥 [MOM DIRECT LINKED] 고장 데이터 런타임 매핑 완정 ➔ Intensity: {intensity:.2f}"
                )
    except Exception as e:
        logger.error(f" ❌ [MOM CONSUME FAULT] 패킷 파싱 예외 발생: {str(e)}")


def init_mqtt_consumer():
    """FastAPI lifespan 서브 시스템에서 트리거할 정격 컨슈머 인스턴싱 루틴"""
    broker_ip = "172.20.0.10"
    port = 1883

    # paho-mqtt 버전 파편화 방어 가드레일 체결
    if hasattr(mqtt, "CallbackApiVersion"):
        client = mqtt.Client(callback_api_version=mqtt.CallbackApiVersion.VERSION2)
    else:
        client = mqtt.Client()

    client.on_connect = on_connect_callback
    client.on_message = on_message_callback

    try:
        client.connect(broker_ip, port, 60)
        # 비동기 백그라운드 런타임 스레드 가동
        client.loop_start()
        return client
    except Exception as e:
        logger.error(f" ❌ MQTT 컨슈머 스핀업 실패: {str(e)}")
        return None
