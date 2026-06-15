# backend/src/api/v1/signaling.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import logging

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1/signal", tags=["Signaling Framework"])


class SignalingManager:
    """[URS-08/FRS-08.2] WebRTC 제어 평면 전담 실시간 멀티캐스팅 시그널 허브 아키텍처"""

    def __init__(self):
        # 액티브 커넥션 세션 관리 맵
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f" 📡 [시그널 채널 개통] Client Connected ➔ ID: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f" 📡 [시그널 채널 해제] Client Disconnected ➔ ID: {client_id}")

    async def broadcast_payload(self, sender_id: str, payload_str: str):
        """인입된 SDP / ICE 캔디데이트 패킷을 대상 브라우저 단말로 상호 투사 라우팅"""
        try:
            raw_json = json.loads(payload_str)
            target_id = raw_json.get("target_id")

            # 특정 타겟 지정 홉이 있을 경우 1:1 유니캐스트 라우팅 수행
            if target_id and target_id in self.active_connections:
                await self.active_connections[target_id].send_text(payload_str)
                return

            # 전체 분산 브로드캐스트 라우팅 (시그널링 터널 구현)
            for client_id, connection in self.active_connections.items():
                if client_id != sender_id:
                    await connection.send_text(payload_str)
        except Exception as e:
            logger.error(f" ❌ [시그널링 내부 패킷 교환 결함] {str(e)}")


manager = SignalingManager()


@router.websocket("/ws/{client_id}")
async def signaling_endpoint(websocket: WebSocket, client_id: str):
    """
    [Task 3-2] SDP / ICE 캔디데이트 실시간 분산 가교 웹소켓 관문 [cite: 92, 441]
    """
    await manager.connect(client_id, websocket)
    try:
        while True:
            # 30Hz 주기의 P2P 세션 디스커버리 텍스트 패킷 수수 루프 
            data = await websocket.receive_text()
            await manager.broadcast_payload(client_id, data)
    except WebSocketDisconnect:
        manager.disconnect(client_id) 
