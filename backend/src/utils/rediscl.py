from src.utils.settings import settings
import redis
from datetime import datetime, timedelta, timezone

# --------------------------
# redis client로 설정
# client1 : accesstoken
# client2 : 임시비밀번호
# client3 : 초대 링크
# --------------------------
client1 = redis.Redis(
  host=settings.redis_host,
  port=settings.redis_port,
  db=settings.redis_db1,
  decode_responses=True
)
client2 = redis.Redis(
  host=settings.redis_host,
  port=settings.redis_port,
  db=settings.redis_db2,
  decode_responses=True
)
client3 = redis.Redis(
  host=settings.redis_host,
  port=settings.redis_port,
  db=settings.redis_db3,
  decode_responses=True
)

# --------------------------
# setRedis: Token Redis(client1)에 값을 저장하는 함수
# --------------------------
def setTokenRedis(uuid: str, token: str):
    """Redis에 uuid를 키로, accessToken을 값으로 저장"""
    try:
        # set(key, value)
        client1.set(uuid, token)
        print(f"Success: Set Redis - uuid: {uuid}")
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}

# --------------------------
# getRedis: Token Redis(client1)에서 저장된 값을 가져오는 함수
# --------------------------
def getTokenRedis(uuid: str):
    """uuid로 accessToken 조회"""
    try:
        result = client1.get(uuid)
        if result:
            return {"status": True, "uuid": uuid, "accessToken": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}

# --------------------------
# delRedis: Token Redis(client1)에 저장된 값을 삭제하는 함수
# --------------------------
def delTokenRedis(uuid: str):
    """특정 uuid 키 삭제"""
    try:
        client1.delete(uuid)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}
    
# --------------------------
# setRedis: Password Redis(client2)에 값을 저장하는 함수
# --------------------------
def setPasswordRedis(tempPwd: str, email: str):
    """Redis에 tempPwd를 키로, Email을 값으로 저장"""
    try:
        # set(key, value)
        client2.set(tempPwd, email)
        print(f"Success: Set Redis - tempPwd: {tempPwd}")
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}

# --------------------------
# getPasswordRedis: Password Redis(client2)에서 저장된 값을 가져오는 함수
# --------------------------
def getPasswordRedis(tempPwd: str):
    """tempPwd로 Email 조회"""
    try:
        result = client2.get(tempPwd)
        if result:
            return {"status": True, "tempPwd": tempPwd, "email": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}

# --------------------------
# delPasswordRedis: Password Redis(client2)에 저장된 값을 삭제하는 함수
# --------------------------
def delPasswordRedis(tempPwd: str):
    """특정 tempPwd 키 삭제"""
    try:
        client2.delete(tempPwd)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}
    
# --------------------------
# setRedis: invite Redis(client3)에 값을 저장하는 함수
# --------------------------
def setInviteRedis(uuid: str, token: str):
    """Redis에 uuid를 키로, token 값을 저장"""
    try:
        client3.set(uuid, token)
        print(f"Success: Set Redis - uuid: {uuid}")
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}

# --------------------------
# getInviteRedis: invite Redis(client3)에서 저장된 값을 가져오는 함수
# --------------------------
def getInviteRedis(uuid: str):
    """ uuid로 간편 회원가입 정보 담은 Token 조회"""
    try:
        result = client3.get(uuid)
        if result:
            return {"status": True, "uuid": uuid, "token": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}

# --------------------------
# delInviteRedis: invite Redis(client3)에 저장된 값을 삭제하는 함수
# --------------------------
def delInviteRedis(uuid: str):
    """특정 uuid 키 삭제"""
    try:
        client3.delete(uuid)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}
    

