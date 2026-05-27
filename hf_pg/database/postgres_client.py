import psycopg2
from config.settings import settings
from utils.helpers import safe_print

def get_postgres_conn(db_conn_str=None):
    """
    Connects to the PostgreSQL instance. If the database (default: 'rag3_db')
    does not exist, attempts to connect to 'postgres' and auto-create it.
    """
    if db_conn_str is None:
        db_conn_str = settings.postgres_conn_str

    try:
        conn = psycopg2.connect(db_conn_str)
        return conn
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        target_db = settings.postgres_database
        
        # Check if error is due to database not existing
        if "does not exist" in error_msg or "database" in error_msg.lower():
            safe_print(f"[경고] '{target_db}' 데이터베이스가 존재하지 않습니다. 자동 생성을 시도합니다...")
            
            # Form connection string to default 'postgres' database to create the target database
            postgres_conn_str = db_conn_str.replace(f"dbname={target_db}", "dbname=postgres")
            try:
                conn_pg = psycopg2.connect(postgres_conn_str)
                conn_pg.autocommit = True
                cur_pg = conn_pg.cursor()
                cur_pg.execute(f"CREATE DATABASE {target_db};")
                cur_pg.close()
                conn_pg.close()
                safe_print(f"[성공] '{target_db}' 데이터베이스가 성공적으로 생성되었습니다!")
                
                # Try connecting to the newly created database again
                return psycopg2.connect(db_conn_str)
            except Exception as create_err:
                safe_print(f"[오류] 데이터베이스 자동 생성 중 오류가 발생했습니다: {create_err}")
                raise e
        else:
            safe_print("\n" + "="*60)
            safe_print("[오류] PostgreSQL 데이터베이스 서버 연결 실패!")
            safe_print(f"상세 에러: {e}")
            safe_print("="*60 + "\n")
            raise e
