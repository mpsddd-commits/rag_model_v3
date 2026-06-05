# ════════════════════════════════════════════════════════════════
# notify.py 패치 가이드
#
# 첨부된 notify.py 파일에 아래 두 부분을 추가하면 AI Agent 알람이
# 정상적으로 통합 작동합니다.
# ════════════════════════════════════════════════════════════════

# ────────────────────────────────────────────────────────────
# [패치 1] notifyType 클래스에 AI_AGENT 추가
# ────────────────────────────────────────────────────────────
class notifyType:
    USER     = "USER"      # 사용자 초대/승인
    CHECK    = "CHECK"     # 데이터 승인/반려
    CHART    = "CHART"     # 보고서 생성
    LEAF     = "LEAF"      # ESG 관련
    CUBE     = "CUBE"      # 데이터셋 관련
    AI_AGENT = "AI_AGENT"  # ★ 추가: AI Agent가 감지한 위반 알림


# ────────────────────────────────────────────────────────────
# [패치 2] NOTIFY_CONFIG에 AI_AGENT 설정 추가
# ────────────────────────────────────────────────────────────
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

# ────────────────────────────────────────────────────────────
# [패치 3] (선택) ALARM 테이블 INSERT 시 type 확장 자동 처리
# ────────────────────────────────────────────────────────────
# 기존 sendNotify() 함수는 그대로 사용 가능합니다.
# AI_AGENT 타입은 notify_template로 동적 메시지가 들어가므로
# aiAgentNotify.py의 createAiAgentAlert()에서 미리 치환된
# title/content를 meta 딕셔너리로 넘기면 됩니다.

# ────────────────────────────────────────────────────────────
# [참고] sendNotify(AI_AGENT) 호출 예시
# ────────────────────────────────────────────────────────────
# await sendNotify(
#     notifyType = notifyType.AI_AGENT,
#     userId     = 1,
#     companyId  = 1,
#     meta       = {
#         "alertId" : 123,
#         "title"   : "FEOC 초과 — (주)케이알엠",
#         "content" : "케이알엠 FEOC 원료 12.5% — IRA 세액공제 위험 임계점 초과.",
#         "partner" : "(주)케이알엠",
#         "value"   : 12.5,
#         "severity": "WARN",
#     },
# )
