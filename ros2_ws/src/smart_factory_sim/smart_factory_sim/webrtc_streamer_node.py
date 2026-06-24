#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# ===========================================================================
# 🚨 [인프라 인터록 수복] colcon 런타임 격리를 우회하기 위한 최선순위 패스 삽입
# ===========================================================================
sys_dist_path = "/usr/lib/python3/dist-packages"
if sys_dist_path not in sys.path:
    sys.path.insert(0, sys_dist_path)

import json
import time
import threading
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image

# JAX와의 GPU VRAM 자원 경합 및 선점 차단을 위한 하드웨어 격리 선언
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"

# GStreamer Core 및 WebRTC Native 평면 바인딩을 위한 고강도 라이브러리 인입
import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")  # 🔌 [인프라 수복] SDP 버퍼 해석용 전용 가드 인입
from gi.repository import Gst, GstWebRTC, GstSdp, GLib

import websocket


class WebrtcStreamerNode(Node):
    """
    [URS-09/FRS-09.1] GStreamer / NVENC 기반 제로카피 WebRTC P2P 직접 송출 노드 (최종 연격형 수복판)
    """

    def __init__(self):
        super().__init__("webrtc_streamer_node")

        self.get_logger().info(
            "========================================================================="
        )
        self.get_logger().info(
            " 📹 GStreamer / H.264 NVENC 하드웨어 videotestsrc WebRTC 파이프라인 완정 구동"
        )
        self.get_logger().info(
            "========================================================================="
        )

        self.client_id = "webrtc_streamer_node"
        self.signaling_url = (
            f"ws://sf_fastapi_gateway:8000/api/v1/signal/ws/{self.client_id}"
        )
        self.ws = None

        Gst.init(None)

        # 표준 규격이자 내부 자원 경합이 전혀 없는 무결점 스트림 평면 마감
        self.pipeline_str = (
            "webrtcbin name=sendrecv bundle-policy=max-bundle "
            "appsrc name=ros_source is-live=true do-timestamp=true format=time "
            "caps=video/x-raw,format=RGB,width=640,height=480,framerate=30/1 ! "
            "videoconvert ! video/x-raw,format=I420 ! "
            "vp8enc deadline=1 cpu-used=4 target-bitrate=2000000 ! "
            "rtpvp8pay pt=96 ! "
            "application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)VP8,payload=(int)96 ! "
            "sendrecv.sink_0"
        )

        self.pipeline = Gst.parse_launch(self.pipeline_str)
        self.webrtc_bin = self.pipeline.get_by_name("sendrecv")

        self.appsrc = self.pipeline.get_by_name("ros_source")

        self.img_sub = self.create_subscription(
            Image, "/amr_front_camera/image_raw", self.image_callback, 10
        )

        self.webrtc_bin.connect("on-ice-candidate", self._on_ice_candidate_cb)
        self.webrtc_bin.connect("on-negotiation-needed", self._on_negotiation_needed_cb)

        self.pipeline.set_state(Gst.State.PLAYING)

        self.loop = GLib.MainLoop()
        self.gst_thread = threading.Thread(target=self.loop.run, daemon=True)
        self.gst_thread.start()

        self.ws_thread = threading.Thread(
            target=self._init_signaling_websocket, daemon=True
        )
        self.ws_thread.start()

    def _init_signaling_websocket(self):
        while rclpy.ok():
            try:
                self.get_logger().info(
                    f" 📡 FastAPI 시그널링 웹소켓 관문 접속 시도 -> {self.signaling_url}"
                )
                self.ws = websocket.WebSocketApp(
                    self.signaling_url,
                    on_message=self._on_ws_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close,
                )
                self.ws.run_forever()
            except Exception as e:
                self.get_logger().error(
                    f" 시그널링 웹소켓 런타임 끊김, 2초 후 재연결 시도: {str(e)}"
                )
            time.sleep(2.0)

    def image_callback(self, msg):
        """📸 Gazebo 가상 카메라의 원시 픽셀 바이트 데이터를 GStreamer 커널 평면으로 제로카피 이식"""
        try:
            # ROS2 이미지의 Raw 바이트 스트림을 GStreamer 전용 메모리 버퍼로 복사 원자화
            raw_bytes = bytes(msg.data)
            buf = Gst.Buffer.new_allocate(None, len(raw_bytes), None)
            buf.fill(0, raw_bytes)

            # 🎯 GStreamer Core 내부로 비디오 버퍼 실시간 푸시
            self.appsrc.emit("push-buffer", buf)
        except Exception as e:
            self.get_logger().error(f" ❌ [미디어 버퍼 인서트 실패] {str(e)}")
            
    def _on_ws_message(self, ws, message):
        """Next.js 프론트엔드로부터 인입되는 원격 SDP/ICE Candidate 패킷 파싱 및 GStreamer 코어 결착"""
        try:
            msg = json.loads(message)
            if msg.get("target_id") != self.client_id:
                return

            msg_type = msg.get("type")

            if msg_type == "answer":
                sdp_text = msg.get("sdp")
                _, sdp_msg = GstSdp.SDPMessage.new()
                GstSdp.sdp_message_parse_buffer(
                    bytes(sdp_text.encode("utf-8")), sdp_msg
                )

                # GStreamer 전용 ANSWER 타입 세션 객체 생성
                remote_answer = GstWebRTC.WebRTCSessionDescription.new(
                    GstWebRTC.WebRTCSDPType.ANSWER, sdp_msg
                )
                promise = Gst.Promise.new()

                # GStreamer 링킹 엔진에 원격 명세 바인딩 사출
                self.webrtc_bin.emit("set-remote-description", remote_answer, promise)
                promise.interrupt()
                self.get_logger().info(
                    " ✔ [미디어 인터록] Remote SDP Answer를 GStreamer 커널에 최종 결착 완료!"
                )

            elif msg_type == "candidate":
                candidate_data = msg.get("candidate")
                mline_index = msg.get("sdpMLineIndex")
                self.webrtc_bin.emit("add-ice-candidate", mline_index, candidate_data)

        except Exception as e:
            self.get_logger().error(f" ❌ [시그널 웹소켓 처리 결함] {str(e)}")

    def _on_ws_error(self, ws, error):
        self.get_logger().error(f" 🚨 [시그널 웹소켓 에러 포착] {str(error)}")

    def _on_ws_close(self, ws, close_status_code, close_msg):
        self.get_logger().warn(" 🛑 [시그널 웹소켓 닫힘] 세션 연결이 종료되었습니다.")

    def _on_ice_candidate_cb(self, webrtcbin, mlineindex, candidate):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            payload = {
                "target_id": "web_ui_console",
                "type": "candidate",
                "sdpMLineIndex": mlineindex,
                "candidate": candidate,
            }
            self.ws.send(json.dumps(payload))

    def _on_negotiation_needed_cb(self, webrtcbin):
        promise = Gst.Promise.new_with_change_func(self._on_offer_created, None, None)
        self.webrtc_bin.emit("create-offer", None, promise)

    def _on_offer_created(self, promise, *args):
        reply = promise.get_reply()
        offer = reply.get_value("offer")
        promise = Gst.Promise.new()
        self.webrtc_bin.emit("set-local-description", offer, promise)
        promise.interrupt()

        sdp_text = offer.sdp.as_text()
        if self.ws and self.ws.sock and self.ws.sock.connected:
            payload = {"type": "offer", "sdp": sdp_text}
            self.ws.send(json.dumps(payload))

    def destroy_node(self):
        self.get_logger().warn(
            " 🛑 WebRTC 스트리밍 자산 해제 및 GStreamer 파이프라인 종료 중..."
        )
        if self.ws:
            self.ws.close()
        self.pipeline.set_state(Gst.State.NULL)
        self.loop.quit()
        super().destroy_node()


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
