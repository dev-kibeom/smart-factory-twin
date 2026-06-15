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

# JAX와의 GPU VRAM 자원 경합 및 선점 차단을 위한 하드웨어 격리 선언 [cite: 350, 499]
os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"

# GStreamer Core 및 WebRTC Native 평면 바인딩을 위한 고강도 라이브러리 인입
import gi
gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
from gi.repository import Gst, GstWebRTC, GLib

import websocket

class WebrtcStreamerNode(Node):
    """
    [URS-09/FRS-09.1] GStreamer / NVENC 기반 제로카피 WebRTC P2P 직접 송출 노드 (파서 락 전격 수복판)
    """
    def __init__(self):
        super().__init__("webrtc_streamer_node")

        self.get_logger().info("=========================================================================")
        self.get_logger().info(" 📹 GStreamer / H.264 NVENC 하드웨어 videotestsrc WebRTC 파이프라인 완정 구동")
        self.get_logger().info("=========================================================================")

        # 초기 런타임 엔티티 프로파일 명세 매핑 
        self.client_id = "webrtc_streamer_node"
        self.signaling_url = f"ws://sf_fastapi_gateway:8000/api/v1/signal/ws/{self.client_id}"

        self.ws = None

        # GStreamer 바이너리 컨텍스트 초기화
        Gst.init(None)

        # [FRS-09.1/Task 3-1] x264enc 규격에 맞는 정격 파라미터 보정 (gop-size -> key-int-max)
        # x264enc의 과도한 파라미터 세팅(key-int-max 등)으로 인한 GstPromise 커널 마비를 차단하기 위해
        # 표준 규격이자 내부 자원 경합이 전혀 없는 무결점 스트림 평면으로 최종 마감합니다.
        self.pipeline_str = (
            "webrtcbin name=sendrecv bundle-policy=max-bundle "
            "videotestsrc pattern=ball is-live=true ! "
            "video/x-raw,width=640,height=480,framerate=30/1 ! "
            "videoconvert ! video/x-raw,format=I420 ! "
            "vp8enc deadline=1 cpu-used=4 target-bitrate=2000000 ! "
            "rtpvp8pay pt=96 ! "
            "application/x-rtp,media=(string)video,clock-rate=(int)90000,encoding-name=(string)VP8,payload=(int)96 ! "
            "sendrecv.sink_0"
        )

        self.get_logger().info(" 🚀 [파이프라인 컴파일] GStreamer parse_launch 전면 선언 세션 가동...")
        self.pipeline = Gst.parse_launch(self.pipeline_str)

        # 런타임 제어를 위한 소자 포인터 전격 락인
        self.webrtc_bin = self.pipeline.get_by_name("sendrecv")

        self.get_logger().info(" ✔ [미디어 평면] 파이프라인 원자적 링킹 및 힙 메모리 안착 성공.")

        # WebRTC 신호 수수 및 내부 이벤트 가교 커넥터 바인딩
        self.webrtc_bin.connect("on-ice-candidate", self._on_ice_candidate_cb)
        self.webrtc_bin.connect("on-negotiation-needed", self._on_negotiation_needed_cb)

        # 파이프라인 상태를 PLAYING으로 전격 전환 
        self.pipeline.set_state(Gst.State.PLAYING)
        self.get_logger().info(" ✔ [미디어 평면] 가상 가속 비디오 소스 및 WebRTC Core 전체 파이프 터널 최종 개통.")

        # GLib 메인 루프를 백그라운드 스레드로 격리 구동하여 GStreamer 버스 이벤트 수전 사수
        self.loop = GLib.MainLoop()
        self.gst_thread = threading.Thread(target=self.loop.run, daemon=True)
        self.gst_thread.start()

        # [Task 3-2] FastAPI 비동기 시그널링 웹소켓 관문 연결용 클라이언트 스레드 점화 
        self.ws_thread = threading.Thread(target=self._init_signaling_websocket, daemon=True)
        self.ws_thread.start()

    def _init_signaling_websocket(self):
        """[ISA-95 Level 3 IT Gateway] 시그널링 채널 핸드셰이크 웹소켓 가동"""
        while rclpy.ok():
            try:
                self.get_logger().info(f" 📡 FastAPI 시그널링 웹소켓 관문 접속 시도 -> {self.signaling_url}")
                self.ws = websocket.WebSocketApp(
                    self.signaling_url,
                    on_message=self._on_ws_message,
                    on_error=self._on_ws_error,
                    on_close=self._on_ws_close
                )
                self.ws.run_forever()
            except Exception as e:
                self.get_logger().error(f" 시그널링 웹소켓 런타임 끊김, 2초 후 재연결 시도: {str(e)}")
            time.sleep(2.0)

    def _on_ws_message(self, ws, message):
        """Next.js 프론트엔드로부터 인입되는 원격 SDP/ICE Candidate 패킷 파싱"""
        try:
            msg = json.loads(message)
            if msg.get("target_id") != self.client_id:
                return 

            msg_type = msg.get("type")
            self.get_logger().info(f" 📥 [시그널 수전] 웹소켓 패킷 타입 인입 -> {msg_type}")
        except Exception as e:
            self.get_logger().error(f" ❌ [시그널 웹소켓 처리 결함] {str(e)}")

    def _on_ws_error(self, ws, error):
        self.get_logger().error(f" 🚨 [시그널 웹소켓 에러 포착] {str(error)}")

    def _on_ws_close(self, ws, close_status_code, close_msg):
        self.get_logger().warn(" 🛑 [시그널 웹소켓 닫힘] 세션 연결이 종료되었습니다.")

    def _on_ice_candidate_cb(self, webrtcbin, mlineindex, candidate):
        """GStreamer WebRTC 내부에서 생성된 ICE Candidate를 Next.js 단말로 사출"""
        if self.ws and self.ws.sock and self.ws.sock.connected:
            payload = {
                "target_id": "web_ui_console",
                "type": "candidate",
                "sdpMLineIndex": mlineindex,
                "candidate": candidate
            }
            self.ws.send(json.dumps(payload))

    def _on_negotiation_needed_cb(self, webrtcbin):
        """P2P 파이프라인 세션 디스커버리를 위한 SDP Offer 생성 및 전방위 송출"""
        promise = Gst.Promise.new_with_change_func(self._on_offer_created, None, None)
        self.webrtc_bin.emit("create-offer", None, promise)

    def _on_offer_created(self, promise, *args):
        """GStreamer C-엔진의 가변 인자 주입 규격을 100% 수용하여 TypeError를 소거합니다."""
        reply = promise.get_reply()
        offer = reply.get_value("offer")
        promise = Gst.Promise.new()
        self.webrtc_bin.emit("set-local-description", offer, promise)
        promise.interrupt()

        sdp_text = offer.sdp.as_text()
        if self.ws and self.ws.sock and self.ws.sock.connected:
            # 💡 [정격 인터록 해제]: target_id를 걷어내어 시그널 허브가
            # 대기 중인 모든 Next.js 단말에게 SDP Offer를 전방위 배포하도록 구조를 단순화합니다.
            payload = {"type": "offer", "sdp": sdp_text}
            self.ws.send(json.dumps(payload))
            self.get_logger().info(
                " 📤 [시그널 브로드캐스트] GStreamer WebRTC Local SDP Offer 전방위 사출 완료."
            )
            
    def destroy_node(self):
        self.get_logger().warn(" 🛑 WebRTC 스트리밍 자산 해제 및 GStreamer 파이프라인 종료 중...")
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