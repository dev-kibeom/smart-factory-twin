#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import jax
import jax.numpy as jnp
import paho.mqtt.client as mqtt
import json
import time

# JAX의 RTX GPU 메모리 preallocation 독점을 방지하여 랩톱 OOM 원천 차단
import os

os.environ["XLA_PYTHON_CLIENT_PREALLOCATE"] = "false"


class JAXPhysicsEngineNode(Node):
    """
    [URS-02/FRS-02.1] 3D 렌더링 오버헤드를 배제한 JAX 가속 기반 2D 고속 물리 에뮬레이터
    AMR의 비선형 동역학(Inertia, Friction 변화량)을 100Hz 단위로 JIT 컴파일 연산 수행
    """

    def __init__(self):
        super().__init__("jax_physics_engine_node")
        self.get_logger().info(
            "========================================================================="
        )
        self.get_logger().info(
            " 🚀 JAX 가속 고속 2D 물리 실행 레이어 가동 (스마트 스케일 다운 준수)"
        )
        self.get_logger().info(
            "========================================================================="
        )

        # 1. 초기 물리 상태 벡터 정의 (x, y, theta, linear_velocity, angular_velocity)
        self.state = jnp.array([0.0, 0.0, 0.0, 0.0, 0.0], dtype=jnp.float32)

        # 2. 동적 비선형 가변 파라미터 셋업 (질량 상태에 따른 관성 및 마찰 변동)
        self.inertia = 4.5  # kg·m²
        self.friction = 0.8  # N·m·s/rad
        self.dt = 0.01  # 100Hz 델타 타임 마진

        # 3. MOM 계층 분산 MQTT 브로커 연동 구성
        self.mqtt_broker_ip = "172.20.0.10"
        self.mqtt_port = 1883
        self.init_mqtt_client()

        # 4. 100Hz 고주파 물리 연단 루프 타이머 트리거 실행
        self.create_timer(self.dt, self.physics_loop)

    def init_mqtt_client(self):
        if hasattr(mqtt, "CallbackApiVersion"):
            self.mqtt_client = mqtt.Client(
                callback_api_version=mqtt.CallbackApiVersion.VERSION2
            )
        else:
            self.mqtt_client = mqtt.Client()

        try:
            self.mqtt_client.connect(self.mqtt_broker_ip, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            self.get_logger().info(
                " ✔ 분산 MQTT 브로커 고주파 물리 텔레메트리 사출 채널 체결 완료."
            )
        except Exception as e:
            self.get_logger().error(f" ❌ MQTT 브로커 소켓 연결 결함: {str(e)}")

    @staticmethod
    @jax.jit
    def update_dynamics_jit(state, u, inertia, friction, dt):
        """
        [수학적 타당성] 차동 주행 로봇(Differential Drive Robot) 비선형 동역학 행렬 연산의 JIT 최적화
        """
        x, y, theta, v, w = state
        v_target, w_target = u

        # 토크 제어 및 비선형 마찰 손실 모델 실증 ($T = I\dot{\omega} + b\omega$)
        dv = (v_target - v) / (inertia * 0.5) - (friction * v * dt)
        dw = (w_target - w) / inertia - (friction * w * dt)

        new_v = v + dv * dt
        new_w = w + dw * dt

        # 운동학적 상태 전이 행렬 매핑
        new_x = x + new_v * jnp.cos(theta) * dt
        new_y = y + new_v * jnp.sin(theta) * dt
        new_theta = theta + new_w * dt

        return jnp.array([new_x, new_y, new_theta, new_v, new_w], dtype=jnp.float32)

    def physics_loop(self):
        """100Hz 클록 주기로 가동되는 고주파 JAX 상태 업데이트 및 IT 전방위 스트리밍"""
        # 임무 레이어에서 수수할 제어 가상 입력값 (Linear target, Angular target)
        # 차순위 가동 시 Behavior Tree 노드와 토픽 링커 연결 예정 (현재는 스텁 타겟 유도)
        u_control = jnp.array([0.5, 0.1], dtype=jnp.float32)

        # JAX 가속 변환 직격 연산 수행
        self.state = self.update_dynamics_jit(
            self.state, u_control, self.inertia, self.friction, self.dt
        )

        # 고주파 물리 역학 실시간 데이터 패킷 정합
        telemetry_payload = {
            "robot_id": "amr_01",
            "x": float(self.state[0]),
            "y": float(self.state[1]),
            "theta": float(self.state[2]),
            "linear_velocity": float(self.state[3]),
            "angular_velocity": float(self.state[4]),
            "inertia": float(self.inertia),
            "friction": float(self.friction),
            "torque_nm": float(float(self.state[3]) * self.friction),
        }

        # [Task 1-3 역방향 링크 통합] 백엔드 Consumer 및 InfluxDB로 실시간 사출
        self.mqtt_client.publish(
            "smart_factory/telemetry/dynamics",
            json.dumps(telemetry_payload),
            qos=0,  # 고주파 데이터 스트림의 하드웨어 부하 경감을 위해 QOS 0 유도
        )


def main(args=None):
    rclpy.init(args=args)
    node = JAXPhysicsEngineNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("JAX 물리 엔진 노드가 정상 종료되었습니다.")
    finally:
        node.mqtt_client.loop_stop()
        node.mqtt_client.disconnect()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
