# src/apis/alarm.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] HTTP/WebSocket 요청 수신 후 models/alarm.py에 위임
#        웹소켓 인증/ping/pong은 utils/websc.py 모듈 사용
# ────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Header, Query
from src.utils.websc import manager, authenticateWS, handlePingPong  # 모듈 import
from src.models.alarm import getAlarmListProcess, readAlarmProcess, deleteAlarmProcess, sendAlarmProcess
from src.models.model import alarmResponse, alarmListModel, alarmReadModel, alarmSendModel

router = APIRouter()


# ── WebSocket — 실시간 알림
@router.websocket("/ws")
async def alarmWebSocket(
    websocket  : WebSocket,
    token      : str = Query(..., description="Bearer Access Token"),
):
    # utils/websc.py — 인증 처리
    partnerId = await authenticateWS(websocket, token)
    if not partnerId:
        return

    # utils/websc.py — 연결 등록
    await manager.connect(websocket, partnerId)
    try:
        while True:
            # utils/websc.py — ping/pong 처리
            await handlePingPong(websocket)
    except WebSocketDisconnect:
        # utils/websc.py — 연결 해제
        manager.disconnect(partnerId)


# ── POST — 알림 목록 조회
@router.post("",
    summary="알림 목록 조회",
    response_model=alarmResponse,
    description="알람 목록 조회")

def getAlarms(
    alarmListModel : alarmListModel,
    partnerId      : str = Header(..., alias="PartnerId"),
):
    return getAlarmListProcess(alarmListModel, partnerId)


# ── PATCH — 알림 읽음 처리
@router.patch("",
    summary="알림 읽음 처리",
    response_model=alarmResponse,
    description="개별 또는 전체 알람을 읽음 상태로 변경")

def patchAlarm(
    alarmReadModel : alarmReadModel,
    partnerId      : str = Header(..., alias="PartnerId"),
):
    return readAlarmProcess(alarmReadModel, partnerId)


# ── DELETE — 알림 삭제
@router.delete("/{alarmId}",
    summary="알림 삭제",
    response_model=alarmResponse,
    description="알림 목록 삭제")

def alarmDel(
    alarmId   : int,
    uuid      : str = Query(..., description="Redis uuid"),
):
    return deleteAlarmProcess(alarmId, uuid)


# ── POST — 알림 전송
@router.post("/send",
    summary="알림 전송",
    response_model=alarmResponse,
    description="단일 알림 전송")

async def sendAlarm(alarmSendModel: alarmSendModel):
    return await sendAlarmProcess(alarmSendModel)
