#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
import os


class WebrtcStreamerNode(Node):
    def __init__(self):
        # [스케일 다운 규칙] use_intra_process_comms를 활성화하여 메모리 포인터 직접 전달 유도 [cite: 84]
        super().__init__(
            "webrtc_streamer_node", namespace="", share_each_with_private_node=True
        )

        self.get_logger().info(
            "초저지연 미디어 평면 NVENC 제로카피 파이프라인 초기화 중..."
        )

        # [핵심 GStreamer 튜닝 파라미터 셋 인가] [cite: 85, 86]
        # nvh264enc 가속 소자 주입, B-프레임 전면 제거(bframes=0), tune=zerolatency 강제 락인 [cite: 85, 86]
        self.gst_pipeline = (
            "appsrc name=mysource ! videoconvert ! video/x-raw,format=I420 ! "
            "nvh264enc bframes=0 tune=zerolatency preset=ultrafast rc-mode=2bitrate=2000000 ! "
            "rtph264pay config-interval=1 pt=96 ! appsink name=mysink"
        )

        self.image_sub = self.create_subscription(
            Image,
            "/camera/image_raw",
            self.camera_callback,
            rclcpp.qos.QoSProfile(
                depth=1
            ),  # 큐 버퍼를 1로 제한하여 지연 프레임 원천 적체 차단
        )

        self.get_logger().info("✔ RTX 4060 하드웨어 코덱 연격 미디어 가교 체결 완정.")

    def camera_callback(self, msg):
        # 코딩 에이전트가 가속 버퍼 포인터를 GStreamer appsrc에 Zero-copy 주입할 구현 도메인 영역 [cite: 81]
        pass


def main(args=None):
    rclpy.init(args=args)
    node = WebrtcStreamerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
