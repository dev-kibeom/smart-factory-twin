from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import get_db

app = FastAPI(title="Carbon Smart Factory Core Gateway", version="1.0.0")
security = HTTPBearer()

# 가상의 유효 마스터 토큰 (실제 구현 시 JWT 복호화 검증 레이어로 대체 가능)
VALID_API_TOKEN = "CARBON_MES_SECRET_EDGE_TOKEN_2026"


# [보안 레이어] 에지 로봇의 인증 정보 위조를 차단하는 Bearer 의존성 주입 함수
def verify_edge_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != VALID_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or Forged Bearer Token. Direct DB Access Blocked.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


class RoutingCompleteRequest(BaseModel):
    work_order_id: str
    routing_sequence: int
    equipment_id: str


@app.post("/api/auth/token")
def generate_mock_token():
    """개발 테스트용 마스터 토큰 발행 엔드포인트"""
    return {"access_token": VALID_API_TOKEN, "token_type": "bearer"}


@app.post("/api/routings/complete")
def complete_routing_step(
    payload: RoutingCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(
        verify_edge_token
    ),  # [Task 1-2 DoD] 토큰이 없으면 여기서 401 Cut
):
    """
    [FRS-05.1] 로봇 임무 완료 시 단일 REST 호출로 ERP ACID 트랜잭션 마감
    단순 갱신이 아닌, 차순위 조립 계획 재설계 및 자재 차감 비즈니스 체인 격리 전담
    """
    # 🧪 [Phase 1 통전 테스트용 Mock 데이터 정합성 반환]
    return {
        "status": "success",
        "message": f"Successfully mediated transaction. Equipment {payload.equipment_id} finished routing {payload.routing_sequence}.",
        "verified_by_gateway": True,
    }
