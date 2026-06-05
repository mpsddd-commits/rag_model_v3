import json
import time
from datetime import datetime
import psycopg2
import ollama
from dbClient import getPostgresConn
from settings import settings, safePrint

def logStatus(message: str):
    """현재 시간과 함께 로그를 출력하는 헬퍼 함수"""
    currentTime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safePrint(f"[{currentTime}] {message}", flush=True)

def injectModifiedJsonlToPostgres(jsonlPath="esgOntologyTemplate.jsonl"):
    startTotalTime = time.time()
    
    logStatus("PostgreSQL 데이터베이스 연결 시도 중...")
    conn = getPostgresConn()
    if not conn:
        logStatus("[오류] DB 연결 실패")
        return

    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        createTableSql = """
            CREATE TABLE IF NOT EXISTS esg_pdf_vectors (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                embedding vector(768), 
                file_name VARCHAR(255),
                page_no INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """
        cur.execute(createTableSql)
        
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
            logStatus("esg_pdf_vectors 테이블 및 page_no 컬럼 검사 완료.")
        except Exception as alterErr:
            conn.rollback()
            logStatus(f"[경고] 컬럼 확인 중 예외 발생(무시 가능): {alterErr}")

        # 기존 온톨로지 삭제
        logStatus(f"기존 벡터 DB 내 '{jsonlPath}' 데이터 클리닝 시작...")
        cur.execute("DELETE FROM esg_pdf_vectors WHERE file_name = %s;", (jsonlPath,))
    
    conn.commit()
    logStatus("기존 온톨로지 데이터 클리닝 완료.")

    logStatus(f"Ollama 클라이언트 초기화 중 (호스트: {settings.ollama_host})")
    ollamaClient = ollama.Client(host=settings.ollama_host)
    
    # 총 라인 수 파악 (진행률 표시용)
    with open(jsonlPath, 'r', encoding='utf-8') as f:
        totalLines = sum(1 for line in f if line.strip())
    
    logStatus(f"총 {totalLines}개의 온톨로지 지표를 로드했습니다. 임베딩 및 적재를 시작합니다.")

    insertedCount = 0
    with open(jsonlPath, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): 
                continue
            
            insertedCount += 1
            lineStartTime = time.time()
            data = json.loads(line)
            
            indicatorNo = data.get("indicator_no")
            subId = data.get("sub_id", "MAIN")
            indicatorName = data.get("indicator_name")
            rawExpr = data.get("raw_expression")
            meta = data.get("meta", {})
            
            chunkContent = (
                f"[ESG 온톨로지 기준 사전]\n"
                f"지표명: {indicatorName}\n"
                f"검증 기준 내용: {rawExpr}\n"
                f"세부 규칙: 유형={meta.get('criteria_type')}, "
                f"연산자={meta.get('operator')}, "
                f"기준값={meta.get('threshold_value') or meta.get('min_value')}"
            )
            
            # 실시간 진행 로그 출력
            logStatus(f"[{insertedCount}/{totalLines}] 지표 No.{indicatorNo} ({subId}: {indicatorName}) 임베딩 생성 중...")
            
            try:
                # 대기 시간이 주로 발생하는 구간
                response = ollamaClient.embeddings(model=settings.embed_model, prompt=chunkContent)
                embedding = response['embedding']
                
                with conn.cursor() as cur:
                    sql = """
                        INSERT INTO esg_pdf_vectors (content, embedding, file_name, page_no)
                        VALUES (%s, %s, %s, %s)
                    """
                    cur.execute(sql, (chunkContent, embedding, jsonlPath, 0))
                
                # 건별 커밋으로 안정성 확보 및 대기 최소화
                conn.commit()
                lineElapsed = time.time() - lineStartTime
                logStatus(f"   -> 성공! 적재 완료 ({lineElapsed:.2f}초 소요)")
                
            except Exception as e:
                conn.rollback()
                logStatus(f"   -> ❌ [에러 발생] 지표 No.{indicatorNo} 처리 실패: {e}")
                
    conn.close()
    totalElapsed = time.time() - startTotalTime
    logStatus(f"🎉 모든 작업이 완료되었습니다! (총 소요 시간: {totalElapsed:.2f}초, 총 {insertedCount}건 적재 완료)")

if __name__ == "__main__":
    injectModifiedJsonlToPostgres()