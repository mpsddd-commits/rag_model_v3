# load_modified_ontology.py (로그 가시성 개선 버전)
import json
import time
from datetime import datetime
import psycopg2
import ollama
from db_client import get_postgres_conn
from settings import settings

def log_status(message: str):
    """현재 시간과 함께 로그를 출력하는 헬퍼 함수"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {message}", flush=True)

def inject_modified_jsonl_to_postgres(jsonl_path="esg_ontology_template.jsonl"):
    start_total_time = time.time()
    
    log_status("PostgreSQL 데이터베이스 연결 시도 중...")
    conn = get_postgres_conn()
    if not conn:
        log_status("[오류] DB 연결 실패")
        return

    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS esg_pdf_vectors (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector(768), 
                file_name VARCHAR(255),
                page_no INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        cur.execute(create_table_sql)
        
        try:
            cur.execute("""
                DO $$ 
                BEGIN 
                    BEGIN
                        ALTER TABLE esg_pdf_vectors ADD COLUMN page_no INT DEFAULT 0;
                    EXCEPTION
                        WHEN duplicate_column THEN RAISE NOTICE 'column page_no already exists in esg_pdf_vectors.';
                    END;
                END $$;
            """)
            conn.commit()
            log_status("esg_pdf_vectors 테이블 및 page_no 컬럼 검사 완료.")
        except Exception as alter_err:
            conn.rollback()
            log_status(f"[경고] 컬럼 확인 중 예외 발생(무시 가능): {alter_err}")

        # 기존 온톨로지 삭제
        log_status(f"기존 벡터 DB 내 '{jsonl_path}' 데이터 클리닝 시작...")
        cur.execute("DELETE FROM esg_pdf_vectors WHERE file_name = %s;", (jsonl_path,))
    
    conn.commit()
    log_status("기존 온톨로지 데이터 클리닝 완료.")

    log_status(f"Ollama 클라이언트 초기화 중 (호스트: {settings.ollama_host})")
    ollama_client = ollama.Client(host=settings.ollama_host)
    
    # 총 라인 수 파악 (진행률 표시용)
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        total_lines = sum(1 for line in f if line.strip())
    
    log_status(f"총 {total_lines}개의 온톨로지 지표를 로드했습니다. 임베딩 및 적재를 시작합니다.")

    inserted_count = 0
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): 
                continue
            
            inserted_count += 1
            line_start_time = time.time()
            data = json.loads(line)
            
            indicator_no = data.get("indicator_no")
            sub_id = data.get("sub_id", "MAIN")
            indicator_name = data.get("indicator_name")
            raw_expr = data.get("raw_expression")
            meta = data.get("meta", {})
            
            chunk_content = (
                f"[ESG 온톨로지 기준 사전]\n"
                f"지표명: {indicator_name}\n"
                f"검증 기준 내용: {raw_expr}\n"
                f"세부 규칙: 유형={meta.get('criteria_type')}, "
                f"연산자={meta.get('operator')}, "
                f"기준값={meta.get('threshold_value') or meta.get('min_value')}"
            )
            
            # 실시간 진행 로그 출력
            log_status(f"[{inserted_count}/{total_lines}] 지표 No.{indicator_no} ({sub_id}: {indicator_name}) 임베딩 생성 중...")
            
            try:
                # 대기 시간이 주로 발생하는 구간
                response = ollama_client.embeddings(model=settings.embed_model, prompt=chunk_content)
                embedding = response['embedding']
                
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO esg_pdf_vectors (content, embedding, file_name, page_no)
                        VALUES (%s, %s, %s, %s)
                    """
                    cur.execute(sql, (chunk_content, embedding, jsonl_path, 0))
                
                # 건별 커밋으로 안정성 확보 및 대기 최소화
                conn.commit()
                line_elapsed = time.time() - line_start_time
                log_status(f"   -> 성공! 적재 완료 ({line_elapsed:.2f}초 소요)")
                
            except Exception as e:
                conn.rollback()
                log_status(f"   -> ❌ [에러 발생] 지표 No.{indicator_no} 처리 실패: {e}")
                
    conn.close()
    total_elapsed = time.time() - start_total_time
    log_status(f"🎉 모든 작업이 완료되었습니다! (총 소요 시간: {total_elapsed:.2f}초, 총 {inserted_count}건 적재 완료)")

if __name__ == "__main__":
    inject_modified_jsonl_to_postgres()