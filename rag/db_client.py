'''
MariaDB 및 PostgreSQL(pgvector) 데이터베이스 통합 관리 모듈
'''
"""
Integrated Database Client for MariaDB and PostgreSQL.
"""
import mariadb
import psycopg2
from settings import settings, safe_print

# ════════════════════════════════════════════════════════
# MariaDB (Excel & Rule Criteria Master)
# ════════════════════════════════════════════════════════
def get_maria_conn():
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

def find_one(sql: str, params=None) -> dict | None:
    conn = get_maria_conn()
    if not conn: return None
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchone()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (find_one) : {e}")
    return None

def find_all(sql: str, params=None) -> list:
    conn = get_maria_conn()
    if not conn: return []
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (find_all) : {e}")
    return []

def save(sql: str, params=None) -> bool:
    conn = get_maria_conn()
    if not conn: return False
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.execute(sql, params)
            conn.commit()
            return True
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (save) : {e}")
    return False

def save_many(sql: str, params=None) -> bool:
    conn = get_maria_conn()
    if not conn: return False
    try:
        with conn as c, c.cursor(dictionary=True) as cur:
            cur.executemany(sql, params)
            conn.commit()
            return True
    except mariadb.Error as e:
        safe_print(f"MariaDB Error (save_many) : {e}")
    return False


# ════════════════════════════════════════════════════════
# PostgreSQL (pgvector Storage)
# ════════════════════════════════════════════════════════
def get_postgres_conn():
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
                    # "DB가 없으면 새로 생성하는 명령어"
                    cur.execute(f"CREATE DATABASE {target_db};")
                conn_pg.close()
                return psycopg2.connect(db_conn_str)
            except Exception as create_err:
                safe_print(f"[오류] DB 자동 생성 실패: {create_err}")
                raise e
        else:
            raise e


# # Backward-compat camelCase aliases
# getConn = get_conn
# findOne = find_one
# findAll = find_all
# saveMany = save_many
# addKey = add_key
# getPageList = get_page_list
# signUpTransaction = sign_up_transaction
# executeTransaction = execute_transaction
