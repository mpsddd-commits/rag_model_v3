# src/apis/aiAgent.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] AI Agent HTTP API 엔드포인트
#        models/aiAgentNotify.py 비즈니스 로직에 위임
#
# [엔드포인트]
#   POST   /ai-agent/analyze         AI 전체 분석 실행 (MainDashboard 버튼)
#   GET    /ai-agent/alerts          AI 알림 목록 조회
#   PATCH  /ai-agent/alerts/{id}/ack 알림 확인 처리
#   PATCH  /ai-agent/alerts/{id}/resolve 알림 해소 처리
#   GET    /ai-agent/runs            실행 로그 조회
#   GET    /ai-agent/rules           룰셋 조회
# ────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Query, Header
from typing import Optional
from src.models.aiAgentModel import (
    aiAgentAnalyzeModel, aiAgentAckModel, aiAgentResolveModel, aiAgentResponse
)
from src.models.aiAgentNotify import (
    runAiAgentAnalysis,
    getAiAgentAlertList,
    acknowledgeAiAgentAlert,
    resolveAiAgentAlert,
    getAiAgentRunLogList,
)
from src.utils.db import findAll
from src.models.alarm import getUserIdFromUuid

router = APIRouter()


# ── POST — AI 전체 분석 실행
@router.post("/analyze",
    summary="AI Agent 전체 분석 실행",
    response_model=aiAgentResponse,
    description="""
    MainDashboard "🤖 AI 전체 분석" 버튼 클릭 시 호출.
    72개 ESG 지표 룰셋 평가 → 위반 감지 → AI_AGENT_ALERT INSERT → ALARM 푸시.
    """)
async def analyzeAiAgent(request: aiAgentAnalyzeModel):
    userId = getUserIdFromUuid(request.uuid)
    if not userId:
        return aiAgentResponse(status=False, message="인증 실패")

    result = await runAiAgentAnalysis(
        triggeredBy = userId,
        triggerType = request.triggerType,
        scope       = request.scope,
        scopeTarget = request.scopeTarget,
        aiModel     = request.aiModel,
    )
    return aiAgentResponse(
        status  = result["status"],
        message = result["message"],
        data    = result,
    )


# ── GET — AI 알림 목록
@router.get("/alerts",
    summary="AI Agent 알림 목록 조회",
    response_model=aiAgentResponse)
def listAiAgentAlerts(
    partnerId : Optional[str] = Query(None, description="협력사 ID 필터"),
    severity  : Optional[str] = Query(None, description="CRITICAL/FAIL/WARN/INFO"),
    status    : Optional[str] = Query("OPEN", description="OPEN/ACKNOWLEDGED/RESOLVED/IGNORED"),
    limit     : int           = Query(50, ge=1, le=200),
):
    alerts = getAiAgentAlertList(
        partnerId = partnerId,
        severity  = severity,
        status    = status,
        limit     = limit,
    )
    return aiAgentResponse(
        status  = True,
        message = "조회 성공",
        data    = {"alerts": alerts, "count": len(alerts)},
    )


# ── PATCH — 알림 확인 처리
@router.patch("/alerts/{alertId}/ack",
    summary="AI Agent 알림 확인 처리",
    response_model=aiAgentResponse)
def ackAiAgentAlert(alertId: int, request: aiAgentAckModel):
    userId = getUserIdFromUuid(request.uuid)
    if not userId:
        return aiAgentResponse(status=False, message="인증 실패")

    result = acknowledgeAiAgentAlert(alertId, userId)
    return aiAgentResponse(status=True, message="확인 처리 완료", data=result)


# ── PATCH — 알림 해소 처리
@router.patch("/alerts/{alertId}/resolve",
    summary="AI Agent 알림 해소 처리",
    response_model=aiAgentResponse)
def resolveAlertEndpoint(alertId: int, request: aiAgentResolveModel):
    userId = getUserIdFromUuid(request.uuid)
    if not userId:
        return aiAgentResponse(status=False, message="인증 실패")

    result = resolveAiAgentAlert(alertId, userId, request.resolutionNote or "")
    return aiAgentResponse(status=True, message="해소 처리 완료", data=result)


# ── GET — 실행 로그 조회
@router.get("/runs",
    summary="AI Agent 실행 로그 조회",
    response_model=aiAgentResponse)
def listAiAgentRuns(limit: int = Query(20, ge=1, le=100)):
    runs = getAiAgentRunLogList(limit=limit)
    return aiAgentResponse(
        status  = True,
        message = "조회 성공",
        data    = {"runs": runs, "count": len(runs)},
    )


# ── GET — 룰셋 조회
@router.get("/rules",
    summary="AI Agent 룰셋 조회",
    response_model=aiAgentResponse)
def listAiAgentRules(activeOnly: bool = Query(True)):
    where = "WHERE active_yn = 'Y'" if activeOnly else ""
    sql = f"""
        SELECT rule_id, indicator_no, rule_code, rule_name, tier_scope,
               metric_key, operator, threshold_value, severity,
               regulation, action_required, priority, active_yn
        FROM `AI_AGENT_RULE`
        {where}
        ORDER BY priority ASC
    """
    rules = findAll(sql, ())
    return aiAgentResponse(
        status  = True,
        message = "조회 성공",
        data    = {"rules": rules, "count": len(rules)},
    )
