# src/models/alarm.py
# ────────────────────────────────────────────────────────────────────────────
# [역할]
#   1. Pydantic v2 Request/Response 모델 정의
#   2. 알림 비즈니스 로직 및 실제 DB 스키마(partner_id 마스터 구조) 호환 SQL 실행
#
# [의존성]
#   utils/websc.py     → authenticateWS (웹소켓 인증)
#   utils/db.py        → findAll, findOne, save
#   utils/rediscl.py   → getRedis
#   models/notify.py   → sendNotify, notifyType, getRelativeTime
# ────────────────────────────────────────────────────────────────────────────

import json
from datetime import datetime
from typing import Optional, List
from src.utils.tokenset import decryptFromJwe
from src.utils.db import findAll, findOne, save
from src.utils.rediscl import getTokenRedis
from src.models.model import responseModel, alarmListModel, alarmReadModel, alarmSendModel, alarmResponse
from src.models.notify import sendNotify, notifyType, getRelativeTime
from src.utils.validatetok import validateToken

# 알림 타입 전체 목록 (typeCounts 집계용 - AI_AGENT 타입 추가 반영)
allTypes = [
    notifyType.USER,
    notifyType.CHECK,
    notifyType.CHART,
    notifyType.LEAF,
    notifyType.CUBE,
    notifyType.AI_AGENT,  # ★ AI Agent 위반 알람 대응 추가
]


# ============================================================
# ■ 공통 유틸
# ============================================================

def getUserIdFromUuid(uuid: str) -> Optional[str]:
    """
    [역할] Redis uuid → 토큰 복호화를 통해 실 유저 식별자인 partner_id(str) 조회
    [반환] partner_id(str) 또는 None (인증 실패)
    """
    # 1. 세션 검증 및 자동 갱신 모듈 호출
    authResponse = validateToken(uuid)
    
    # 인증 실패 시 그대로 반환
    if not authResponse["status"]:
        return None

    # 2. 검증 통과 후 최신 UUID 획득
    activeUuid = authResponse["data"]["uuid"]

    # 3. 최신 UUID를 통해 토큰 데이터베이스(sub)에서 partner_id 추출
    tokenRes = getTokenRedis(activeUuid)
    payLoad = decryptFromJwe(tokenRes["accessToken"])
    partnerId = payLoad.get("sub")
    
    if not partnerId:
        return None
    return str(partnerId)


def buildTypeCounts(partnerId: str) -> dict:
    """
    [역할] 실제 DB 컬럼(partner_id) 기준 타입별 읽지 않은 알림 개수 집계
    [반환] {"USER": 0, "AI_AGENT": 2, ...}
    """
    countSql = """
        SELECT type, COUNT(*) as cnt
        FROM `ALARM`
        WHERE partner_id = ?
          AND is_read   = 0
          AND delete_yn = 0
        GROUP BY type
    """
    rows   = findAll(countSql, (partnerId,))
    counts = {t: 0 for t in allTypes}
    for row in rows:
        if row["type"] in counts:
            counts[row["type"]] = row["cnt"]
    return counts


def getUnreadCount(partnerId: str) -> int:
    """[역할] 실제 DB 컬럼(partner_id) 기준 읽지 않은 전체 알림 총합 조회"""
    unreadSql = """
        SELECT COUNT(*) as cnt
        FROM `ALARM`
        WHERE partner_id = ?
          AND is_read   = 0
          AND delete_yn = 0
    """
    row = findOne(unreadSql, (partnerId,))
    return row["cnt"] if row else 0


def formatAlarm(row: dict) -> dict:
    """
    [역할] DB 조회 결과(partner_id 구조) → 프론트엔드 명세서 응답 형식 변환
    """
    createdAt = row.get("created_at")
    if isinstance(createdAt, str):
        createdAt = datetime.strptime(createdAt, "%Y-%m-%d %H:%M:%S")

    return {
        "id"        : row["id"],
        "type"      : row["type"],
        "title"     : row["title"],
        "content"   : row["content"],
        "isRead"    : bool(row["is_read"]),
        "createdAt" : createdAt.strftime("%Y-%m-%dT%H:%M:%SZ") if createdAt else None,
        "time"      : getRelativeTime(createdAt) if createdAt else "",
        "path"      : row["path"],
        "meta"      : json.loads(row["meta_json"]) if row.get("meta_json") else {},
    }


# ============================================================
# ■ 비즈니스 로직
# ============================================================

