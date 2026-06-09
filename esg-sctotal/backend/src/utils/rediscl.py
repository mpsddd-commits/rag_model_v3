from src.utils.settings import settings
import redis

# --------------------------
# redis client로 설정
# client1 : accesstoken
# client2 : 임시비밀번호
# client3 : 회사 선택
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
# setTokenRedis: Token Redis(client1)에 값을 저장하는 함수
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
# getTokenRedis: Token Redis(client1)에서 저장된 값을 가져오는 함수
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
# delTokenRedis: Token Redis(client1)에 저장된 값을 삭제하는 함수
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
# setPasswordRedis: Password Redis(client2)에 값을 저장하는 함수
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
# setCompanyRedis: Company Redis(client3)에 값을 저장하는 함수
# --------------------------
def setCompanyRedis(uuid: str, companyId: int):
    """Redis에 uuid를 키로, 선택한 회사 저장"""
    try:
        client3.set(uuid, companyId)
        return {"status": True}
    except Exception as e:
        print(f"Error setting Redis keys: {e}")
        return {"status": False}

# --------------------------
# getCompanyRedis: Company Redis(client3)에서 저장된 값을 가져오는 함수
# --------------------------
def getCompanyRedis(uuid: str):
    """ uuid로 회사 조회"""
    try:
        result = client3.get(uuid)
        if result:
            return {"status": True, "uuid": uuid, "token": result}
        return {"status": False, "message": "Key not found"}
    except Exception as e:
        print(f"Error getting Redis value: {e}")
        return {"status": False}

# --------------------------
# delCompanyRedis: Company Redis(client3)에 저장된 값을 삭제하는 함수
# --------------------------
def delCompanyRedis(uuid: str):
    """특정 uuid 키 삭제"""
    try:
        client3.delete(uuid)
        return {"status": True}
    except Exception as e:
        print(f"Error deleting Redis key: {e}")
        return {"status": False}
