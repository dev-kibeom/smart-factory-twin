#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64
import paho.mqtt.client as mqtt
import json


class SysidOptimizationEngine(Node):
    """
    [URS-11/FRS-11.2] 고장 주입 신호를 수전하여 가상 공장 동역학 파라미터를 비선형 변조하는 최적화 엔진
    """

    def __init__(self):
        super().__init__("sysid_optimization_engine")
        self.get_logger().info(
            "========================================================================="
        )
        self.get_logger().info(
            " 🧮 실시간 실증 고장 주입 및 파라미터 식별(SysID) 동적 변조 엔진 점화"
        )
        self.get_logger().info(
            "========================================================================="
        )

        # 1. 고장 강도(Fault Intensity) 수신을 위한 ROS 2 서브스크라이버 개통
        self.fault_sub = self.create_subscription(
            Float64, "/ros2_medkit/fault_intensity", self.fault_engagement_callback, 10
        )

        # 2. IT 평면 데이터 수수를 위한 MQTT 링커 결합
        self.mqtt_broker_ip = "172.20.0.10"
        self.init_mqtt_client()

    def init_mqtt_client(self):
        if hasattr(mqtt, "CallbackApiVersion"):
            self.mqtt_client = mqtt.Client(
                callback_api_version=mqtt.CallbackApiVersion.VERSION2
            )
        else:
            self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(self.mqtt_broker_ip, 1883, 60)
        self.mqtt_client.loop_start()

    def fault_engagement_callback(self, msg):
        """
        [고장 주입 수식적 결합 매커니즘]
        인입된 고장 인텐시티(0.0 ~ 1.0)에 따라 하부 주행 마찰력을 인위적으로 승수 연산 변조
        """
        intensity = msg.data
        # 기본 마찰계수 0.8에 고장 강도 비례 계수를 가산하여 강제 가속 성능 저하 유도
        mutated_friction = 0.8 + (intensity * 4.2)

        payload = {
            "robot_id": "amr_01",
            "injected_fault_intensity": intensity,
            "mutated_friction": mutated_friction,
            "system_status": "DEGRADED" if intensity > 0.3 else "OPERATIONAL",
        }

        # JAX 물리 평면 및 IT 백엔드로 고장 연동 사출
        self.mqtt_client.publish(
            "smart_factory/telemetry/fault_state", json.dumps(payload), qos=1
        )
        self.get_logger().warn(
            f" ⚠️ [고장 융합 발동] 강도: {intensity:.2f} ➔ 변조 마찰 계수 수치: {mutated_friction:.2f} 로켓 적용."
        )


def main(args=None):
    rclpy.init(args=args)
    node = SysidOptimizationEngine()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.mqtt_client.loop_stop()
        node.mqtt_client.disconnect()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
