import os
import sys
import glob
import re
import ollama
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from pypdf import PdfReader
import pandas as pd
from datasets import Dataset 
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi

# ==========================================
# 0-0. Windows 콘솔 인코딩 예외 안전장치 (Global Safe Print)
# ==========================================
def safe_print(*args, **kwargs):
    sep = kwargs.get('sep', ' ')
    end = kwargs.get('end', '\n')
    file = kwargs.get('file', sys.stdout)
    
    text = sep.join(str(arg) for arg in args)
    try:
        file.write(text + end)
        file.flush()
    except UnicodeEncodeError:
        encoding = getattr(file, 'encoding', 'utf-8') or 'utf-8'
        safe_text = text.encode(encoding, errors='replace').decode(encoding)
        file.write(safe_text + end)
        file.flush()

print = safe_print

# ==========================================
# 0. 설정 상수 및 Ollama 클라이언트 정의
# ==========================================
EMBED_MODEL = "bge-m3"
RERANK_MODEL = "BAAI/bge-reranker-large"
DB_CONN_STR = "dbname=rag3_db user=root password=1234 host=localhost port=5432"

# 리랭커 모델 로드 (처음 실행 시 자동 다운로드됩니다)
print(f"[로딩] 리랭킹 모델 '{RERANK_MODEL}' 초기화 중...")
reranker = CrossEncoder(RERANK_MODEL)

# [네트워크 세팅] 서버가 0.0.0.0 바인딩이어도 클라이언트가 명확히 찾아가도록 조치
os.environ["OLLAMA_HOST"] = "http://127.0.0.1:11434"
ollama_client = ollama.Client(host="http://127.0.0.1:11434")

# 글로벌 전역 변수로 BM25 인덱스와 청크 리스트 보관
bm25_index = None
global_chunks_pool = []

# ==========================================
# [도우미 함수] BM25용 초간단 토크나이저
# ==========================================
def simple_tokenizer(text):
    """문장 내 특수문자를 제거하고 공백 단위로 쪼개어 소문자화하는 토크나이저"""
    clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
    return clean_text.split()

def initialize_bm25(chunks_list):
    """
    구축된 모든 텍스트 청크를 기반으로 메모리에 BM25 스파스 인덱스를 생성합니다.
    """
    global bm25_index, global_chunks_pool
    global_chunks_pool = chunks_list
    
    print(f"[BM25] {len(chunks_list)}개의 청크 대상 스파스(키워드) 인덱스 구축 중...")
    # 각 청크의 본문(content)을 토큰화하여 코퍼스 리스트 구축
    tokenized_corpus = [simple_tokenizer(chunk["content"]) for chunk in chunks_list]
    bm25_index = BM25Okapi(tokenized_corpus)
    print("[성공] BM25 키워드 인덱스 생성 완료.")

# ==========================================
# 0-1. 데이터베이스 연결 및 자동 생성 도우미 함수
# ==========================================
def get_db_connection(db_conn_str):
    try:
        conn = psycopg2.connect(db_conn_str)
        return conn
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "does not exist" in error_msg or "database" in error_msg.lower():
            print("[경고] 'rag3_db' 데이터베이스가 존재하지 않습니다. 자동 생성을 시도합니다...")
            postgres_conn_str = db_conn_str.replace("dbname=rag3_db", "dbname=postgres")
            try:
                conn_pg = psycopg2.connect(postgres_conn_str)
                conn_pg.autocommit = True
                cur_pg = conn_pg.cursor()
                cur_pg.execute("CREATE DATABASE rag3_db;")
                cur_pg.close()
                conn_pg.close()
                print("[성공] 'rag3_db' 데이터베이스가 성공적으로 생성되었습니다!")
                return psycopg2.connect(db_conn_str)
            except Exception as create_err:
                print(f"[오류] 데이터베이스 자동 생성 중 오류가 발생했습니다: {create_err}")
                raise e
        else:
            print("\n" + "="*60)
            print("[오류] PostgreSQL 데이터베이스 서버 연결 실패!")
            print(f"상세 에러: {e}")
            print("="*60 + "\n")
            raise e

