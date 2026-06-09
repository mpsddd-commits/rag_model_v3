# src/models/notify.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] 단일 sendNotify() 함수로 알림 전송 통일
#        타입별 설정은 NOTIFY_CONFIG에서 관리
#        웹소켓 전송은 utils/websc.py의 partner_id 기반 v2.0 manager 사용
#
# [ERD FK 흐름]
#   COMPANY.partner_id ──→ ALARM.partner_id
# ────────────────────────────────────────────────────────────────────────────

import json
from datetime import datetime
from src.utils.websc import manager   # utils/websc.py에서 v2.0 싱글톤 인스턴스 import
from src.utils.db import save


# ============================================================
# ■ 알림 타입 상수
# ============================================================

class notifyType:
    USER     = "USER"       # 사용자 초대/승인
    CHECK    = "CHECK"      # 데이터 승인/반려
    CHART    = "CHART"      # 보고서 생성
    LEAF     = "LEAF"       # ESG 관련
    CUBE     = "CUBE"       # 데이터셋 관련
    AI_AGENT = "AI_AGENT"   # AI Agent 위반 알림


# ============================================================
# ■ 타입별 알림 설정
# ── title, content : format() 치환 변수 사용
# ── path           : 클릭 시 이동 경로
# ── target         : partner(협력사 타겟) / all(전체 브로드캐스트)
# ============================================================

NOTIFY_CONFIG = {
    notifyType.USER: {
        "title"  : "신규 팀원 초대",
        "content": "신규 팀원 초대 요청이 승인되었습니다.",
        "path"   : "/manager/invite",
        "target" : "partner",
    },
    notifyType.CHECK: {
        "title"  : "데이터 승인 반려",
        "content": "ESG 데이터 1분기 실적 승인이 반려되었습니다.",
        "path"   : "/onboarding",
        "target" : "partner",
    },
    notifyType.CHART: {
        "title"  : "{title}",
        "content": "{content}",
        "path"   : "/dashboard/reports/{reportId}",
        "target" : "partner",
    },
    notifyType.LEAF: {
        "title"  : "{title}",
        "content": "{content}",
        "path"   : "/leaf",
        "target" : "partner",
    },
    notifyType.CUBE: {
        "title"  : "{title}",
        "content": "{content}",
        "path"   : "/cube",
        "target" : "partner",
    },

    # ★ AI Agent 위반 알림 (v2.0 단일 partner 체계 수렴)
    notifyType.AI_AGENT: {
        "title": "🔴 [ESG 경고] {partner_name} 감사 결과 - {status}",
        "content": "감사 결과 {status} 판정되었습니다. 조치 계획: {action_short}",
        "path": "/esg/dashboard?partnerId={partner_id}",
        "target": "partner" 
    },
}


# ============================================================
# ■ 상대 시간 변환 유틸
# ============================================================

def getRelativeTime(createdAt: datetime) -> str:
    """
    [역할] datetime → '방금 전', 'N분 전', 'N시간 전', 'N일 전' 변환
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
# ■ 단일 알림 전송 함수 (v2.0 완전 융합 버전)
# ============================================================

async def sendNotify(
    notifyType : str,
    partnerId  : str,
    companyId  : int,
    meta       : dict = {},
):
    """
    [역할] 단일 알림 처리 함수
    [처리 순서]
    ├─ Step 1. NOTIFY_CONFIG 타입별 설정 조회
    ├─ Step 2. meta 값으로 title/content/path 문자열 치환
    ├─ Step 3. ALARM 테이블 DB 저장 (이력 보존)
    └─ Step 4. utils/websc.py v2.0 manager 규칙으로 실시간 전송

    [전송 방식 — v2.0 리팩토링 규격 수렴]
      all     → manager.broadcast()     (전체 실시간 송출)
      partner → manager.sendToPartner() (특정 partner_id 지정 정밀 송출)
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
    alarmSql = """
        INSERT INTO `ALARM` (
            partner_id, company_id, type,
            title, content, path,
            meta_json, is_read, delete_yn
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
    """
    alarmParams = (
        partnerId,
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
        "partnerId" : partnerId,
        "type"      : notifyType,
        "title"     : title,
        "content"   : content,
        "isRead"    : False,
        "createdAt" : datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "time"      : "방금 전",
        "path"      : path,
        "meta"      : meta,
    }

    # ── v2.0 단일 키 아키텍처 연동 전송 분기
    target = config["target"]
    if target == "all":
        # 1. 시스템 전체 실시간 전송
        await manager.broadcast(message)
    else:
        # 2. partner 타겟 지정 실시간 정밀 전송 (websc.py의 정형화된 아규먼트 구조인 partnerId 매핑)
        await manager.sendToPartner(partnerId, message)