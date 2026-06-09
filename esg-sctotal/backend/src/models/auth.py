# src/models/auth.py
# ────────────────────────────────────────────────────────
# [v1.1] 2026-06-04 — UserModel→dict 수정 (JSON 직렬화 오류 해결)
# [v1.0] 2026-06-04 — 원청사/N차 협력사 로그인, 2차 인증(Kafka/Redis), JWT 토큰 관리
# ────────────────────────────────────────────────────────

from fastapi import Response, Request
from src.utils.db import findOne, save
from src.utils.tokenset import createUserTokens
from src.utils.rediscl import setTokenRedis, client2
from src.utils.kafkasv import sendToKafka
from src.utils.settings import settings
from src.models.model import responseModel
import random
import uuid


# --------------------------
# 로그인 로직 처리 함수 (원청사/협력사 공통 진입점)
# --------------------------
def loginProcess(response: Response, request: Request, loginModel):
    """
    [원청사] email → COMPANY 테이블 매칭 → 토큰 발급
    [협력사] email + authCode → Redis 코드 검증 → COMPANY 테이블 매칭 → 토큰 발급
    """
    try:
        email = loginModel.email
        loginType = loginModel.loginType  # "oem" | "supplier"
        
        # ── N차 협력사: 2차 인증 코드 검증 ──
        if loginType == "supplier":
            authCode = loginModel.authCode
            if not authCode:
                return responseModel(False, "인증 코드를 입력해 주세요.")

            # Redis에서 인증 코드 조회
            storedCode = client2.get(f"auth_code:{email}")
            if not storedCode:
                return responseModel(False, "인증 코드가 만료되었습니다. 다시 발송해 주세요.")
            if storedCode != authCode:
                return responseModel(False, "인증코드가 맞지 않습니다.")

            # 검증 성공 시 Redis에서 코드 삭제 (일회성)
            client2.delete(f"auth_code:{email}")

        # ── 공통: COMPANY 테이블에서 이메일 매칭 ──
        companySql = """
            SELECT partner_id, company_name, ceo_name, tier, tier_label,
                   email, country, size, status
            FROM `COMPANY`
            WHERE email = ? AND delete_yn = 0
        """
        company = findOne(companySql, (email,))
        if not company:
            return responseModel(False, "등록되지 않은 이메일이거나 비활성 기업입니다.")

        # ── 공통: 토큰 생성 (partner_id를 식별 ID로 사용) ──
        # [v1.1] dict로 전달 — Pydantic BaseModel은 JSON 직렬화 불가
        user = {
            "uuid": "",
            "id": company["partner_id"],
            "name": company["company_name"],
            "email": email,
            "role": company["tier_label"] or str(company["tier"]),
            "role_name": company["tier_label"] or "협력사",
        }

        accessToken, refreshToken, tokenUuid = createUserTokens(user)

        # ── refresh token DB 저장 (TOKEN 테이블) ──
        refreshTokenSql = """
            INSERT INTO `TOKEN` (`partner_id`, `refresh_token`, `uuid`)
            VALUES (?, ?, ?)
        """
        save(refreshTokenSql, (company["partner_id"], refreshToken, tokenUuid))

        # ── accessToken Redis 저장 ──
        setTokenRedis(tokenUuid, accessToken)

        # ── Cookie 설정 ──
        maxAge = 60 * 60 * 24 * settings.refresh_token_expire_days
        cookieDomain = _getDomain(request)
        response.set_cookie(
            key=settings.cookie_key,
            value=tokenUuid,
            domain=cookieDomain,
            httponly=True,
            samesite="lax",
            max_age=maxAge,
        )

        return responseModel(True, "로그인에 성공했습니다.", {
            "partner_id": company["partner_id"],
            "company_name": company["company_name"],
            "tier": company["tier"],
            "tier_label": company["tier_label"],
            "tokenUuid": tokenUuid,
        })

    except Exception as e:
        return responseModel(False, f"로그인 처리 중 오류가 발생했습니다: {str(e)}")


# --------------------------
# 2차 인증 코드 발송 함수 (N차 협력사 전용)
# --------------------------
def sendAuthCodeProcess(authCodeModel):
    """
    1. COMPANY 테이블에서 이메일 존재 여부 확인
    2. 6자리 난수 인증 코드 생성
    3. Redis에 저장 (TTL 5분)
    4. Kafka를 통해 이메일 발송
    """
    try:
        email = authCodeModel.email

        # 1. COMPANY 테이블에서 이메일 확인
        checkSql = """
            SELECT partner_id, company_name
            FROM `COMPANY`
            WHERE email = ? AND delete_yn = 0
        """
        company = findOne(checkSql, (email,))
        if not company:
            return responseModel(False, "등록되지 않은 이메일입니다.")

        # 2. 6자리 난수 인증 코드 생성
        code = str(random.randint(100000, 999999))

        # 3. Redis에 저장 (TTL 300초 = 5분)
        client2.setex(f"auth_code:{email}", 300, code)

        # 4. Kafka를 통해 이메일 발송
        kafkaData = {
            "type": 5,
            "email": email,
            "authCode": code,
            "companyName": company["company_name"],
        }
        sendToKafka(kafkaData)

        return responseModel(True, "인증 코드가 이메일로 발송되었습니다.")

    except Exception as e:
        return responseModel(False, f"인증 코드 발송 중 오류가 발생했습니다: {str(e)}")


# --------------------------
# 내부 헬퍼: 쿠키 도메인 추출
# --------------------------
def _getDomain(request: Request):
    """요청 도메인에서 쿠키 도메인 결정"""
    hostname = request.url.hostname
    if hostname and hostname.endswith(settings.domain):
        return f".{settings.domain}"
    return None


# --------------------------
# 로그아웃 처리 함수 (Redis + Cookie 초기화)
# --------------------------
def logoutProcess(response: Response, request: Request):
    """Redis 토큰 삭제 + Cookie 삭제"""
    try:
        # Cookie에서 tokenUuid 추출
        tokenUuid = request.cookies.get(settings.cookie_key, "")
        if tokenUuid:
            # Redis에서 토큰 삭제
            from src.utils.rediscl import client1
            client1.delete(tokenUuid)
            # TOKEN 테이블에서 논리 삭제
            save("UPDATE `TOKEN` SET delete_yn = 1 WHERE uuid = ? AND delete_yn = 0", (tokenUuid,))

        # Cookie 삭제
        cookieDomain = _getDomain(request)
        response.delete_cookie(
            key=settings.cookie_key,
            domain=cookieDomain,
            path="/",
        )
        return responseModel(True, "로그아웃 되었습니다.")
    except Exception as e:
        return responseModel(False, f"로그아웃 처리 중 오류: {str(e)}")