# ==========================================
# 0-2. Ollama 모델 관리 및 다운로드 도우미 함수
# ==========================================
def check_and_pull_ollama_model(model_name):
    print(f"[조회] Ollama 모델 '{model_name}' 로컬 설치 상태 검사 중...")
    try:
        models_list = ollama_client.list()
        downloaded_models = []
        for m in models_list.get('models', []):
            name = m.get('model', m.get('name', ''))
            downloaded_models.append(name)
            if ':' in name:
                downloaded_models.append(name.split(':')[0])
                
        exists = any(model_name == m or model_name in m or m in model_name for m in downloaded_models)
        
        if not exists:
            print(f"[다운로드] 로컬에서 '{model_name}' 모델을 찾을 수 없습니다. 자동 다운로드(pull)를 시작합니다...")
            ollama_client.pull(model_name)
            print(f"[성공] 모델 '{model_name}' 다운로드 완료!")
        else:
            print(f"[성공] 모델 '{model_name}' 확인 완료 (사용 가능)")
    except Exception as e:
        print(f"[경고] Ollama 서비스 모델 조회/다운로드 시 실패: {e}")

def get_embedding_dimension(model_name):
    check_and_pull_ollama_model(model_name)
    try:
        test_emb = get_ollama_embedding("test")
        dim = len(test_emb)
        print(f"[크기] 임베딩 모델 '{model_name}' 차원 수 감지 완료: {dim}차원")
        return dim
    except Exception as e:
        print(f"[경고] 임베딩 차원 동적 감지 실패: {e}. 기본값 1024차원으로 설정합니다.")
        return 1024

