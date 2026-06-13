import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
import json

class Vda5050BridgeNode(Node):
    def __init__(self):
        super().__init__('vda5050_bridge_node')
        
        # [Task 1-3 DoD] 내부 Nav2 유도 제어망과 연동할 최종 목적지 좌표 퍼블리셔
        self.goal_pub = self.create_publisher(PoseStamped, '/vda5050/order_incoming', 10)
        
        # 가상 수신 서브스크라이버
        self.mock_mqtt_sub = self.create_subscription(
            String,
            '/vda5050/raw_mqtt_topic',
            self.mqtt_callback,
            10
        )
        self.get_logger().info('VDA 5050 OT Bridge Connector Logic 점화 완료.')

    def mqtt_callback(self, msg):
        try:
            data = json.loads(msg.data)
            target_node = data["nodes"][0]["nodePosition"]
            
            pose_msg = PoseStamped()
            pose_msg.header.frame_id = target_node["mapId"]
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.pose.position.x = float(target_node["x"])
            pose_msg.pose.position.y = float(target_node["y"])
            pose_msg.pose.orientation.w = 1.0
            
            self.goal_pub.publish(pose_msg)
            self.get_logger().info(f'➔ [VDA5050 통전 성공] 목적지 수신 완정 -> X: {pose_msg.pose.position.x}, Y: {pose_msg.pose.position.y}')
        except Exception as e:
            self.get_logger().error(f'VDA 5050 스키마 디코딩 실패: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    node = Vda5050BridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
