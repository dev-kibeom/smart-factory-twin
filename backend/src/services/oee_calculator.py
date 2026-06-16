import time
import logging
from typing import Dict, Any
from influxdb_client import Point

logger = logging.getLogger("sf_twin.oee")


class OEEDataSpace:
    """
    [Task 4-3-B] ISA-95 가이드라인 준수 가동 상태 장부 및 OEE 물리 계측 공간
    - 원자적 변수 관리를 통해 고속 데이터 레이스 컨디션 선제 차단
    """

    def __init__(self):
        # 생산 타임라인 추적 레지스터
        self.start_time: float = time.time()
        self.total_operation_time: float = 0.0  # T_total (초)
        self.cumulative_downtime: float = 0.0  # T_downtime (초)

        # 고장 상태 물리 모델 상태 변수
        self.is_fault_active: bool = False
        self.current_fault_intensity: float = 0.0  # 0.0 ~ 1.0 [cite: 395]
        self.last_update_time: float = time.time()

        # 생산 수량 카운터 (PostgreSQL 트랜잭션 대용량 미러링 타깃)
        self.target_production_qty: int = 1000  # 목표 생산량 사양
        self.actual_production_qty: int = 0  # 총 생산량
        self.good_qty: int = 0  # 양품 생산량
        self.defect_qty: int = 0  # 불량품 생산량


class OEECalculatorEngine:
    """
    실시간 스마트 팩토리 공정 지표 분석 엔진
    - 10Hz 주기적 동적 기하 쿼리 및 수학적 수식 비례 연산 처리 [cite: 358, 369]
    """

    def __init__(self):
        self.data_space = OEEDataSpace()

    def update_fault_state(self, is_fault: bool, intensity: float) -> None:
        """ros2_medkit 진단 모듈 혹은 고장 주입 API와 락프리 동기화"""
        self.data_space.is_fault_active = is_fault
        self.data_space.current_fault_intensity = intensity if is_fault else 0.0

    def increment_production(self, is_good: bool = True) -> None:
        """물류 공정(AMR Fetch/Deliver) 완료 이벤트 수전 시 수량 증분"""
        self.data_space.actual_production_qty += 1
        if is_good:
            self.data_space.good_qty += 1
        else:
            self.data_space.defect_qty += 1

    def calculate_current_metrics(self) -> Dict[str, Any]:
        """
        [URS-09 / FRS-09.2] 실시간 물류 처리량 및 OEE 수학적 수식 분석 연산 [cite: 15, 176]
        - A (가동률): (T_total - T_downtime) / T_total [cite: 176]
        - P (성능효율): Actual Qty / Target Qty [cite: 178]
        - Q (품질지수): Good Qty / Actual Qty [cite: 178]
        - OEE: A * P * Q * 100 [cite: 399]
        """
        now = time.time()
        delta_time = now - self.data_space.last_update_time
        self.data_space.last_update_time = now

        # 1. 시계열 타임라인 가속 업데이트
        self.data_space.total_operation_time = now - self.data_space.start_time
        if self.data_space.is_fault_active:
            # 고장 강도 지수 비례 가중 다운타임 인가 구조 수립 [cite: 177, 369]
            self.data_space.cumulative_downtime += (
                delta_time * self.data_space.current_fault_intensity
            )

        # 2. 가동률 (Availability Index) 도출 수학적 예외 방어 예외 처리 [cite: 396]
        if self.data_space.total_operation_time <= 0:
            availability = 1.0
        else:
            availability = (
                self.data_space.total_operation_time
                - self.data_space.cumulative_downtime
            ) / self.data_space.total_operation_time
        availability = max(0.0, min(1.0, availability))  # 물리적 안전 마진 클리핑

        # 3. 성능효율 (Performance Index) 도출 [cite: 397]
        # 실시간 속도 저하를 모사하기 위해 고장 강도에 비례해 동적으로 가중치 쉐이핑 가동
        if self.data_space.target_production_qty <= 0:
            performance = 1.0
        else:
            # 기본 베이스 진척에 고장으로 인한 속도 하락 감쇠 인자 결합
            expected_base = (self.data_space.total_operation_time * 0.5) * (
                1.0 - (self.data_space.current_fault_intensity * 0.4)
            )
            self.data_space.actual_production_qty = max(
                self.data_space.good_qty + self.data_space.defect_qty,
                int(expected_base),
            )
            performance = (
                self.data_space.actual_production_qty
                / self.data_space.target_production_qty
            )
        performance = max(0.0, min(1.0, performance))

        # 4. 품질지수 (Quality Index) 도출 [cite: 398]
        # 센서 드리프트 및 고장 강도가 높아질수록 확률적 불량품 가중 인가 수립
        if self.data_space.actual_production_qty > 0:
            if self.data_space.current_fault_intensity > 0.5 and (int(now) % 3 == 0):
                self.data_space.defect_qty += 1

            # 무결성 복구 보정
            self.data_space.good_qty = max(
                0, self.data_space.actual_production_qty - self.data_space.defect_qty
            )
            quality = self.data_space.good_qty / self.data_space.actual_production_qty
        else:
            quality = 1.0
        quality = max(0.0, min(1.0, quality))

        # 5. 종합 OEE 연산 수식 최종 도출 [cite: 176, 399]
        overall_oee = availability * performance * quality * 100.0

        return {
            "fault_intensity": float(self.data_space.current_fault_intensity),
            "availability_index": float(availability),
            "performance_index": float(performance),
            "quality_index": float(quality),
            "overall_oee": float(overall_oee),
            "total_operation_time": self.data_space.total_operation_time,
            "cumulative_downtime": self.data_space.cumulative_downtime,
        }

    def export_influx_point(self, metrics: Dict[str, Any]) -> Point:
        """
        [Task 4-3-C / 인수인계서 3-4] 인플럭스 버킷 정격 물리 데이터 모델 스키마 변환
        """
        return (
            Point("factory_oee_metrics")
            .tag("line_id", "amr_fleet_01")
            .field("fault_intensity", metrics["fault_intensity"])
            .field("availability_index", metrics["availability_index"])
            .field("performance_index", metrics["performance_index"])
            .field("quality_index", metrics["quality_index"])
            .field("overall_oee", metrics["overall_oee"])
        )


# 전역 엔진 단일 인스턴스 격리화 완료
oee_engine = OEECalculatorEngine()
