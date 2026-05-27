import os
import psycopg2
from psycopg2.extras import execute_values
import numpy as np
import ollama
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi

from config.settings import settings
from database.postgres_client import get_postgres_conn
from utils.helpers import safe_print, simple_tokenizer, check_and_pull_ollama_model

# ────────────────────────────────────────────────────────
# Reranker and Ollama Client Initialization
# ────────────────────────────────────────────────────────
safe_print(f"[로딩] 리랭킹 모델 '{settings.rerank_model}' 초기화 중...")
reranker = CrossEncoder(settings.rerank_model)

# Configure Ollama Client based on settings
os.environ["OLLAMA_HOST"] = settings.ollama_host
ollama_client = ollama.Client(host=settings.ollama_host)

# Global variables for BM25 (kept for modular and facade compatibility)
bm25_index = None
global_chunks_pool = []

def initialize_bm25(chunks_list):
    """
    Builds the BM25 keyword index in-memory from the document chunk pool.
    """
    global bm25_index, global_chunks_pool
    global_chunks_pool = chunks_list
    
    safe_print(f"[BM25] {len(chunks_list)}개의 청크 대상 스파스(키워드) 인덱스 구축 중...")
    tokenized_corpus = [simple_tokenizer(chunk["content"]) for chunk in chunks_list]
    bm25_index = BM25Okapi(tokenized_corpus)
    safe_print("[성공] BM25 키워드 인덱스 생성 완료.")

# ────────────────────────────────────────────────────────
# Ollama Embedding Extraction
# ────────────────────────────────────────────────────────
def get_ollama_embedding(text):
    """Retrieves high-dimensional vector embeddings from local Ollama service."""
    response = ollama_client.embeddings(model=settings.embed_model, prompt=text)
    return response['embedding']

def get_embedding_dimension(model_name):
    """Detects the vector dimension dynamically by calling get_ollama_embedding."""
    check_and_pull_ollama_model(ollama_client, model_name)
    try:
        test_emb = get_ollama_embedding("test")
        dim = len(test_emb)
        safe_print(f"[크기] 임베딩 모델 '{model_name}' 차원 수 감지 완료: {dim}차원")
        return dim
    except Exception as e:
        safe_print(f"[경고] 임베딩 차원 동적 감지 실패: {e}. 기본값 1024차원으로 설정합니다.")
        return 1024

# ────────────────────────────────────────────────────────
# Vector Store Management
# ────────────────────────────────────────────────────────
def init_and_save_to_pgvector(chunks_with_metadata):
    """
    Initializes PostgreSQL pgvector environment and inserts embeddings.
    Creates an HNSW index to optimize vector similarity query speed.
    """
    conn = get_postgres_conn()
    cur = conn.cursor()
    
    # 1. Enable Vector extension
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    
    dim = get_embedding_dimension(settings.embed_model)
    
    # 2. Reset and create schema
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
    
    safe_print("[시작] 하이브리드 청크 기반 임베딩 연산 및 pgvector 저장 중...")
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
    
    safe_print("[인덱스] HNSW 벡터 인덱스 생성 중...")
    cur.execute("CREATE INDEX IF NOT EXISTS esg_documents_hnsw_idx ON esg_documents USING hnsw (embedding vector_cosine_ops);")
    conn.commit()
    
    cur.close()
    conn.close()
    safe_print("[성공] pgvector 데이터베이스 구축 완료!")

# ────────────────────────────────────────────────────────
# 2-Phase Hybrid Search & Reranking
# ────────────────────────────────────────────────────────
def search_similar_documents(query, top_k=3, dense_n=10, sparse_n=10):
    """
    [하이브리드 2단계 검색 구조]
    Channel 1 (Dense): pgvector를 이용한 의미론적 코사인 유사도 검색 -> dense_n개 추출
    Channel 2 (Sparse): BM25를 이용한 키워드 텍스트 일치 검색 -> sparse_n개 추출
    통합 및 중복제거 -> 총 후보군을 Cross-Encoder 리랭커로 재정렬 후 최종 top_k 결정
    """
    global bm25_index, global_chunks_pool
    
    candidate_dict = {}  # Dictionary to eliminate duplicates (key: content)

    # ----------------------------------------------------
    # [채널 1] pgvector 의미론적(Dense) 검색
    # ----------------------------------------------------
    query_vector = get_ollama_embedding(query)
    conn = get_postgres_conn()
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
        sparse_top_chunks = bm25_index.get_top_n(tokenized_query, global_chunks_pool, n=sparse_n)
        
        for chunk in sparse_top_chunks:
            content = chunk["content"]
            if content in candidate_dict:
                # Dense and Sparse collision -> Synergy
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
    safe_print(f"[하이브리드] 1단계 후보군 총 {len(candidates)}개 획득 (중복 제거 완료).")
    
    if not candidates:
        return []

    # ----------------------------------------------------
    # [2단계] Cross-Encoder 정밀 리랭킹으로 통합순위 결정
    # ----------------------------------------------------
    safe_print(f"[리랭킹] 통합 후보군에 대해 문맥 연관성 점수 산출 중...")
    pairs = [[query, doc["content"]] for doc in candidates]
    scores = reranker.predict(pairs)
    
    for idx, score in enumerate(scores):
        candidates[idx]["rerank_score"] = float(score)
        
    # Sort candidates by rerank score descending and slice up to top_k
    candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
    final_retrieved = candidates[:top_k]
    
    if final_retrieved:
        safe_print(f"[성공] 하이브리드 리랭킹 탑 스코어: {final_retrieved[0]['rerank_score']:.4f} (출처 채널: {final_retrieved[0]['search_type']})")
    return final_retrieved
