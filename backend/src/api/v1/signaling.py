from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict

router = APIRouter(prefix="/api/v1/signal", tags=["Signaling"])


class SignalingManager:
    """WebRTC 제어 평면 전담 웹소켓 시그널 허브 매니저"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, receiver_id: str):
        if receiver_id in self.active_connections:
            await self.active_connections[receiver_id].send_text(message)


manager = SignalingManager()


@router.websocket("/ws/{client_id}")
async def signaling_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            # SDP / ICE Candidate 텍스트 스트링 패킷 수수 루프 [cite: 92]
            data = await websocket.receive_text()
            # 코딩 에이전트가 패킷 파싱 후 Target 브라우저/GStreamer 송출기로 라우팅할 구현 영역
    except WebSocketDisconnect:
        manager.disconnect(client_id)
