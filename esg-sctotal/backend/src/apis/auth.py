# src/apis/auth.py
# ────────────────────────────────────────────────────────
# [v1.0] 2026-06-04 — 원청사/N차 협력사 로그인 분기, 2차 인증 코드 발송
# ────────────────────────────────────────────────────────

from fastapi import APIRouter, Response, Request
from src.models.model import EsgLoginModel, AuthCodeModel
from src.models.auth import loginProcess, sendAuthCodeProcess, logoutProcess

router = APIRouter()


# --------------------------
# 로그인 API (원청사 / N차 협력사 공통)
# --------------------------
@router.post("/login",
    summary="로그인 API",
    description="원청사: 이메일 매칭 로그인 / 협력사: 2차 인증 코드 검증 후 로그인")
def login(response: Response, request: Request, loginModel: EsgLoginModel):
    return loginProcess(response, request, loginModel)


# --------------------------
# 2차 인증 코드 발송 API (N차 협력사 전용)
# --------------------------
@router.post("/send-code",
    summary="인증 코드 발송 API",
    description="이메일로 6자리 인증 코드 발송 (Kafka + Redis)")
def sendCode(authCodeModel: AuthCodeModel):
    return sendAuthCodeProcess(authCodeModel)


# --------------------------
# 로그아웃 API (Redis + Cookie 초기화)
# --------------------------
@router.post("/logout",
    summary="로그아웃 API",
    description="Redis 토큰 삭제 + Cookie 초기화")
def logout(response: Response, request: Request):
    return logoutProcess(response, request)