def getAlarmListProcess(alarmListModel: alarmListModel, companyId: int) -> alarmResponse:
    """
    알림 목록 조회 (테이블 파라미터 구조 정정 버전)
    """
    try:
        # Step 1. uuid → partner_id 조회
        partnerId = getUserIdFromUuid(alarmListModel.uuid)
        if not partnerId:
            return alarmResponse(False, "인증 정보가 유효하지 않습니다.", {})

        # Step 2. 실제 스키마 필드(partner_id) 기반 동적 WHERE 조건 생성
        conditions = ["partner_id = ?", "delete_yn = 0"]
        params     = [partnerId]

        if alarmListModel.type:
            conditions.append("type = ?")
            params.append(alarmListModel.type)

        if alarmListModel.types:
            typeList     = [t.strip() for t in alarmListModel.types.split(",")]
            placeholders = ", ".join(["?" for _ in typeList])
            conditions.append(f"type IN ({placeholders})")
            params.extend(typeList)

        if alarmListModel.isRead is not None:
            conditions.append("is_read = ?")
            params.append(1 if alarmListModel.isRead else 0)

        whereClause = " AND ".join(conditions)
        offset      = (alarmListModel.page - 1) * alarmListModel.size
        params.extend([alarmListModel.size, offset])

        # Step 3. ALARM 테이블 실 스키마 조회
        alarmSql = f"""
            SELECT id, type, title, content,
                   is_read, path, meta_json, created_at
            FROM `ALARM`
            WHERE {whereClause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = findAll(alarmSql, tuple(params))

        # Step 4. 집계 결과 반환
        return alarmResponse(True, "알림 목록 조회에 성공했습니다.", {
            "notifications" : [formatAlarm(row) for row in rows],
            "unreadCount"   : getUnreadCount(partnerId),
            "typeCounts"    : buildTypeCounts(partnerId),
        })

    except Exception as e:
        errMsg = str(e)
        print(f"[getAlarmListProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})


def readAlarmProcess(alarmReadModel: alarmReadModel, companyId: int) -> alarmResponse:
    """
    알림 읽음 처리 (partner_id 조건 매핑)
    """
    try:
        partnerId = getUserIdFromUuid(alarmReadModel.uuid)
        if not partnerId:
            return alarmResponse(False, "인증 정보가 유효하지 않습니다.", {})

        conditions = [
            "partner_id = ?",
            "delete_yn  = 0",
            "is_read    = 0",
        ]
        params = [partnerId]

        if alarmReadModel.types:
            placeholders = ", ".join(["?" for _ in alarmReadModel.types])
            conditions.append(f"type IN ({placeholders})")
            params.extend(alarmReadModel.types)

        whereClause = " AND ".join(conditions)
        save(f"UPDATE `ALARM` SET is_read = 1 WHERE {whereClause}", tuple(params))

        return alarmResponse(True, "알림 읽음 처리가 완료되었습니다.", {
            "uuid"        : alarmReadModel.uuid,
            "unreadCount" : getUnreadCount(partnerId),
            "typeCounts"  : buildTypeCounts(partnerId),
        })

    except Exception as e:
        errMsg = str(e)
        print(f"[readAlarmProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})


def deleteAlarmProcess(alarmId: int, uuid: str, companyId: int) -> alarmResponse:
    """
    알림 소프트 삭제 (partner_id 조건 매핑)
    """
    try:
        partnerId = getUserIdFromUuid(uuid)
        if not partnerId:
            return alarmResponse(False, "인증 정보가 유효하지 않습니다.", {})

        # 실제 존재하지 않는 company_id 컬럼을 배제하고 partner_id 조건으로 업데이트 수행
        save(
            "UPDATE `ALARM` SET delete_yn = 1 WHERE id = ? AND partner_id = ?",
            (alarmId, partnerId)
        )

        # 삭제 후 최신 목록 Top 20 리로드
        rows = findAll("""
            SELECT id, type, title, content,
                   is_read, path, meta_json, created_at
            FROM `ALARM`
            WHERE partner_id = ? AND delete_yn = 0
            ORDER BY created_at DESC LIMIT 20
        """, (partnerId,))

        return alarmResponse(True, "알림이 삭제되었습니다.", {
            "notifications" : [formatAlarm(row) for row in rows],
            "deletedCount"  : 1,
            "unreadCount"   : getUnreadCount(partnerId),
            "deletedId"     : alarmId,
        })

    except Exception as e:
        errMsg = str(e)
        print(f"[deleteAlarmProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})


async def sendAlarmProcess(alarmSendModel: alarmSendModel) -> alarmResponse:
    """알림 직접 전송 인터페이스"""
    try:
        await sendNotify(
            notifyType = alarmSendModel.notifyType,
            userId     = alarmSendModel.userId,     # notify.py 연동 시 partner_id가 전달됨
            companyId  = alarmSendModel.companyId,  # 내부 인자 구조 호환 유지
            meta       = alarmSendModel.meta,
        )
        return alarmResponse(True, "알림 전송 완료")

    except Exception as e:
        errMsg = str(e)
        print(f"[sendAlarmProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})