# ==========================================
# 1. 하이브리드 텍스트 분할 알고리즘 (PDF & Excel)
# ==========================================
def extract_and_chunk_pdf(pdf_path, chunk_size=600, chunk_overlap=150):
    """
    [하이브리드 시맨틱 분할]
    문장 구조를 무너뜨리지 않기 위해 마침표와 줄바꿈을 기준으로 먼저 쪼갠 뒤,
    의미적 덩어리를 유지하면서 글자 수 한도에 맞게 재귀적으로 결합하는 방식입니다.
    """
    print(f"[PDF] '{pdf_path}' 하이브리드 시맨틱 청킹 시작...")
    reader = PdfReader(pdf_path)
    chunks_with_metadata = []
    file_name = os.path.basename(pdf_path)
    
    for page_idx, page in enumerate(reader.pages):
        page_num = page_idx + 1
        text = page.extract_text()
        if not text or not text.strip():
            continue
            
        # 텍스트 노이즈 정제
        text = text.replace('\r\n', '\n').strip()
        
        # 규정 조항이나 서술형 문장 경계를 보존하기 위해 정규식으로 분할
        # 마침표, 물음표, 느낌표 뒤에 공백이나 줄바꿈이 오는 패턴을 문장 경계로 인식
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 문장 하나가 너무 긴 경우 예외 처리
            if len(sentence) > chunk_size:
                # 문장 내에서 강제 분할하되 기존 데이터 유실 방지
                if current_chunk:
                    chunks_with_metadata.append({
                        "content": current_chunk.strip(),
                        "source_file": file_name,
                        "source_type": "PDF",
                        "page_or_row": f"{page_num}페이지"
                    })
                    current_chunk = ""
                
                # 긴 문장을 sub-chunk 크기로 분할하여 강제 삽입
                sub_sentences = [sentence[i:i+chunk_size] for i in range(0, len(sentence), chunk_size - chunk_overlap)]
                for sub in sub_sentences:
                    chunks_with_metadata.append({
                        "content": sub.strip(),
                        "source_file": file_name,
                        "source_type": "PDF",
                        "page_or_row": f"{page_num}페이지"
                    })
                continue

            # 청크 결합 조건 체크
            if len(current_chunk) + len(sentence) + 1 > chunk_size:
                if current_chunk:
                    chunks_with_metadata.append({
                        "content": current_chunk.strip(),
                        "source_file": file_name,
                        "source_type": "PDF",
                        "page_or_row": f"{page_num}페이지"
                    })
                
                # Overlap 영역을 계산하여 문맥 연속성 유지
                overlap_start = max(0, len(current_chunk) - chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + " " + sentence
            else:
                current_chunk += (" " if current_chunk else "") + sentence
                
        # 페이지별 잔여 텍스트 마감
        if current_chunk.strip():
            chunks_with_metadata.append({
                "content": current_chunk.strip(),
                "source_file": file_name,
                "source_type": "PDF",
                "page_or_row": f"{page_num}페이지"
            })
            
    print(f"[성공] PDF 하이브리드 분할 완료: 총 {len(chunks_with_metadata)} 개 청크.")
    return chunks_with_metadata


def extract_and_chunk_excel(excel_path):
    """
    [하이브리드 구조적 청킹]
    표 데이터의 행(Row)을 독립된 의미 개체로 취급하며, 
    공급망 정보나 지표 데이터의 탐색력을 강화하기 위해 [키: 값] 형태의 마크다운 느낌으로 변환합니다.
    """
    print(f"[엑셀] '{excel_path}' 구조적 하이브리드 청킹 시작...")
    file_name = os.path.basename(excel_path)
    
    # 모든 컬럼을 텍스트화하여 결측치 처리 효율화
    df = pd.read_excel(excel_path, engine='openpyxl')
    df = df.fillna("")
    
    chunks_with_metadata = []
    for index, row in df.iterrows():
        row_text_list = []
        for col in df.columns:
            val = str(row[col]).strip()
            if val:
                # 컬럼 헤더와 셀 값을 일치시켜 정보 검색 매칭력 최적화
                row_text_list.append(f"[{col}]: {val}")
        
        if not row_text_list:
            continue
            
        # 의미론적 완결성을 가진 문장 형태로 조립
        chunk_text = " | ".join(row_text_list)
        full_chunk = f"설명: 해당 데이터는 {file_name}의 정보 항목입니다. 세부 내용 -> {chunk_text}"
        
        chunks_with_metadata.append({
            "content": full_chunk,
            "source_file": file_name,
            "source_type": "Excel",
            "page_or_row": f"{index + 1}번째 행"
        })
        
    print(f"[성공] 엑셀 구조화 분할 완료: 총 {len(chunks_with_metadata)} 개 레코드 추출.")
    return chunks_with_metadata

# ==========================================
# 2. Ollama 기반 임베딩 추출 함수
# ==========================================
def get_ollama_embedding(text):
    response = ollama_client.embeddings(model=EMBED_MODEL, prompt=text)
    return response['embedding']

# ==========================================
# 3. PostgreSQL(pgvector) 초기화 및 데이터 저장
# ==========================================
def init_and_save_to_pgvector(chunks_with_metadata):
    conn = get_db_connection(DB_CONN_STR)
    cur = conn.cursor()
    
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    
    dim = get_embedding_dimension(EMBED_MODEL)
    
    cur.execute("DROP TABLE IF EXISTS esg_documents;")
    cur.execute(f"""
        CREATE TABLE esg_documents (
            id SERIAL PRIMARY KEY,
            content TEXT,
            embedding vector({dim}),
            source_file TEXT,
            source_type TEXT,
            page_or_row TEXT
        );
    """)
    conn.commit()
    
    print("[시작] 하이브리드 청크 기반 임베딩 연산 및 pgvector 저장 중...")
    data_to_insert = []
    for item in chunks_with_metadata:
        vector = get_ollama_embedding(item["content"])
        data_to_insert.append((
            item["content"], 
            str(vector), 
            item["source_file"], 
            item["source_type"], 
            item["page_or_row"]
        ))
        
    execute_values(
        cur, 
        "INSERT INTO esg_documents (content, embedding, source_file, source_type, page_or_row) VALUES %s", 
        data_to_insert
    )
    conn.commit()
    
    print("[인덱스] HNSW 벡터 인덱스 생성 중...")
    cur.execute("CREATE INDEX IF NOT EXISTS esg_documents_hnsw_idx ON esg_documents USING hnsw (embedding vector_cosine_ops);")
    conn.commit()
    
    cur.close()
    conn.close()
    print("[성공] pgvector 데이터베이스 구축 완료!")

# ==========================================
# 4. pgvector 기반 코사인 유사도 검색 알고리즘
# ==========================================
def search_similar_documents(query, top_k=3, dense_n=10, sparse_n=10):
    """
    [하이브리드 2단계 검색 구조]
    Channel 1 (Dense): pgvector를 이용한 의미론적 코사인 유사도 검색 -> 10개 추출
    Channel 2 (Sparse): BM25를 이용한 키워드 텍스트 일치 검색 -> 10개 추출
    통합 및 중복제거 -> 총 후보군을 Cross-Encoder 리랭커로 재정렬 후 최종 top_k(3개) 결정
    """
    global bm25_index, global_chunks_pool
    
    candidate_dict = {}  # 중복 제거를 위한 딕셔너리 (key: content)

    # ----------------------------------------------------
    # [채널 1] pgvector 의미론적(Dense) 검색
    # ----------------------------------------------------
    query_vector = get_ollama_embedding(query)
    conn = get_db_connection(DB_CONN_STR)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT content, source_file, source_type, page_or_row 
        FROM esg_documents 
        ORDER BY embedding <=> %s 
        LIMIT %s;
    """, (str(query_vector), dense_n))
    
    dense_results = cur.fetchall()
    cur.close()
    conn.close()
    
    for row in dense_results:
        content = row[0]
        candidate_dict[content] = {
            "content": content,
            "source_file": row[1],
            "source_type": row[2],
            "page_or_row": row[3],
            "search_type": "Dense"
        }

    # ----------------------------------------------------
    # [채널 2] BM25 키워드(Sparse) 검색
    # ----------------------------------------------------
    if bm25_index is not None:
        tokenized_query = simple_tokenizer(query)
        # BM25 기반 점수가 높은 상위 'sparse_n'개 문서 추출
        sparse_top_chunks = bm25_index.get_top_n(tokenized_query, global_chunks_pool, n=sparse_n)
        
        for chunk in sparse_top_chunks:
            content = chunk["content"]
            if content in candidate_dict:
                # 이미 Dense 채널에서 뽑혔다면 시너지 표시
                candidate_dict[content]["search_type"] = "Hybrid_Both"
            else:
                candidate_dict[content] = {
                    "content": content,
                    "source_file": chunk["source_file"],
                    "source_type": chunk["source_type"],
                    "page_or_row": chunk["page_or_row"],
                    "search_type": "Sparse"
                }
                
    candidates = list(candidate_dict.values())
    print(f"[하이브리드] 1단계 후보군 총 {len(candidates)}개 획득 (중복 제거 완료).")
    
    if not candidates:
        return []

    # ----------------------------------------------------
    # [2단계] Cross-Encoder 정밀 리랭킹으로 통합순위 결정
    # ----------------------------------------------------
    print(f"[리랭킹] 통합 후보군에 대해 문맥 연관성 점수 산출 중...")
    pairs = [[query, doc["content"]] for doc in candidates]
    scores = reranker.predict(pairs)
    
    for idx, score in enumerate(scores):
        candidates[idx]["rerank_score"] = float(score)
        
    # 최종 스코어 내림차순 정렬 후 최상위 top_k 슬라이싱
    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    final_retrieved = candidates[:top_k]
    
    print(f"[성공] 하이브리드 리랭킹 탑 스코어: {final_retrieved[0]['rerank_score']:.4f} (출처 채널: {final_retrieved[0]['search_type']})")
    return final_retrieved

# ==========================================
# 5. RAG 생성 파트 (출처 명시)
# ==========================================
def ask_esg_chatbot(model_name, query):
    check_and_pull_ollama_model(model_name)
    retrieved_contexts = search_similar_documents(query, top_k=3)
    
    if not retrieved_contexts:
        return "[경고] 검색 결과가 존재하지 않아 답변을 구성할 수 없습니다.", []
    
    formatted_context_list = []
    citations = []
    
    for idx, ctx in enumerate(retrieved_contexts):
        source_info = f"{ctx['source_file']} ({ctx['page_or_row']})"
        citations.append(source_info)
        formatted_context_list.append(
            f"[참고 자료 {idx+1}] (출처: {source_info})\n내용: {ctx['content']}"
        )
        
    context = "\n\n".join(formatted_context_list)
    
    prompt = f"""당신은 ESG 공급망 실사 지침 및 글로벌 규제 전문가입니다. 
주어진 [참고 문서]의 핵심 내용을 기반으로 [사용자 질문]에 신뢰할 수 있는 정확한 정보를 제공하세요.
반드시 제공된 문서에 나와 있는 내용만을 토대로 요약 및 분석을 수행해야 합니다.
답변할 때 해당하는 내용이 어떤 참고 자료(예: [참고 자료 1], [참고 자료 2] 등)에서 온 것인지 본문 내에 명시하여 사용자가 출처를 검증할 수 있도록 하세요.

[참고 문서]
{context}

[사용자 질문]
{query}
"""
    
    print(f"\n[AI] [{model_name}] 모델이 답변을 생성하는 중...")
    try:
        response = ollama_client.generate(model=model_name, prompt=prompt)
        return response['response'], citations
    except Exception as e:
        err_msg = f"LLM 답변 생성 중 치명적인 실패가 발생했습니다: {e}"
        return err_msg, citations

# ==========================================
# 6. pgvector 백업 및 허깅페이스 저장
# ==========================================
def export_pgvector_to_file_and_hf(repo_id="Makesols/esg-vector-dataset3"):
    conn = get_db_connection(DB_CONN_STR)
    cur = conn.cursor()
    cur.execute("SELECT id, content, embedding::text, source_file, source_type, page_or_row FROM esg_documents;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        print("[경고] DB에 저장된 데이터가 없어 백업을 건너뜜.")
        return

    df = pd.DataFrame(rows, columns=['id', 'content', 'embedding', 'source_file', 'source_type', 'page_or_row'])
    df['embedding'] = df['embedding'].apply(lambda x: [float(i) for i in x.strip('[]').split(',')])

    df.to_csv("esg_vector_backup.csv", index=False, encoding='utf-8-sig')
    df.to_parquet("esg_vector_backup.parquet", index=False)
    print("[백업] 로컬 파일 백업 성공.")

    if repo_id:
        try:
            print("[HF] 허깅페이스 데이터셋 업로드 시작...")
            hf_dataset = Dataset.from_pandas(df)
            hf_dataset.push_to_hub(repo_id, private=True)
            print(f"[성공] 허깅페이스 허브 업로드 완료!")
        except Exception as e:
            print(f"[오류] 허깅페이스 업로드 중 실패 (토큰/권한 재확인 요망): {e}")


# ==========================================
# 메인 제어 흐름
# ==========================================
if __name__ == "__main__":
    all_chunks = []

    # 1. PDF 폴더 처리
    pdf_folder_path = "./esg_pdf_files"
    if not os.path.exists(pdf_folder_path):
        os.makedirs(pdf_folder_path)
    
    pdf_files = glob.glob(os.path.join(pdf_folder_path, "*.pdf"))
    if pdf_files:
        for pdf_path in pdf_files:
            try:
                pdf_chunks = extract_and_chunk_pdf(pdf_path)
                all_chunks.extend(pdf_chunks)
            except Exception as e:
                print(f"[오류] {pdf_path} 읽기 실패: {e}")

    # 2. 엑셀 폴더 처리
    excel_folder_path = "./esg_excel_files"
    if not os.path.exists(excel_folder_path):
        os.makedirs(excel_folder_path)
        
    excel_files = glob.glob(os.path.join(excel_folder_path, "*.xlsx")) + glob.glob(os.path.join(excel_folder_path, "*.xls"))
    if excel_files:
        for excel_path in excel_files:
            try:
                excel_chunks = extract_and_chunk_excel(excel_path)
                all_chunks.extend(excel_chunks)
            except Exception as e:
                print(f"[오류] {excel_path} 읽기 실패: {e}")

   # 3. pgvector 통합 저장 및 BM25 인덱스 동시 초기화
    if all_chunks:
        try:
            # 덴스용 DB 저장
            init_and_save_to_pgvector(all_chunks)
            
            # [핵심] 스파스용 BM25 인덱스 초기화
            initialize_bm25(all_chunks)
            
        except Exception as e:
            print(f"[오류] 지식 베이스(Hybrid) 구축 실패: {e}")

    # 4. RAG 질의응답 및 백업 수행
    if all_chunks:
        test_query = "협력사의 탄소 배출량 실사 의무 규정과 제재 조치는 어떻게 되나요?"
        target_model = "gemma4:e2b" 
        try:
            gemma4_answer, citations = ask_esg_chatbot(target_model, test_query)
            print(f"\n========= [답변] {target_model} =========")
            print(gemma4_answer)
            print("\n========= 참고 출처 =========")
            for idx, citation in enumerate(citations):
                print(f"[{idx+1}] {citation}")
        except Exception as e:
            print(f"\n[오류] 답변 생성 실패: {e}")

        export_pgvector_to_file_and_hf(repo_id="Makesols/esg-vector-dataset3")