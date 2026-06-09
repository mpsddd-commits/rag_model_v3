# src/apis/aiAgent.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] AI Agent HTTP API 엔드포인트 (v2.0 회사 중심 partner_id 체계 완전 동기화)
# ────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Query, Header, HTTPException
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
from src.utils.rediscl import getTokenRedis, getCompanyRedis  # Redis 세션 직접 조회를 위해 임포트

router = APIRouter()

# =====================================================================
# 🔐 [공통 헬퍼] v2.0 인증 동기화를 위한 토큰 검증 함수
# =====================================================================
# def getPartnerIdFromUuid(uuid: str) -> Optional[str]:
#     """
#     현재 프로젝트의 Redis 분리 저장 구조(db1: 토큰, db3: 회사식별)에 맞춰 
#     세션 유효성을 완벽히 검증하고 partner_id를 추출합니다.
#     """
#     if not uuid:
#         return None
        
#     # [단계 1] 우선 db1(client1)에 해당 uuid 세션 토큰이 활성화되어 있는지 유효성 검증
#     tokenCheck = getTokenRedis(uuid)
#     if not tokenCheck or not tokenCheck.get("status"):
#         print(f"❌ [AI Agent 인증 실패] db1에 해당 UUID 세션이 존재하지 않음: {uuid}")
#         return None

#     # [단계 2] 유효한 세션이라면 db3(client3)에서 이 유저가 활성화한 회사 코드(partner_id)를 조회
#     companyCheck = getCompanyRedis(uuid)
#     if not companyCheck or not companyCheck.get("status"):
#         print(f"❌ [AI Agent 인증 실패] db3에 해당 UUID와 매핑된 회사(partner_id) 정보가 없음: {uuid}")
#         return None
        
#     # getCompanyRedis의 리턴 딕셔너리 구조에서 회사 코드는 "token" 키에 담겨 있습니다.
#     partnerId = companyCheck.get("token")
    
#     print(f"✅ [AI Agent 인증 성공] 관리사/원청사 감지 성공: {partnerId}")
#     return partnerId

def getPartnerIdFromUuid(uuid: str) -> Optional[str]:
    """
    현재 프로젝트의 Redis 분리 저장 구조를 검증합니다.
    """
    # 🌟 [로컬 테스트 마스터 패스 추가]
    # Swagger에서 uuid에 아래 값을 넣으면 Redis를 타지 않고 즉시 무조건 통과시킵니다.
    if uuid == "test_master" or uuid == "9e81223c132f46a59ca3f1457081cf93":
        print("🚀 [테스트 모드] 임시 마스터 우회 통과 - partner_id: MAIN_HQ")
        return "MAIN_HQ"  # 현재 COMPANY 테이블에 등록되어 있는 실제 본사/원청사 코드 입력
        
    if not uuid:
        return None
        
    # [단계 1] db1 세션 검증
    tokenCheck = getTokenRedis(uuid)
    if not tokenCheck or not tokenCheck.get("status"):
        return None

    # [단계 2] db3 회사 식별 코드 조회
    companyCheck = getCompanyRedis(uuid)
    if not companyCheck or not companyCheck.get("status"):
        print(f"❌ [AI Agent 인증 실패] db3에 해당 UUID와 매핑된 회사(partner_id) 정보가 없음: {uuid}")
        return None
        
    return companyCheck.get("token")

# ── POST — AI 전체 분석 실행
@router.post("/analyze",
    summary="AI Agent 전체 분석 실행",
    response_model=aiAgentResponse,
    description="하이브리드 RAG 엔진을 작동시켜 가드레일 위반 탐지 및 실시간 DB 적재, 웹소켓 알람 트리거")
async def analyzeEndpoint(request: aiAgentAnalyzeModel):
    # 1. 토큰 기반 본사/원청사 partner_id 검증
    managerPartnerId = getPartnerIdFromUuid(request.uuid)
    if not managerPartnerId:
        return aiAgentResponse(status=False, message="인증 실패: 유유한 세션 토큰이 아닙니다.")

    # 2. 메인 백엔드 분석 파이프라인 엔진 가동
    # [수정] 룰셋 정의에 명시된 'triggeredBy' 위치에 인증 성공한 managerPartnerId 문자열을 함께 주입합니다.
    try:
        success = await runAiAgentAnalysis(
            managerPartnerId,        # 🏢 triggeredBy 파라미터 요구사항 매핑 완료!
            request.triggerType,
            request.scope,
            request.scopeTarget,
            request.aiModel
        )
    except TypeError:
        # 혹시 키워드 인자(명시적 매핑)를 완벽하게 선호하는 선언 방식일 경우를 대비한 가드레일 백업
        success = await runAiAgentAnalysis(
            triggeredBy=managerPartnerId,
            triggerType=request.triggerType,
            scope=request.scope,
            scopeTarget=request.scopeTarget,
            aiModel=request.aiModel
        )

    if not success:
        return aiAgentResponse(status=False, message="AI 분석 엔진 가동 중 오류가 발생했습니다.")
        
    return aiAgentResponse(status=True, message="AI Agent 공급망 분석 및 실시간 경고 전송이 성공적으로 완료되었습니다.")


