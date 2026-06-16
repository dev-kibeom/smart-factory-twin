#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import paho.mqtt.client as mqtt
import json

class Ros2MqttBridgeNode(Node):
    def __init__(self):
        super().__init__('ros2_mqtt_bridge_node')
        self.get_logger().info('Initializing Clean IT/OT Boundary Bridge Driver Pipeline...')

        self.subscription = self.create_subscription(
            String,
            'amr/telemetry/dynamics',
            self.dynamics_callback,
            10
        )

        self.mqtt_broker_ip = "172.20.0.10"
        self.mqtt_port = 1883
        self.mqtt_topic = "smart_factory/telemetry/dynamics"

        try:
            # [버전 방어적 예외 처리] paho-mqtt 1.x와 2.x 버전을 모두 지원하도록 자동 매핑
            if hasattr(mqtt, 'CallbackApiVersion'):
                self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackApiVersion.VERSION2)
            else:
                self.mqtt_client = mqtt.Client() # 구형 1.x 호환 규칙 인가

            self.mqtt_client.connect(self.mqtt_broker_ip, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            self.get_logger().info(f'Successfully connected to MQTT Broker at {self.mqtt_broker_ip}:{self.mqtt_port}')
        except Exception as e:
            self.get_logger().error(f'MQTT Connection Failure: {str(e)}')

    def dynamics_callback(self, msg):
        try:
            raw_data = json.loads(msg.data)
            payload = {
                "robot_id": "amr_01",
                "inertia": raw_data.get("inertia", 4.5),
                "friction": raw_data.get("friction", 0.8),
                "torque_nm": raw_data.get("torque_nm", 12.4),
                "system_status": "OPERATIONAL"
            }
            json_payload = json.dumps(payload)
            self.mqtt_client.publish(self.mqtt_topic, json_payload, qos=1)
            self.get_logger().info(f'Streamed Telemetry Packet to IT Plane -> {json_payload}')
        except Exception as e:
            self.get_logger().error(f'Serialization failure: {str(e)}')

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

if __name__ == '__main__':
    main()
