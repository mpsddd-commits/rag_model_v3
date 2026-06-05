# src/models/alarm.py
# ────────────────────────────────────────────────────────────────────────────
# [역할]
#   1. Pydantic v2 Request/Response 모델 정의
#   2. 알림 비즈니스 로직 및 SQL 실행
#
# [의존성]
#   utils/websc.py → authenticateWS (웹소켓 인증)
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

# 알림 타입 전체 목록 (typeCounts 집계용)
allTypes = [
    notifyType.USER,
    notifyType.CHECK,
    notifyType.CHART,
    notifyType.LEAF,
    notifyType.CUBE,
    notifyType.AI_AGENT,
]


# ============================================================
# ■ 공통 유틸
# ============================================================

def getUserIdFromUuid(uuid: str) -> Optional[int]:
    """
    [역할] Redis uuid → user_id 조회 공통 함수
    [반환] user_id(int) 또는 None (인증 실패)
    [사용] 각 Process 함수에서 인증 처리 시 호출
    """
    # 1. 세션 검증 및 자동 갱신 모듈 호출
    # 이 한 줄로 Redis 조회, Access 만료 체크, Refresh 재발급, DB/Redis 업데이트가 완료됩니다.
    authResponse = validateToken(uuid)
    
    # 인증 실패 시 (세션 만료, 리프레시 만료 등) 그대로 반환
    if not authResponse["status"]:
        return authResponse

    # 2. 검증 통과 후 최신 UUID 획득
    # 재발급되었다면 신규 UUID가, 유효하다면 기존 UUID가 들어있습니다.
    activeUuid = authResponse["data"]["uuid"]

    # 3. 최신 UUID를 통해 유저 ID(sub) 추출
    # Redis에서 토큰을 가져와 복호화하여 sub(userId)를 얻습니다.
    tokenRes = getTokenRedis(activeUuid)
    payLoad = decryptFromJwe(tokenRes["accessToken"])
    userId = payLoad.get("sub")
    
    if not userId:
        return None
    return userId


def buildTypeCounts(userId: int, companyId: int) -> dict:
    """
    [역할] 타입별 읽지 않은 알림 개수 집계
    [반환] {"USER": 1, "CHECK": 0, "CHART": 0, "LEAF": 0, "CUBE": 0}
    """
    countSql = """
        SELECT type, COUNT(*) as cnt
        FROM `ALARM`
        WHERE user_id    = ?
          AND company_id = ?
          AND is_read    = 0
          AND delete_yn  = 0
        GROUP BY type
    """
    rows   = findAll(countSql, (userId, companyId))
    counts = {t: 0 for t in allTypes}
    for row in rows:
        if row["type"] in counts:
            counts[row["type"]] = row["cnt"]
    return counts


def getUnreadCount(userId: int, companyId: int) -> int:
    """[역할] 읽지 않은 전체 알림 개수 조회"""
    unreadSql = """
        SELECT COUNT(*) as cnt
        FROM `ALARM`
        WHERE user_id    = ?
          AND company_id = ?
          AND is_read    = 0
          AND delete_yn  = 0
    """
    row = findOne(unreadSql, (userId, companyId))
    return row["cnt"] if row else 0


