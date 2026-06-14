import time
from src.core.influx_client import (
    influx_client,
)  # 1.7호 인프라 자산 TSDB 링커 수입


class OeeCalculatorService:
    """[ISA-95 Layer 3] 고빈도 시계열 데이터 결합형 실시간 공정 KPI 증명 모듈"""

    def __init__(self):
        self.bucket = "robot_telemetry_bucket"
        self.org = "smart_factory_org"
        self.query_api = (
            influx_client.query_api()
        )  # Flux 쿼리 조회 엔진 연동 

    def calculate_runtime_oee(self, total_planned_time_sec: float) -> dict:
        """비헤이비어 트리 복구 지연 시간을 다운타임에 반영하여 가동률(A) 및 OEE 동적 도출"""

        # [Flux Query] 지난 10분간 로봇 에이전트의 비정상 정체 다운타임 총합 산출
        downtime_query = f'''
            from(bucket: "{self.bucket}")
            |> range(start: -10m)
            |> filter(fn: (r) => r["_measurement"] == "amr_dynamics")
            |> filter(fn: (r) => r["system_status"] == "FAULT")
            |> count()
        '''

        # 실전 환경 모사 및 고장 상황 발생 시 다운타임 누적 항 그래프 하락 수식 모델 연동
        try:
            result = self.query_api.query(org=self.org, query=downtime_query)
            fault_ticks = sum(
                [record.get_value() for table in result for record in table]
            )
            downtime_sec = (
                fault_ticks * 0.033
            )  # 30Hz 제어 주기 역산 누적 다운타임
        except Exception:
            downtime_sec = 0.0

        # 설비종합효율 수학적 수식 연산 레이어 마감
        # 가동률 A = (총 계획 시간 - 다운타임) / 총 계획 시간 
        availability = (
            (total_planned_time_sec - downtime_sec) / total_planned_time_sec
            if total_planned_time_sec > 0
            else 0.0
        )
        performance = 0.95  # OpenPLC 누적 가동 주기 기반 고정 마진 (예시) 
        quality = 0.99  # 모터 전류 마모 징후 검출 횟수 합산 반영률 (예시) 

        oee = availability * performance * quality  # OEE = A x P x Q

        return {
            "oee": round(oee * 100, 2),
            "availability": round(availability * 100, 2),
            "downtime_sec": round(downtime_sec, 2),
            "timestamp": time.time(),
        }
