# src/utils/websocket.py
# ────────────────────────────────────────────────────────────────────────────
# [v2.0] 2026-06-05 — partner_id 기반 전면 리팩토링 (user_id/company_id 레거시 제거)
# [v1.0] 초기 버전 — user_id / company_id 기반
#
# [역할] 웹소켓 관련 모든 공통 기능 모듈화
#
# [아키텍처 변경 사항]
#   기존: USER 테이블의 user_id + COMPANY 테이블의 company_id (2키 체계)
#   변경: COMPANY 테이블의 partner_id 단일 마스터 식별자 (1키 체계)
#
# [모듈 구성]
#   ConnectionManager : 연결 풀 관리 (connect/disconnect/send)
#   authenticateWS    : 웹소켓 토큰 인증 (Redis uuid → partner_id)
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
        # [v2.0] partner_id → WebSocket 매핑 (단일 키 체계)
        # [FK] partner_id → COMPANY.partner_id
        self.connections: dict[str, WebSocket] = {}

    # ── 연결 등록
    async def connect(self, websocket: WebSocket, partnerId: str):
        """
        [역할] 웹소켓 연결 수락 및 연결 풀 등록
        [v2.0] partner_id 단일 키로 연결 관리
        [FK] partner_id → COMPANY.partner_id
        """
        await websocket.accept()
        self.connections[partnerId] = websocket
        print(f"[WS 연결] partner_id={partnerId}")

    # ── 연결 해제
    def disconnect(self, partnerId: str):
        """[역할] 연결 풀에서 협력사 제거"""
        self.connections.pop(partnerId, None)
        print(f"[WS 해제] partner_id={partnerId}")

    # ── 특정 협력사에게 전송
    async def sendToPartner(self, partnerId: str, message: dict):
        """
        [역할] 특정 협력사 1곳에게 알림 전송
        [v2.0] user_id → partner_id 변경
        [FK] partner_id → COMPANY.partner_id
        """
        websocket = self.connections.get(partnerId)
        if websocket:
            try:
                await websocket.send_text(
                    json.dumps(message, ensure_ascii=False)
                )
            except Exception as e:
                print(f"[WS 전송 실패] partner_id={partnerId} error={e}")
                self.connections.pop(partnerId, None)

    # ── 복수 협력사에게 전송
    async def sendToPartners(self, partnerIds: list[str], message: dict):
        """
        [역할] 지정된 복수 협력사에게 알림 전송
        [v2.0] company_id 기반 그룹 전송 → partner_id 리스트 기반으로 변경
        [사용 예시] 특정 공급망 계층(1차/2차/3차)의 모든 협력사에게 전송
        """
        for partnerId in partnerIds:
            await self.sendToPartner(partnerId, message)

    # ── 전체 브로드캐스트
    async def broadcast(self, message: dict):
        """
        [역할] 현재 연결된 모든 협력사에게 전송
        [사용] SYSTEM 타입 알림
        """
        for partnerId, websocket in list(self.connections.items()):
            try:
                await websocket.send_text(
                    json.dumps(message, ensure_ascii=False)
                )
            except Exception as e:
                print(f"[WS 브로드캐스트 실패] partner_id={partnerId} error={e}")
                self.connections.pop(partnerId, None)

    # ── 연결 여부 확인
    def isConnected(self, partnerId: str) -> bool:
        """[역할] 특정 협력사의 웹소켓 연결 여부 반환"""
        return partnerId in self.connections

    # ── 현재 접속자 수
    def getConnectedCount(self) -> int:
        """[역할] 현재 연결된 총 협력사 수 반환"""
        return len(self.connections)

    # ── 현재 접속 중인 partner_id 목록
    def getConnectedPartners(self) -> list[str]:
        """[역할] 현재 연결된 모든 partner_id 목록 반환"""
        return list(self.connections.keys())


# ============================================================
# ■ 웹소켓 인증 모듈
# ============================================================

async def authenticateWS(websocket: WebSocket, token: str) -> str | None:
    """
    [역할] 웹소켓 연결 요청의 토큰 인증
           Redis에서 uuid → partner_id 조회 후 반환

    [v2.0] 반환값: user_id(int) → partner_id(str) 변경

    [반환]
      partner_id (str) : 인증 성공
      None             : 인증 실패 → 웹소켓 강제 종료 (code=4001)

    [사용]
      apis/alarm.py의 websocketEndpoint에서 호출
    """
    tokenData = getTokenRedis(token)
    if not tokenData:
        await websocket.close(code=4001)
        print(f"[WS 인증 실패] 유효하지 않은 토큰: {token}")
        return None

    # [v2.0] user_id → partner_id (id 필드에 partner_id가 저장됨)
    partnerId = tokenData.get("id")
    if not partnerId:
        await websocket.close(code=4001)
        print(f"[WS 인증 실패] partner_id 없음")
        return None

    return partnerId


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
    data = await websocket.receive_text()
    if data == "ping":
        await websocket.send_text("pong")
    return data


# ============================================================
# ■ 싱글톤 인스턴스 (전역 사용)
# ============================================================

manager = ConnectionManager()