# ── GET — AI 알림 목록 조회
@router.get("/alerts",
    summary="AI Agent 위반 알림 목록 조회",
    response_model=aiAgentResponse)
def listAlertsEndpoint(
    partnerId: Optional[str] = Query(None, description="특정 협력사 코드 필터"),
    severity: Optional[str] = Query(None, description="위험 심각도 필터 (CRITICAL/HIGH/MEDIUM/LOW)"),
    status: Optional[str] = Query("OPEN", description="알림 상태 필터 (OPEN/ACKNOWLEDGED/RESOLVED)"),
    limit: int = Query(50, ge=1, le=100)
):
    alerts = getAiAgentAlertList(partnerId=partnerId, severity=severity, status=status, limit=limit)
    return aiAgentResponse(
        status=True,
        message="알림 목록 조회 성공",
        data={"alerts": alerts, "count": len(alerts)}
    )


# ── PATCH — 알림 확인 처리 (ACK)
@router.patch("/alerts/{alertId}/ack",
    summary="AI Agent 알림 확인 처리",
    response_model=aiAgentResponse)
def ackAlertEndpoint(alertId: int, request: aiAgentAckModel):
    # 기존 유저 ID 대신 partner_id 검증으로 전면 교체
    managerPartnerId = getPartnerIdFromUuid(request.uuid)
    if not managerPartnerId:
        return aiAgentResponse(status=False, message="인증 실패")

    # 수정한 비즈니스 로직 함수 인터페이스 매핑 (managerPartnerId 문자열 주입)
    result = acknowledgeAiAgentAlert(alertId, managerPartnerId)
    return aiAgentResponse(status=True, message="알림 확인(ACK) 처리가 완료되었습니다.", data=result)


# ── PATCH — 알림 해소 처리 (RESOLVE)
@router.patch("/alerts/{alertId}/resolve",
    summary="AI Agent 알림 해소 처리",
    response_model=aiAgentResponse)
def resolveAlertEndpoint(alertId: int, request: aiAgentResolveModel):
    # 기존 유저 ID 대신 partner_id 검증으로 전면 교체
    managerPartnerId = getPartnerIdFromUuid(request.uuid)
    if not managerPartnerId:
        return aiAgentResponse(status=False, message="인증 실패")

    # 수정한 비즈니스 로직 함수 인터페이스 매핑 (managerPartnerId 문자열 주입)
    result = resolveAiAgentAlert(alertId, managerPartnerId, request.resolutionNote or "")
    return aiAgentResponse(status=True, message="감사관 최종 리스크 해소(RESOLVED) 처리가 완료되었습니다.", data=result)


# ── GET — 실행 로그 조회
@router.get("/runs",
    summary="AI Agent 실행 로그 조회",
    response_model=aiAgentResponse)
def listAiAgentRuns(limit: int = Query(20, ge=1, le=100)) -> aiAgentResponse:
    runs = getAiAgentRunLogList(limit=limit)
    return aiAgentResponse(
        status=True,
        message="조회 성공",
        data={"runs": runs, "count": len(runs)},
    )


# ── GET — 룰셋 조회
@router.get("/rules",
    summary="AI Agent 룰셋 조회",
    response_model=aiAgentResponse)
def listAiAgentRules(activeOnly: bool = Query(True)):
    where = "WHERE active_yn = 'Y'" if activeOnly else ""
    sql = f"""
        SELECT rule_id, indicator_no, rule_code, rule_name, tier_scope,
               metric_key, operator, threshold_value, severity, regulation
        FROM `AI_AGENT_RULE_REGISTRY` {where}
        ORDER BY indicator_no ASC
    """
    rules = findAll(sql)
    return aiAgentResponse(
        status=True,
        message="룰셋 마스터 정보 조회 성공",
        data={"rules": rules, "count": len(rules)}
    )