def formatAlarm(row: dict) -> dict:
    """
    [역할] DB 조회 결과 → 명세서 응답 형식 변환
    [처리]
      created_at  → time(상대시간) 변환  ← utils/notify.py getRelativeTime() 사용
      meta_json   → dict 변환
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
    알림 목록 조회

    [처리 순서]
    ├─ Step 1. uuid → user_id 조회
    ├─ Step 2. 동적 WHERE 조건 생성
    ├─ Step 3. ALARM 테이블 조회 (페이지네이션)
    └─ Step 4. unreadCount + typeCounts 집계 반환
    """
    try:
        userId = getUserIdFromUuid(alarmListModel.uuid)
        if not userId:
            return alarmResponse(False, "인증 정보가 유효하지 않습니다.", {})

        conditions = ["user_id = ?", "company_id = ?", "delete_yn = 0"]
        params     = [userId, companyId]

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

        alarmSql = f"""
            SELECT id, type, title, content,
                   is_read, path, meta_json, created_at
            FROM `ALARM`
            WHERE {whereClause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = findAll(alarmSql, tuple(params))

        return alarmResponse(True, "알림 목록 조회에 성공했습니다.", {
            "notifications" : [formatAlarm(row) for row in rows],
            "unreadCount"   : getUnreadCount(userId, companyId),
            "typeCounts"    : buildTypeCounts(userId, companyId),
        })

    except Exception as e:
        errMsg = str(e)
        print(f"[getAlarmListProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})


def readAlarmProcess(alarmReadModel: alarmReadModel, companyId: int) -> alarmResponse:
    """
    알림 읽음 처리

    [처리 순서]
    ├─ Step 1. uuid → user_id 조회
    ├─ Step 2. types 유무에 따라 전체 or 유형별 읽음 처리
    └─ Step 3. unreadCount + typeCounts 반환
    """
    try:
        userId = getUserIdFromUuid(alarmReadModel.uuid)
        if not userId:
            return alarmResponse(False, "인증 정보가 유효하지 않습니다.", {})

        conditions = [
            "user_id    = ?",
            "company_id = ?",
            "delete_yn  = 0",
            "is_read    = 0",
        ]
        params = [userId, companyId]

        if alarmReadModel.types:
            placeholders = ", ".join(["?" for _ in alarmReadModel.types])
            conditions.append(f"type IN ({placeholders})")
            params.extend(alarmReadModel.types)

        whereClause = " AND ".join(conditions)
        save(f"UPDATE `ALARM` SET is_read = 1 WHERE {whereClause}", tuple(params))

        return alarmResponse(True, "알림 읽음 처리가 완료되었습니다.", {
            "uuid"        : alarmReadModel.uuid,
            "unreadCount" : getUnreadCount(userId, companyId),
            "typeCounts"  : buildTypeCounts(userId, companyId),
        })

    except Exception as e:
        errMsg = str(e)
        print(f"[readAlarmProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})


def deleteAlarmProcess(alarmId: int, uuid: str, companyId: int) -> alarmResponse:
    """
    알림 소프트 삭제

    [처리 순서]
    ├─ Step 1. uuid → user_id 조회
    ├─ Step 2. ALARM 소프트 삭제 (delete_yn = 1)
    └─ Step 3. 삭제 후 최신 목록 반환
    """
    try:
        userId = getUserIdFromUuid(uuid)
        if not userId:
            return alarmResponse(False, "인증 정보가 유효하지 않습니다.", {})

        save(
            "UPDATE `ALARM` SET delete_yn = 1 WHERE id = ? AND user_id = ? AND company_id = ?",
            (alarmId, userId, companyId)
        )

        rows = findAll("""
            SELECT id, type, title, content,
                   is_read, path, meta_json, created_at
            FROM `ALARM`
            WHERE user_id = ? AND company_id = ? AND delete_yn = 0
            ORDER BY created_at DESC LIMIT 20
        """, (userId, companyId))

        return alarmResponse(True, "알림이 삭제되었습니다.", {
            "notifications" : [formatAlarm(row) for row in rows],
            "deletedCount"  : 1,
            "unreadCount"   : getUnreadCount(userId, companyId),
            "deletedId"     : alarmId,
        })

    except Exception as e:
        errMsg = str(e)
        print(f"[deleteAlarmProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})


async def sendAlarmProcess(alarmSendModel: alarmSendModel) -> alarmResponse:
    """알림 전송 — models/notify.py sendNotify() 호출"""
    try:
        await sendNotify(
            notifyType = alarmSendModel.notifyType,
            userId     = alarmSendModel.userId,
            companyId  = alarmSendModel.companyId,
            meta       = alarmSendModel.meta,
        )
        return alarmResponse(True, "알림 전송 완료")

    except Exception as e:
        errMsg = str(e)
        print(f"[sendAlarmProcess ERROR] {errMsg}")
        return alarmResponse(False, f"오류 발생 : {errMsg}", {})