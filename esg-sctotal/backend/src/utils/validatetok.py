from src.utils.tokenset import decryptFromJwe, generateAccessWithUuid
from src.utils.rediscl import getTokenRedis, setTokenRedis, delTokenRedis
from src.utils.db import findAll, save
from src.models.model import responseModel

def validateToken(currentUuid: str):
    """
    UUID를 기반으로 액세스 토큰을 검증하고, 
    만료 시 리프레시 토큰을 통해 세션을 자동 갱신하는 통합 모듈
    """
    try:
        # 1. Redis에서 현재 UUID로 액세스 토큰 조회
        redisRes = getTokenRedis(currentUuid)
        if not redisRes["status"]:
            return responseModel(False, "세션이 존재하지 않습니다. 다시 로그인 해주세요.")

        accessJwe = redisRes["accessToken"]
        
        # 2. 액세스 토큰 유효성 검사 (복호화)
        payload = decryptFromJwe(accessJwe)

        # --- [CASE: 액세스 토큰 만료 시 재발급 로직] ---
        if payload is None:
            # DB에서 UUID를 통해 리프레시 토큰 조회
            # (TOKEN 테이블과 USER 테이블 조인하여 유효성 확인)
            userSql = """
                SELECT u.id, t.refresh_token 
                FROM `USER` u 
                JOIN `TOKEN` t ON u.id = t.user_id 
                WHERE t.uuid = ? AND u.delete_yn = 0 AND t.delete_yn = 0
                ORDER BY t.id DESC
            """
            userRecord = findAll(userSql, (currentUuid,))
            
            if len(userRecord) == 0 :
                return responseModel(False, "로그인 정보가 만료되었습니다.")
            
            refreshPayload = decryptFromJwe(userRecord[0]['refresh_token'])
            if not refreshPayload:
                return responseModel(False, "장기 세션이 만료되어 다시 로그인이 필요합니다.")

            # 새로운 액세스 토큰 및 UUID 생성
            userId = refreshPayload.get("sub")
            newAccessToken, newUuid = generateAccessWithUuid(userId)

            # DB 업데이트: TOKEN 테이블의 uuid 수정
            updateSql = "UPDATE `TOKEN` SET uuid = ?, updated_at = now() WHERE user_id = ? and uuid = ? ORDER BY created_at DESC LIMIT 1"
            save(updateSql, (newUuid, userId, currentUuid))

            # Redis 업데이트: 구 UUID 삭제 후 신규 등록
            delTokenRedis(currentUuid)
            setTokenRedis(newUuid, newAccessToken)

            return responseModel(True, "액세스 토큰이 성공적으로 갱신되었습니다.",{"uuid": newUuid})

        # --- [CASE: 액세스 토큰이 아직 유효함] ---
        return responseModel(True, "액세스 토큰이 유효합니다.",{"uuid": currentUuid})

    except Exception as e:
        print(f"Auth Module Error: {e}")
        return responseModel(False, "오류 발생")
    
