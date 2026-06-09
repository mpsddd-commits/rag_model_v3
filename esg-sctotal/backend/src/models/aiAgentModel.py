# src/models/aiAgentModel.py
# ────────────────────────────────────────────────────────────────────────────
# [역할] AI Agent 알람 API Pydantic 모델 정의
# ────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import Optional


class aiAgentAnalyzeModel(BaseModel):
    """AI 전체 분석 실행 요청 모델"""
    uuid        : str           = Field(..., description="Redis uuid (인증)")
    triggerType : str           = Field("MANUAL", description="MANUAL/SCHEDULED/EVENT_DRIVEN")
    scope       : str           = Field("ALL", description="ALL/PARTNER/TIER/SINGLE_RULE")
    scopeTarget : Optional[str] = Field(None, description="partner_id 또는 tier_label")
    aiModel     : str           = Field("gemma4:e2b", description="gemma4:e2b")


class aiAgentAckModel(BaseModel):
    """알림 확인 처리 요청 모델"""
    uuid : str = Field(..., description="Redis uuid")


class aiAgentResolveModel(BaseModel):
    """알림 해소 처리 요청 모델"""
    uuid           : str           = Field(..., description="Redis uuid")
    resolutionNote : Optional[str] = Field(None, description="해소 비고")


class aiAgentResponse(BaseModel):
    """AI Agent API 공통 응답 모델"""
    status  : bool
    message : str
    data    : Optional[dict] = None
