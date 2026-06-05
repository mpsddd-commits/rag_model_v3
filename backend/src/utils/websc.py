# src/utils/websocket.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] 웹소켓 관련 모든 공통 기능 모듈화
#
# [모듈 구성]
#   ConnectionManager : 연결 풀 관리 (connect/disconnect/send)
#   authenticateWS    : 웹소켓 토큰 인증 (Redis uuid → user_id)
#   handlePingPong    : 연결 유지 ping/pong 처리
# ────────────────────────────────────────────────────────────────────────────

import json
from fastapi import WebSocket
from src.utils.rediscl import getTokenRedis


# ============================================================
# ■ ConnectionManager — 연결 풀 관리
# ============================================================

class ConnectionManager:
    def __init__(self):
        # user_id → WebSocket 매핑
        # [FK] user_id → USER.id
        self.connections: dict[int, WebSocket] = {}

        # company_id → [user_id, ...] 매핑
        # [FK] company_id → COMPANY.id
        self.companyConnections: dict[int, list[int]] = {}

    # ── 연결 등록
    async def connect(self, websocket: WebSocket, userId: int, companyId: int):
        """
        [역할] 웹소켓 연결 수락 및 연결 풀 등록
        [FK] user_id → USER.id / company_id → COMPANY.id
        """
        await websocket.accept()
        self.connections[userId] = websocket

        if companyId not in self.companyConnections:
            self.companyConnections[companyId] = []
        if userId not in self.companyConnections[companyId]:
            self.companyConnections[companyId].append(userId)

        print(f"[WS 연결] user_id={userId} company_id={companyId}")

    # ── 연결 해제
    def disconnect(self, userId: int, companyId: int):
        """[역할] 연결 풀에서 사용자 제거"""
        self.connections.pop(userId, None)

        if companyId in self.companyConnections:
            if userId in self.companyConnections[companyId]:
                self.companyConnections[companyId].remove(userId)
            if not self.companyConnections[companyId]:
                del self.companyConnections[companyId]

        print(f"[WS 해제] user_id={userId} company_id={companyId}")

    # ── 특정 사용자에게 전송
    async def sendToUser(self, userId: int, message: dict):
        """
        [역할] 특정 사용자 1명에게 알림 전송
        [사용] USER / CHECK / CHART 타입
        """
        websocket = self.connections.get(userId)
        if websocket:
            try:
                await websocket.sendText(
                    json.dumps(message, ensureAscii=False)
                )
            except Exception as e:
                print(f"[WS 전송 실패] user_id={userId} error={e}")
                self.connections.pop(userId, None)

    # ── 특정 회사 전체에게 전송
    async def sendToCompany(self, companyId: int, message: dict):
        """
        [역할] 특정 회사 전체 사용자에게 알림 전송
        [사용] LEAF / CUBE 타입
        [FK] company_id → COMPANY.id
        """
        userIds = self.companyConnections.get(companyId, [])
        for userId in userIds:
            await self.sendToUser(userId, message)

    # ── 전체 브로드캐스트
    async def broadcast(self, message: dict):
        """
        [역할] 현재 연결된 모든 사용자에게 전송
        [사용] SYSTEM 타입
        """
        for userId, websocket in list(self.connections.items()):
            try:
                await websocket.sendText(
                    json.dumps(message, ensureAscii=False)
                )
            except Exception as e:
                print(f"[WS 브로드캐스트 실패] user_id={userId} error={e}")
                self.connections.pop(userId, None)

    # ── 연결 여부 확인
    def isConnected(self, userId: int) -> bool:
        """[역할] 특정 사용자의 웹소켓 연결 여부 반환"""
        return userId in self.connections


# ============================================================
# ■ 웹소켓 인증 모듈
# ============================================================

async def authenticateWS(websocket: WebSocket, token: str) -> int | None:
    """
    [역할] 웹소켓 연결 요청의 토큰 인증
           Redis에서 uuid → user_id 조회 후 반환

    [반환]
      user_id (int) : 인증 성공
      None          : 인증 실패 → 웹소켓 강제 종료 (code=4001)

    [사용]
      apis/alarm.py의 websocketEndpoint에서 호출
    """
    tokenData = getTokenRedis(token)
    if not tokenData:
        await websocket.close(code=4001)
        print(f"[WS 인증 실패] 유효하지 않은 토큰: {token}")
        return None

    userId = tokenData.get("user_id")
    if not userId:
        await websocket.close(code=4001)
        print(f"[WS 인증 실패] user_id 없음")
        return None

    return userId


# ============================================================
# ■ ping/pong 처리 모듈
# ============================================================

async def handlePingPong(websocket: WebSocket) -> str:
    """
    [역할] 클라이언트 메시지 수신 및 ping/pong 연결 유지 처리

    [흐름]
      클라이언트 "ping" 전송
          → 서버 "pong" 응답
          → 연결 유지

    [반환]
      수신된 메시지 문자열 (ping 외 메시지 처리 확장 가능)

    [사용]
      apis/alarm.py의 websocketEndpoint while 루프에서 호출
    """
    data = await websocket.receiveText()
    if data == "ping":
        await websocket.sendText("pong")
    return data


# ============================================================
# ■ 싱글톤 인스턴스 (전역 사용)
# ============================================================

manager = ConnectionManager()