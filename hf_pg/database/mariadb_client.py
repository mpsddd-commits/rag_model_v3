import mariadb
from config.settings import settings
from utils.helpers import safe_print

def get_conn():
    """Establishes a connection to the MariaDB instance using settings."""
    conn_params = {
        "user": settings.maria_db_user,
        "password": settings.maria_db_password,
        "host": settings.maria_db_host,
        "database": settings.maria_db_database,
        "port": settings.maria_db_port
    }
    try:
        conn = mariadb.connect(**conn_params)
        return conn
    except mariadb.Error as e:
        safe_print(f"[MariaDB 접속 오류] : {e}")
        return None

def find_one(sql: str, params=None):
    """Retrieves a single row from the database."""
    result = None
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                result = cur.fetchone()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (findOne) : {e}")
    return result

def find_all(sql: str, params=None):
    """Retrieves multiple rows from the database."""
    result = []
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                result = cur.fetchall()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (findAll) : {e}")
    return result

def save(sql: str, params=None):
    """Saves a single record into the database."""
    result = False
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                conn.commit()
                result = True
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (save) : {e}")
    return result

def save_many(sql: str, params=None):
    """Saves multiple records in a single batch into the database."""
    result = False
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                cur.executemany(sql, params)
                conn.commit()
                result = True
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (saveMany) : {e}")
    return result

def add_key(sql: str, params=None):
    """Saves a record and retrieves the last inserted ID in a transaction."""
    result = [False, 0]
    conn = get_conn()
    if not conn:
        return result
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                sql2 = "SELECT LAST_INSERT_ID() as id"
                cur.execute(sql2)
                data = cur.fetchone()  
                conn.commit()
                result[0] = True
                if data:
                    result[1] = data["id"]
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (addKey) : {e}")
    return result

def exists(sql: str, params=None):
    """Checks the existence of records in the database matching a query."""
    result = False
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                row = cur.fetchone()
                count = list(row.values())[0] if row else 0
                result = True if count > 0 else False
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (exists) : {e}")
    return result

def get_page_list(sql: str, params=None):
    """Retrieves paginated search results along with total count."""
    result = {"total": 0, "list": []}
    conn = get_conn()
    if not conn:
        return result
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                # 1. Total row count for pagination calculations
                count_sql = f"SELECT COUNT(*) as cnt FROM ({sql}) as temp"
                cur.execute(count_sql)
                result["total"] = cur.fetchone()["cnt"]
                # 2. Slice query based on limit & offset params
                paging_sql = sql + " LIMIT ? OFFSET ?"
                cur.execute(paging_sql, params)
                result["list"] = cur.fetchall()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (getPageList) : {e}")
    return result

def sign_up_transaction(user_sql, user_params, company_sql, company_params, user_role_sql, user_role_params, industry_detail_sql, industry_detail_params):
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
    conn = get_conn()
    if not conn:
        return result
    try:
        with conn as c:
            c.autocommit = False  # Enable transaction control
            with c.cursor(dictionary=True) as cur:
                # ── Step 1. USER INSERT → user_id
                cur.execute(user_sql, user_params)
                cur.execute("SELECT LAST_INSERT_ID() as id")
                user_id = cur.fetchone()["id"]

                # ── Step 2. COMPANY INSERT → company_id
                cur.execute(company_sql, (*company_params, user_id))
                cur.execute("SELECT LAST_INSERT_ID() as id")
                company_id = cur.fetchone()["id"]

                # ── Step 3. USER_ROLE INSERT
                cur.execute(user_role_sql, (user_id, company_id, *user_role_params))

                # ── Step 4. INDUSTRY_DETAIL Array Batch INSERT
                final_industry_params = [
                    (industry_id, company_id)
                    for industry_id in industry_detail_params
                ]
                cur.executemany(industry_detail_sql, final_industry_params)

                # ── Commit transaction if all succeeded
                conn.commit()
                result[0] = True
                result[1] = {"user_id": user_id, "company_id": company_id}
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (signUpTransaction) : {e}")
    return result

def execute_transaction(queries: list):
    """
    Executes multiple SQL statements in a single transaction (All or Nothing).
    queries: List of (sql, params) tuples.
    """
    result = False
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c:
            with c.cursor(dictionary=True) as cur:
                for sql, params in queries:
                    cur.execute(sql, params)
                conn.commit()
                result = True
    except mariadb.Error as e:
        safe_print(f"MariaDB Transaction Error : {e}")
        conn.rollback()
        result = False
    return result
