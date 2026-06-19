#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"

import rclpy
from rclpy.node import Node
from std_msgs.msg import (
    String,
    Float64,
)  # 🔌 [인프라 수복] 고장 강도 사출용 Float64 타입 인입
import paho.mqtt.client as mqtt
import json


class Ros2MqttBridgeNode(Node):
    def __init__(self):
        super().__init__("ros2_mqtt_bridge_node")
        self.get_logger().info(
            "Initializing Clean IT/OT Boundary Bridge Driver Pipeline_v2..."
        )

        # ---------------------------------------------------------------------------
        # 📥 [OT -> IT 상향 링크] ROS2 구독 및 MQTT 발행 설정
        # ---------------------------------------------------------------------------
        self.subscription = self.create_subscription(
            String, "amr/telemetry/dynamics", self.dynamics_callback, 10
        )

        # 🧠 행동 트리의 비상 고장 알람 리포트 채널 추가 구독
        self.fault_report_sub = self.create_subscription(
            String, "/amr_fleet/fault_report", self.bt_fault_report_callback, 10
        )

        # ---------------------------------------------------------------------------
        # 📤 [IT -> OT 하향 링크] MQTT 구독 및 ROS2 발행 설정 (고장 주입 서킷 개통)
        # ---------------------------------------------------------------------------
        self.fault_pub = self.create_publisher(
            Float64, "/ros2_medkit/fault_intensity", 10
        )

        self.mqtt_broker_ip = "172.20.0.10"
        self.mqtt_port = 1883
        self.mqtt_topic_dynamics = "smart_factory/telemetry/dynamics"
        self.mqtt_topic_vda5050 = "uagv/v2/EA/vda5050_state"
        self.mqtt_topic_inject = "smart_factory/fault/inject"  # 대시보드 직격 고장 채널

        try:
            if hasattr(mqtt, "CallbackApiVersion"):
                self.mqtt_client = mqtt.Client(
                    callback_api_version=mqtt.CallbackApiVersion.VERSION2
                )
            else:
                self.mqtt_client = mqtt.Client()

            # MQTT 브로ker 연결 및 비동기 이벤트 핸들러 바인딩
            self.mqtt_client.on_message = self.on_mqtt_message
            self.mqtt_client.connect(self.mqtt_broker_ip, self.mqtt_port, 60)

            # 대시보드 고장 채널 구독 세션 수립
            self.mqtt_client.subscribe(self.mqtt_topic_inject, qos=1)
            self.mqtt_client.loop_start()

            self.get_logger().info(
                f"Successfully connected & Subscribed to MQTT Broker at {self.mqtt_broker_ip}"
            )
        except Exception as e:
            self.get_logger().error(f"MQTT Connection Failure: {str(e)}")

    def dynamics_callback(self, msg):
        """순정 다이내믹스 텔레메트리 파이프라인 사수"""
        try:
            raw_data = json.loads(msg.data)
            payload = {
                "robot_id": "amr_01",
                "inertia": raw_data.get("inertia", 4.5),
                "friction": raw_data.get("friction", 0.8),
                "torque_nm": raw_data.get("torque_nm", 12.4),
                "system_status": "OPERATIONAL",
            }

            self.mqtt_client.publish(
                self.mqtt_topic_dynamics, json.dumps(payload), qos=1
            )
        except Exception as e:
            self.get_logger().error(f"Serialization failure: {str(e)}")

    def on_mqtt_message(self, client, userdata, msg):
        """🔌 [하향 인터록 코어] IT 대시보드 결함 패킷 수전 ➔ OT ROS2 전포 사출"""
        try:
            payload_str = msg.payload.decode("utf-8")
            data = json.loads(payload_str)

            # 대시보드 사출 키 패턴 매칭 (Target, Intensity)
            target = data.get("Target") or data.get("target")
            intensity = data.get("Intensity") or data.get("intensity", 0.0)

            if target == "amr_01_lidar":
                ros_msg = Float64()
                ros_msg.data = float(intensity)
                self.fault_pub.publish(ros_msg)
                self.get_logger().warn(
                    f"📥 [MQTT ➔ ROS2] 고장 주입 수전 연격 사출: Intensity {intensity}"
                )
        except Exception as e:
            self.get_logger().error(f"Incoming MQTT Fault Processing Failure: {str(e)}")

    def bt_fault_report_callback(self, msg):
        """🧠 행동 트리 비상 가드 획득 및 VDA 5050 IT 상향 사출"""
        try:
            bt_fault_data = json.loads(msg.data)
            vda5050_payload = {
                "header": {"robot_id": "amr_01", "manufacturer": "ros2_medkit"},
                "errors": [
                    {
                        "errorType": str(bt_fault_data.get("errorType", 401)),
                        "errorLevel": bt_fault_data.get("errorLevel", "FATAL"),
                        "errorDescription": bt_fault_data.get(
                            "description", "Lidar Blind"
                        ),
                    }
                ],
                "operatingMode": "MANUAL_TEACH_IN",
            }
            self.mqtt_client.publish(
                self.mqtt_topic_vda5050, payload=json.dumps(vda5050_payload), qos=1
            )
            # self.get_logger().warn(
            #     "🚨 [VDA5050 EXPORT] Fail-Safe State Dispatched to IT Network."
            # )
        except Exception as e:
            self.get_logger().error(f"Fault Bridge Parsing Failure: {str(e)}")

    def destroy_node(self):
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = Ros2MqttBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
