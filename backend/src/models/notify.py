# src/models/notify.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] 단일 sendNotify() 함수로 알림 전송 통일
#        타입별 설정은 NOTIFY_CONFIG에서 관리
#        웹소켓 전송은 utils/websc.py의 manager 사용
#
# [ERD FK 흐름]
#   USER.id    ──→ ALARM.user_id
#   COMPANY.id ──→ ALARM.company_id
# ────────────────────────────────────────────────────────────────────────────

import json
from datetime import datetime
from src.utils.websc import manager   # utils/websc.py에서 import
from src.utils.db import save


# ============================================================
# ■ 알림 타입 상수
# ============================================================

class notifyType:
    USER     = "USER"      # 사용자 초대/승인
    CHECK    = "CHECK"     # 데이터 승인/반려
    CHART    = "CHART"     # 보고서 생성
    LEAF     = "LEAF"      # ESG 관련
    CUBE     = "CUBE"      # 데이터셋 관련
    AI_AGENT = "AI_AGENT"  # ★ 추가: AI Agent가 감지한 위반 알림


# ============================================================
# ■ 타입별 알림 설정
# ── title, content : format() 치환 변수 사용
# ── path           : 클릭 시 이동 경로
# ── target         : user(개인) / company(회사전체) / all(전체)
# ============================================================

NOTIFY_CONFIG = {
    notifyType.USER: {
        "title"  : "신규 팀원 초대",
        "content": "신규 팀원 초대 요청이 승인되었습니다.",
        "path"   : "/manager/invite",
        "target" : "user",
    },
    notifyType.CHECK: {
        "title"  : "데이터 승인 반려",
        "content": "ESG 데이터 1분기 실적 승인이 반려되었습니다.",
        "path"   : "/onboarding",
        "target" : "user",
    },
    notifyType.CHART: {
        "title"  : "{title}",
        "content": "{content}",
        "path"   : "/dashboard/reports/{reportId}",
        "target" : "user",
    },
    notifyType.LEAF: {
        "title"  : "{title}",
        "content": "{content}",
        "path"   : "/leaf",
        "target" : "company",
    },
    notifyType.CUBE: {
        "title"  : "{title}",
        "content": "{content}",
        "path"   : "/cube",
        "target" : "company",
    },

    # ★ 추가: AI Agent 위반 알림
    notifyType.AI_AGENT: {
        "title"  : "{title}",                          # AI Agent가 생성한 알림 제목
        "content": "{content}",                        # AI Agent가 생성한 본문
        "path"   : "/dashboard/ai-alerts/{alertId}",   # 클릭 시 알림 상세 페이지
        "target" : "company",                          # 회사 전체 사용자에게 전송
    },
}

# ============================================================
# ■ 상대 시간 변환 유틸
# ============================================================

def getRelativeTime(createdAt: datetime) -> str:
    """
    [역할] datetime → '방금 전', 'N분 전', 'N시간 전', 'N일 전' 변환
    [사용] models/alarm.py의 formatAlarm()에서 호출
    """
    diff = datetime.now() - createdAt
    secs = int(diff.total_seconds())

    if secs < 60:
        return "방금 전"
    elif secs < 3600:
        return f"{secs // 60}분 전"
    elif secs < 86400:
        return f"{secs // 3600}시간 전"
    else:
        return f"{secs // 86400}일 전"


# ============================================================
# ■ 단일 알림 전송 함수
# ============================================================

async def sendNotify(
    notifyType : str,
    userId     : int,
    companyId  : int,
    meta       : dict = {},
):
    """
    [역할] 단일 알림 처리 함수
    [처리 순서]
    ├─ Step 1. NOTIFY_CONFIG 타입별 설정 조회
    ├─ Step 2. meta 값으로 title/content/path 문자열 치환
    ├─ Step 3. ALARM 테이블 DB 저장
    └─ Step 4. utils/websocket.py manager로 실시간 전송

    [전송 방식 — NOTIFY_CONFIG target 기준]
      user    → manager.sendToUser()    (개인)
      company → manager.sendToCompany() (회사 전체)
      all     → manager.broadcast()     (전체)
    """
    # ── Step 1. 타입별 설정 조회
    config = NOTIFY_CONFIG.get(notifyType)
    if not config:
        print(f"[sendNotify] 알 수 없는 알림 타입: {notifyType}")
        return

    # ── Step 2. 문자열 치환
    try:
        title   = config["title"].format(**meta)
        content = config["content"].format(**meta)
        path    = config["path"].format(**meta)
    except KeyError as e:
        print(f"[sendNotify] 치환 실패 — 누락된 meta 키: {e}")
        return

    # ── Step 3. ALARM 테이블 DB 저장
    # [FK] user_id → USER.id / company_id → COMPANY.id
    alarmSql = """
        INSERT INTO `ALARM` (
            partner_id, type,
            title, content, path,
            meta_json, is_read, delete_yn
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
    """
    alarmParams = (
        userId,
        companyId,
        notifyType,
        title,
        content,
        path,
        json.dumps(meta, ensure_ascii=False),
    )
    save(alarmSql, alarmParams)

    # ── Step 4. 웹소켓 실시간 전송 (명세서 응답 형식)
    message = {
        "id"        : None,
        "companyId" : companyId,
        "type"      : notifyType,
        "title"     : title,
        "content"   : content,
        "isRead"    : False,
        "createdAt" : datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time"      : "방금 전",
        "path"      : path,
        "meta"      : meta,
    }

    # ── 타입별 전송 방식 분기 (utils/websocket.py manager 사용)
    target = config["target"]
    if target == "all":
        await manager.broadcast(message)
    elif target == "company":
        await manager.sendToCompany(companyId, message)
    else:
        await manager.sendToUser(userId, message)