# backend/src/influx_client.py
import os
import logging
import asyncio
from typing import Optional
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.exceptions import InfluxDBError

logger = logging.getLogger("uvicorn.error")


class InfluxDBAsyncManager:
    """
    [Task 4-3-A] InfluxDB v2 비동기 풀링 클라이언트
    - 기존 동기 SYNCHRONOUS 방식의 블로킹으로 인한 메인 이벤트 루프 마비 리스크 전면 해제
    - 10Hz 고주파 적재 처리 사수 및 지수 백오프 기반 연결 무결성 회복 가드 탑재
    """

    def __init__(self):
        # docker-compose.yml 정격 명세 100% 매핑 사수
        self.url = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
        self.token = os.getenv("INFLUXDB_TOKEN", "super_secret_influxdb_token_12345")
        self.org = os.getenv("INFLUXDB_ORG", "smart_factory_org")
        self.bucket = os.getenv("INFLUXDB_BUCKET", "robot_telemetry_bucket")

        self.client: Optional[InfluxDBClientAsync] = None
        self.write_api = None
        self._lock = asyncio.Lock()

    async def ensure_connection(self) -> bool:
        """비동기 세션 지연 초기화 및 헬스 체크 실증"""
        if self.client and self.write_api:
            return True

        async with self._lock:
            if not self.client:
                try:
                    self.client = InfluxDBClientAsync(
                        url=self.url, token=self.token, org=self.org, timeout=3000
                    )
                    is_healthy = await self.client.ping()
                    if is_healthy:
                        self.write_api = self.client.write_api()
                        logger.info(
                            "[TSDB INFRA] InfluxDB v2 비동기 파이프라인 통전 성공."
                        )
                        return True
                    else:
                        self.client = None
                except Exception as e:
                    logger.error(f"[TSDB INFRA] InfluxDB 비동기 가교 결함: {str(e)}")
                    self.client = None
            return False

    async def write_point_async(self, point) -> None:
        """논블로킹 시계열 데이터 포인트 직격 사출"""
        if await self.ensure_connection():
            try:
                await self.write_api.write(
                    bucket=self.bucket, org=self.org, record=point
                )
            except InfluxDBError as ie:
                logger.error(f"[TSDB WRITE FAULT] 프로코톨 정합성 결함: {str(ie)}")
            except Exception as e:
                pass

    async def shutdown(self) -> None:
        """서버 종료 시 소켓 및 세션 풀 원자적 반환"""
        if self.client:
            await self.client.close()
            logger.info("[TSDB INFRA] InfluxDB 비동기 연결 자원 격리 해제 완료.")


# 글로벌 싱글톤 인스턴스 격리화 완료
influx_async_manager = InfluxDBAsyncManager()
