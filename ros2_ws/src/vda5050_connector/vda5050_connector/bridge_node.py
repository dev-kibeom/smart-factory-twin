import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
import json
import time


class Vda5050BridgeNode(Node):
    def __init__(self):
        super().__init__("vda5050_bridge_node")

        # [IT ➔ OT] 목적지 인입 및 유도 제어망 전달 퍼블리셔
        self.goal_pub = self.create_publisher(
            PoseStamped, "/vda5050/order_incoming", 10
        )

        # [OT ➔ IT] 목적지 안착 시 완료 상태 역발행 파이프라인 퍼블리셔
        self.state_pub = self.create_publisher(String, "/vda5050/state_outgoing", 10)

        # IT 평면 오더 수신 서브스크라이버
        self.mock_mqtt_sub = self.create_subscription(
            String, "/vda5050/raw_mqtt_topic", self.mqtt_callback, 10
        )
        self.get_logger().info("VDA 5050 OT Bridge Connector Logic 점화 완료.")

    def mqtt_callback(self, msg):
        try:
            data = json.loads(msg.data)
            target_node = data["nodes"][0]["nodePosition"]
            work_order_id = data.get("orderId", "unknown_order")
            equipment_id = data.get("serialNumber", "unknown_amr")

            # 1. 수신된 목적지 좌표 변환 및 하향 퍼블리시
            pose_msg = PoseStamped()
            pose_msg.header.frame_id = target_node["mapId"]
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.pose.position.x = float(target_node["x"])
            pose_msg.pose.position.y = float(target_node["y"])
            pose_msg.pose.orientation.w = 1.0
            self.goal_pub.publish(pose_msg)
            self.get_logger().info(
                f"➔ [수신 완정] 목적지 전달 -> X: {pose_msg.pose.position.x}, Y: {pose_msg.pose.position.y}"
            )

            # 2. [Task 1-4 물리 시뮬레이션 모사] 3초간 주행 후 목적지 도달 상황 연출
            self.get_logger().info(
                f"AMR {equipment_id}가 가상 공장 격자망을 통해 이동 중..."
            )
            time.sleep(3.0)

            # 3. [OT ➔ IT 역방향 피드백] MQTT 스케줄러 규격에 맞추어 완료 이벤트를 역발행
            state_packet = {
                "orderId": work_order_id,
                "routing_sequence": 1,
                "equipment_id": equipment_id,
                "connectionState": "ONLINE",
                "operatingMode": "AUTOMATIC",
                "agvPosition": {
                    "x": pose_msg.pose.position.x,
                    "y": pose_msg.pose.position.y,
                },
            }
            state_msg = String()
            state_msg.data = json.dumps(state_packet)
            self.state_pub.publish(state_msg)
            self.get_logger().info(
                f"✔ [역방향 피드백 송출 완료] Order {work_order_id} 마감 패킷 발행."
            )

        except Exception as e:
            self.get_logger().error(f"VDA 5050 통전 예외 처리: {str(e)}")


def main(args=None):
    rclpy.init(args=args)
    node = Vda5050BridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # 종료 자원 해제 중복 호출 결함(RCLError)을 차단하기 위한 예외 방어 조건절 설계
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
