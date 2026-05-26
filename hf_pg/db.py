import mariadb
from settings import settings

# ------------------
# DB 연결
# ------------------

# env 관리
conn_params = {
  "user": settings.maria_db_user,
  "password": settings.maria_db_password,
  "host": settings.maria_db_host,
  "database" : settings.maria_db_database,
  "port" : int(settings.maria_db_port)
}

def getConn():
  '''DB 연결'''
  try:
    conn = mariadb.connect(**conn_params)
    if conn == None:
        return None
    return conn
  except mariadb.Error as e:
    print(f"접속 오류 : {e}")
    return None

# --------------------------
# 하나만 불러오기
# --------------------------
def findOne(sql:str, params=None):
  '''DB에서 단일 행 조회'''
  result = None
  try:
    with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            result = cur.fetchone()
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 모두 불러오기
# --------------------------
def findAll(sql:str, params=None):
  '''DB에서 여러 행 조회'''
  result = []
  try:
     with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            result = cur.fetchall()
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# DB에 저장하기
# --------------------------
def save(sql:str, params=None):
  '''DB에 단일 값 저장'''
  result = False
  try:
     with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            conn.commit()
            result = True
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 여러 값 저장하기
# --------------------------
def saveMany(sql:str, params=None):
  """DB에 여러 값 한번에 저장"""
  result = False
  try:
     with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.executemany(sql, params)
            conn.commit()
            result = True
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 직전에 넣은 키값 불러오기
# --------------------------
def addKey(sql:str, params=None):
  """DB에 직전에 생성한 키값 불러오기"""
  result = [False, 0]
  try:
    with getConn() as conn:
        with conn.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            sql2 = "SELECT LAST_INSERT_ID() as id"
            cur.execute(sql2)
            data = cur.fetchone()  
            conn.commit()
            result[0] = True
            if data:
                result[1] = data["id"]
  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 데이터 존재 여부 확인
# --------------------------
def exists(sql:str, params=None):
    '''DB에서 데이터 존재 여부 체크'''
    result = False
    try:
         with getConn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                # 결과가 0보다 크면 존재하는 것
                row = cur.fetchone()
                count = list(row.values())[0] if row else 0
                result = True if count > 0 else False
    except mariadb.Error as e:
        print(f"MariaDB Error : {e}")
    return result

# --------------------------
# 페이지네이션 목록
# --------------------------
def getPageList(sql:str, parmas=None):
    '''DB에서 페이지네이션 목록 조회'''
    result = {"total": 0, "list": []}
    try:
        with getConn() as conn:
            with conn.cursor(dictionary=True) as cur:
                # 1. 전체 개수 파악 (페이지 번호 계산용)
                count_sql = f"SELECT COUNT(*) as cnt FROM ({sql}) as temp"
                cur.execute(count_sql)
                result["total"] = cur.fetchone()["cnt"]
                # 2. 실제 페이지 데이터 조회
                paging_sql = sql + " LIMIT ? OFFSET ?"
                cur.execute(paging_sql, parmas)
                result["list"] = cur.fetchall()
    except mariadb.Error as e:
        print(f"MariaDB Error : {e}")
    return result
# limit = 보여줄 개수, offset = 건너뛸 개수

# db.py 하단에 추가
# --------------------------
# 회원가입 전용 트랜잭션
# --------------------------
def signUpTransaction(userSql, userParams, companySql, companyParams, userRoleSql, userRoleParams, industryDetailSql, industryDetailParams):
  """
    [역할] USER → COMPANY → USER_ROLE → INDUSTRY_DETAIL
          4개 테이블을 단일 트랜잭션으로 원자적 저장.
          하나라도 실패 시 전체 ROLLBACK 보장.

    [ERD FK 흐름]
      USER.id          ──→ COMPANY.user_id        (Step1 → Step2 주입)
      USER.id          ──→ USER_ROLE.user_id      (Step1 → Step3 주입)
      COMPANY.id       ──→ USER_ROLE.company_id   (Step2 → Step3 주입)
      COMPANY.id       ──→ INDUSTRY_DETAIL.company_id (Step2 → Step4 주입)
      INDUSTRY_CODE.id ──→ INDUSTRY_DETAIL.industry_id (외부에서 주입)

    반환값: [성공여부(bool), {"user_id": int, "company_id": int}]
  """
  result = [False, {}]
  try:
    with getConn() as conn:
      conn.autocommit = False  # 트랜잭션 수동 제어 시작
      with conn.cursor(dictionary=True) as cur:

        # ── Step 1. USER INSERT → user_id 획득
        cur.execute(userSql, userParams)
        cur.execute("SELECT LAST_INSERT_ID() as id")
        userId = cur.fetchone()["id"]   # USER.id (AUTO_INCREMENT)

        # ── Step 2. COMPANY INSERT → company_id 획득
        # user_id FK를 companyParams 마지막에 주입
        cur.execute(companySql, (*companyParams, userId))
        cur.execute("SELECT LAST_INSERT_ID() as id")
        companyId = cur.fetchone()["id"]  # COMPANY.id (AUTO_INCREMENT)

        # ── Step 3. USER_ROLE INSERT
        # user_id + company_id FK 앞에 주입
        cur.execute(userRoleSql, (userId, companyId, *userRoleParams))

        # ── Step 4. INDUSTRY_DETAIL 배열 일괄 INSERT
        # [(industry_id, company_id), ...] 형태로 executemany 실행
        # company_id FK → Step 2에서 획득한 companyId로 교체 주입
        finalIndustryParams = [
            (industryId, companyId)     # company_id 확정값으로 교체
            for industryId in industryDetailParams
        ]
        cur.executemany(industryDetailSql, finalIndustryParams)

        # ── 4개 테이블 전체 성공 시 커밋
        conn.commit()
        
        result[0] = True
        result[1] = {"user_id": userId, "company_id": companyId}

  except mariadb.Error as e:
    print(f"MariaDB Error : {e}")
  return result

# --------------------------
# 여러 SQL 문을 하나의 트랜잭션으로 처리
# --------------------------
def executeTransaction(queries: list):
    """
    여러 SQL 문을 하나의 트랜잭션으로 처리 (All or Nothing)
    queries: [(sql1, params1), (sql2, params2), ...] 형식의 리스트
    """
    result = False
    conn = getConn()
    if not conn:
        return False
    
    try:
        # 트랜잭션 시작 (mariadb 커넥션은 기본적으로 autocommit=False 상태가 많지만 명시적 처리)
        with conn.cursor(dictionary=True) as cur:
            for sql, params in queries:
                cur.execute(sql, params)
            
            # 모든 쿼리가 성공적으로 실행되면 커밋
            conn.commit()
            result = True
    except mariadb.Error as e:
        # 하나라도 실패하면 전체 취소
        print(f"MariaDB Transaction Error : {e}")
        conn.rollback()
        result = False
    finally:
        conn.close()
        
    return result