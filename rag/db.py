"""
Database clients for MariaDB and PostgreSQL.
"""
import mariadb
import psycopg2
from settings import settings, safe_print


# ════════════════════════════════════════════════════════
# MariaDB
# ════════════════════════════════════════════════════════
def get_conn():
    """Establishes a connection to the MariaDB instance."""
    try:
        return mariadb.connect(
            user=settings.maria_db_user,
            password=settings.maria_db_password,
            host=settings.maria_db_host,
            database=settings.maria_db_database,
            port=settings.maria_db_port,
        )
    except mariadb.Error as e:
        safe_print(f"[MariaDB 접속 오류] : {e}")
        return None


def find_one(sql: str, params=None):
    """Retrieves a single row as a dict."""
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (find_one) : {e}")
    return None


def find_all(sql: str, params=None) -> list:
    """Retrieves all matching rows as a list of dicts."""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (find_all) : {e}")
    return []


def save(sql: str, params=None) -> bool:
    """Executes a single INSERT/UPDATE/DELETE and commits."""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            conn.commit()
            return True
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (save) : {e}")
    return False


def save_many(sql: str, params=None) -> bool:
    """Batch-inserts multiple records and commits."""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.executemany(sql, params)
            conn.commit()
            return True
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (save_many) : {e}")
    return False


def add_key(sql: str, params=None) -> list:
    """Inserts a record and returns [success, last_insert_id]."""
    result = [False, 0]
    conn = get_conn()
    if not conn:
        return result
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            cur.execute("SELECT LAST_INSERT_ID() as id")
            data = cur.fetchone()
            conn.commit()
            result[0] = True
            if data:
                result[1] = data["id"]
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (add_key) : {e}")
    return result


def exists(sql: str, params=None) -> bool:
    """Returns True if the COUNT(*) query yields > 0."""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return bool(list(row.values())[0]) if row else False
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (exists) : {e}")
    return False


def get_page_list(sql: str, params=None) -> dict:
    """Returns paginated results with total count: {total, list}."""
    result = {"total": 0, "list": []}
    conn = get_conn()
    if not conn:
        return result
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(f"SELECT COUNT(*) as cnt FROM ({sql}) as temp")
            result["total"] = cur.fetchone()["cnt"]
            cur.execute(sql + " LIMIT ? OFFSET ?", params)
            result["list"] = cur.fetchall()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (get_page_list) : {e}")
    return result


def sign_up_transaction(
    user_sql, user_params,
    company_sql, company_params,
    user_role_sql, user_role_params,
    industry_detail_sql, industry_detail_params,
) -> list:
    """
    Atomically inserts USER → COMPANY → USER_ROLE → INDUSTRY_DETAIL.
    Returns [success, {"user_id": int, "company_id": int}].
    """
    result = [False, {}]
    conn = get_conn()
    if not conn:
        return result
    try:
        with conn as c:
            c.autocommit = False
            with c.cursor(dictionary=True) as cur:
                cur.execute(user_sql, user_params)
                cur.execute("SELECT LAST_INSERT_ID() as id")
                user_id = cur.fetchone()["id"]

                cur.execute(company_sql, (*company_params, user_id))
                cur.execute("SELECT LAST_INSERT_ID() as id")
                company_id = cur.fetchone()["id"]

                cur.execute(user_role_sql, (user_id, company_id, *user_role_params))
                cur.executemany(
                    industry_detail_sql,
                    [(iid, company_id) for iid in industry_detail_params],
                )
                conn.commit()
                result = [True, {"user_id": user_id, "company_id": company_id}]
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (sign_up_transaction) : {e}")
    return result


def execute_transaction(queries: list) -> bool:
    """Runs multiple (sql, params) pairs in one atomic transaction."""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            for sql, params in queries:
                cur.execute(sql, params)
            conn.commit()
            return True
    except mariadb.Error as e:
        safe_print(f"MariaDB Transaction Error : {e}")
        conn.rollback()
    return False


# Backward-compat camelCase aliases
getConn = get_conn
findOne = find_one
findAll = find_all
saveMany = save_many
addKey = add_key
getPageList = get_page_list
signUpTransaction = sign_up_transaction
executeTransaction = execute_transaction


# ════════════════════════════════════════════════════════
# PostgreSQL
# ════════════════════════════════════════════════════════
def get_postgres_conn(db_conn_str: str | None = None):
    """
    Connects to PostgreSQL. Auto-creates the target database if it does not exist.
    """
    if db_conn_str is None:
        db_conn_str = settings.postgres_conn_str

    try:
        return psycopg2.connect(db_conn_str)
    except psycopg2.OperationalError as e:
        target_db = settings.postgres_database
        if "does not exist" in str(e) or "database" in str(e).lower():
            safe_print(f"[경고] '{target_db}' DB 없음. 자동 생성 시도...")
            fallback = db_conn_str.replace(f"dbname={target_db}", "dbname=postgres")
            try:
                conn_pg = psycopg2.connect(fallback)
                conn_pg.autocommit = True
                with conn_pg.cursor() as cur:
                    cur.execute(f"CREATE DATABASE {target_db};")
                conn_pg.close()
                safe_print(f"[성공] '{target_db}' DB 생성 완료!")
                return psycopg2.connect(db_conn_str)
            except Exception as create_err:
                safe_print(f"[오류] DB 자동 생성 실패: {create_err}")
                raise e
        else:
            safe_print(f"[오류] PostgreSQL 연결 실패: {e}")
            raise e
