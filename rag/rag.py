"""
RAG pipeline: document ingestion, pgvector storage, hybrid retrieval,
answer generation, and dataset export.
"""
import os
import re
import datetime
import hashlib

import numpy as np
import ollama
import pandas as pd
import psycopg2
from datasets import Dataset
from psycopg2.extras import execute_values
from pypdf import PdfReader
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from settings import settings, safe_print, simple_tokenizer, check_and_pull_ollama_model
from db import get_postgres_conn


# # ════════════════════════════════════════════════════════
# # Ollama client & reranker (module-level singletons)
# # ════════════════════════════════════════════════════════
# os.environ["OLLAMA_HOST"] = settings.ollama_host
# ollama_client = ollama.Client(host=settings.ollama_host)

# safe_print(f"[로딩] 리랭킹 모델 '{settings.rerank_model}' 초기화 중...")
# reranker = CrossEncoder(settings.rerank_model)

# # In-memory BM25 state
# bm25_index = None
# global_chunks_pool: list = []
# ════════════════════════════════════════════════════════
# Ollama client & reranker (module-level singletons)
# ════════════════════════════════════════════════════════
os.environ["OLLAMA_HOST"] = settings.ollama_host

safe_print(f"[로딩] 리랭킹 모델 '{settings.rerank_model}' 초기화 중...")
# 💡 만약 여기서 멈춘다면 PyTorch 환경 문제입니다. (캐시 폴더 권한 등 검사 필요)
reranker = CrossEncoder(settings.rerank_model) 
safe_print("[성공] 리랭킹 모델 로드 완료.")

safe_print(f"[접속] Ollama 호스트({settings.ollama_host}) 연결 시도 중...")
# 💡 타임아웃 설정을 추가하여 무한 대기를 방지합니다 (httpx 기반 타임아웃 부여)
import httpx
ollama_client = ollama.Client(
    host=settings.ollama_host,
    timeout=httpx.Timeout(10.0, connect=5.0) # 5초 내 연결 실패 시 에러 발생
)

# Ollama가 켜져 있는지 가볍게 검사하여 블록 현상 사전 차단
try:
    ollama_client.list()
    safe_print("[성공] Ollama 서비스 연결 확인 완료.")
except Exception as e:
    safe_print(f"\n❌ [🚨 치명적 오류] Ollama 엔진이 꺼져있거나 접속할 수 없습니다: {e}")
    safe_print("팁: 터미널에서 'ollama serve'가 구동 중인지 또는 포트가 열려있는지 확인하세요.")
    sys.exit(1)

# In-memory BM25 state
bm25_index = None
global_chunks_pool: list = []


# ════════════════════════════════════════════════════════
# Document Processing
# ════════════════════════════════════════════════════════
def extract_and_chunk_pdf(pdf_path: str, chunk_size: int = 600, chunk_overlap: int = 150) -> list[dict]:
    """
    Hybrid semantic chunking: splits on sentence boundaries first,
    then merges up to chunk_size characters while preserving overlap context.
    """
    safe_print(f"[PDF] '{pdf_path}' 하이브리드 시맨틱 청킹 시작...")
    reader = PdfReader(pdf_path)
    file_name = os.path.basename(pdf_path)
    chunks: list[dict] = []

    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or not text.strip():
            continue
        text = text.replace("\r\n", "\n").strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            if len(sentence) > chunk_size:
                if current_chunk:
                    chunks.append(_make_chunk(current_chunk, file_name, "PDF", page_idx + 1))
                    current_chunk = ""
                for sub in [sentence[i:i + chunk_size] for i in range(0, len(sentence), chunk_size - chunk_overlap)]:
                    chunks.append(_make_chunk(sub, file_name, "PDF", page_idx + 1))
                continue

            if len(current_chunk) + len(sentence) + 1 > chunk_size:
                if current_chunk:
                    chunks.append(_make_chunk(current_chunk, file_name, "PDF", page_idx + 1))
                overlap_start = max(0, len(current_chunk) - chunk_overlap)
                current_chunk = current_chunk[overlap_start:] + " " + sentence
            else:
                current_chunk += (" " if current_chunk else "") + sentence

        if current_chunk.strip():
            chunks.append(_make_chunk(current_chunk, file_name, "PDF", page_idx + 1))

    safe_print(f"[성공] PDF 분할 완료: {len(chunks)}개 청크.")
    return chunks


def extract_and_chunk_excel(excel_path: str) -> list[dict]:
    """
    Structural chunking: each Excel row becomes a [column]: value pipe-joined string.
    """
    safe_print(f"[엑셀] '{excel_path}' 구조적 청킹 시작...")
    file_name = os.path.basename(excel_path)
    df = pd.read_excel(excel_path, engine="openpyxl").fillna("")
    chunks: list[dict] = []

    for index, row in df.iterrows():
        parts = [f"[{col}]: {str(row[col]).strip()}" for col in df.columns if str(row[col]).strip()]
        if not parts:
            continue
        chunk_text = " | ".join(parts)
        chunks.append({
            "content": f"설명: 해당 데이터는 {file_name}의 정보 항목입니다. 세부 내용 -> {chunk_text}",
            "source_file": file_name,
            "source_type": "Excel",
            "page_or_row": f"{index + 1}번째 행",
        })

    safe_print(f"[성공] 엑셀 분할 완료: {len(chunks)}개 레코드.")
    return chunks


def _make_chunk(content: str, source_file: str, source_type: str, page: int) -> dict:
    return {
        "content": content.strip(),
        "source_file": source_file,
        "source_type": source_type,
        "page_or_row": f"{page}페이지",
    }


# ════════════════════════════════════════════════════════
# Embedding & pgvector
# ════════════════════════════════════════════════════════
def get_ollama_embedding(text: str) -> list[float]:
    """Returns a dense embedding vector from the local Ollama service."""
    return ollama_client.embeddings(model=settings.embed_model, prompt=text)["embedding"]


def _detect_embedding_dim(model_name: str) -> int:
    check_and_pull_ollama_model(ollama_client, model_name)
    try:
        dim = len(get_ollama_embedding("test"))
        safe_print(f"[크기] 임베딩 차원 감지 완료: {dim}차원")
        return dim
    except Exception as e:
        safe_print(f"[경고] 임베딩 차원 감지 실패: {e}. 기본값 1024 사용.")
        return 1024


def init_and_save_to_pgvector(chunks: list[dict]) -> None:
    """
    Resets the esg_documents table, inserts embeddings, and builds an HNSW index.
    """
    conn = get_postgres_conn()
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()

    dim = _detect_embedding_dim(settings.embed_model)
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

    safe_print("[시작] 임베딩 연산 및 pgvector 저장 중...")
    rows = [
        (item["content"], str(get_ollama_embedding(item["content"])),
         item["source_file"], item["source_type"], item["page_or_row"])
        for item in chunks
    ]
    execute_values(
        cur,
        "INSERT INTO esg_documents (content, embedding, source_file, source_type, page_or_row) VALUES %s",
        rows,
    )
    conn.commit()

    cur.execute("CREATE INDEX IF NOT EXISTS esg_documents_hnsw_idx ON esg_documents USING hnsw (embedding vector_cosine_ops);")
    conn.commit()
    cur.close()
    conn.close()
    safe_print("[성공] pgvector 데이터베이스 구축 완료!")


# ════════════════════════════════════════════════════════
# BM25
# ════════════════════════════════════════════════════════
def initialize_bm25(chunks: list[dict]) -> None:
    """Builds the in-memory BM25 keyword index from the chunk pool."""
    global bm25_index, global_chunks_pool
    global_chunks_pool = chunks
    safe_print(f"[BM25] {len(chunks)}개 청크 인덱스 구축 중...")
    bm25_index = BM25Okapi([simple_tokenizer(c["content"]) for c in chunks])
    safe_print("[성공] BM25 인덱스 생성 완료.")


# ════════════════════════════════════════════════════════
# Hybrid Retrieval
# ════════════════════════════════════════════════════════
def search_similar_documents(query: str, top_k: int = 3, dense_n: int = 10, sparse_n: int = 10) -> list[dict]:
    """
    2-phase hybrid search:
    1) Dense (pgvector cosine) + Sparse (BM25) → merged candidate pool
    2) Cross-Encoder reranking → top_k results
    """
    global bm25_index, global_chunks_pool
    candidates: dict[str, dict] = {}

    # Channel 1 – Dense
    query_vector = get_ollama_embedding(query)
    conn = get_postgres_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT content, source_file, source_type, page_or_row FROM esg_documents ORDER BY embedding <=> %s LIMIT %s;",
        (str(query_vector), dense_n),
    )
    for row in cur.fetchall():
        candidates[row[0]] = {"content": row[0], "source_file": row[1], "source_type": row[2], "page_or_row": row[3], "search_type": "Dense"}
    cur.close()
    conn.close()

    # Channel 2 – Sparse
    if bm25_index is not None:
        for chunk in bm25_index.get_top_n(simple_tokenizer(query), global_chunks_pool, n=sparse_n):
            content = chunk["content"]
            if content in candidates:
                candidates[content]["search_type"] = "Hybrid_Both"
            else:
                candidates[content] = {**chunk, "search_type": "Sparse"}

    candidate_list = list(candidates.values())
    safe_print(f"[하이브리드] 후보군 {len(candidate_list)}개 획득.")

    if not candidate_list:
        return []

    # Rerank
    scores = reranker.predict([[query, doc["content"]] for doc in candidate_list])
    for doc, score in zip(candidate_list, scores):
        doc["rerank_score"] = float(score)
    candidate_list.sort(key=lambda x: x["rerank_score"], reverse=True)
    top = candidate_list[:top_k]
    if top:
        safe_print(f"[리랭킹] 탑 스코어: {top[0]['rerank_score']:.4f} (채널: {top[0]['search_type']})")
    return top


# ════════════════════════════════════════════════════════
# Generation
# ════════════════════════════════════════════════════════
def ask_esg_chatbot(model_name: str, query: str) -> tuple[str, list[str]]:
    """
    RAG answer generation:
    1) Hybrid retrieval → top 3 contexts
    2) Structured prompt with citation protocol
    3) Ollama LLM synthesis
    """
    check_and_pull_ollama_model(ollama_client, model_name)
    contexts = search_similar_documents(query, top_k=3)

    if not contexts:
        return "[경고] 검색 결과가 없어 답변을 구성할 수 없습니다.", []

    citations = []
    formatted = []
    for idx, ctx in enumerate(contexts):
        source_info = f"{ctx['source_file']} ({ctx['page_or_row']})"
        citations.append(source_info)
        formatted.append(f"[참고 자료 {idx+1}] (출처: {source_info})\n내용: {ctx['content']}")

    prompt = (
        "당신은 ESG 공급망 실사 지침 및 글로벌 규제 전문가입니다.\n"
        "주어진 [참고 문서]의 핵심 내용을 기반으로 [사용자 질문]에 신뢰할 수 있는 정확한 정보를 제공하세요.\n"
        "반드시 제공된 문서에 나와 있는 내용만을 토대로 요약 및 분석을 수행해야 합니다.\n"
        "답변할 때 해당 내용이 어떤 참고 자료에서 온 것인지 본문에 명시하세요.\n\n"
        f"[참고 문서]\n{chr(10).join(formatted)}\n\n"
        f"[사용자 질문]\n{query}"
    )

    safe_print(f"\n[AI] [{model_name}] 답변 생성 중...")
    try:
        response = ollama_client.generate(model=model_name, prompt=prompt)
        return response["response"], citations
    except Exception as e:
        return f"LLM 답변 생성 실패: {e}", citations


# ════════════════════════════════════════════════════════
# Dataset Export
# ════════════════════════════════════════════════════════
def export_pgvector_to_file_and_hf(repo_id: str = "Makesols/esg-vector-dataset3") -> None:
    """
    Exports esg_documents to local CSV/Parquet and optionally to Hugging Face Hub.
    Adds MD5 chunk hash, upload timestamp, detected chemical elements, and numeric values.
    """
    safe_print("\n[백업/HF] 데이터셋 파이프라인 가동...")
    try:
        conn = get_postgres_conn()
        cur = conn.cursor()
        cur.execute("SELECT id, content, embedding::text, source_file, source_type, page_or_row FROM esg_documents;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        safe_print(f"[오류] PostgreSQL 조회 실패: {e}")
        return

    if not rows:
        safe_print("[경고] 저장된 데이터가 없어 백업을 건너뜁니다.")
        return

    df = pd.DataFrame(rows, columns=["id", "content", "embedding", "source_file", "source_type", "page_or_row"])
    df["embedding"] = df["embedding"].apply(lambda x: [float(i) for i in x.strip("[]").split(",")])
    df["chunk_hash"] = df["content"].apply(lambda x: hashlib.md5(x.encode()).hexdigest())
    df["uploaded_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def extract_elements(text):
        tags = [e for e in ["Mn", "Cu", "Al", "Si", "Fe", "Mg", "Zn", "Ti"] if e in text]
        return tags or ["General_ESG"]

    def extract_numbers(text):
        found = re.findall(r"\d+\.\d+\s*%|\d+\s*%\s*|\d+\s*[Mm]pa", text)
        return [f.strip() for f in found] or ["None"]

    df["detected_elements"] = df["content"].apply(extract_elements)
    df["detected_numbers"] = df["content"].apply(extract_numbers)

    try:
        df.to_csv("esg_vector_backup.csv", index=False, encoding="utf-8-sig")
        df.to_parquet("esg_vector_backup.parquet", index=False)
        safe_print("[성공] 로컬 백업 완료 (CSV + Parquet)")
    except Exception as e:
        safe_print(f"[경고] 로컬 백업 오류: {e}")

    if repo_id:
        try:
            safe_print(f"[HF] '{repo_id}' 업로드 중...")
            Dataset.from_pandas(df).push_to_hub(repo_id, private=True)
            safe_print("[성공] HF 데이터셋 업로드 완료!")
        except Exception as e:
            safe_print(f"[오류] HF 업로드 실패: {e}")

# ==========================================
# rag.py 맨 아래에 이 코드를 추가해 주세요!
# ==========================================

if __name__ == "__main__":
    import glob
    
    safe_print("\n=== 🚀 [단계 1] PostgreSQL(pgvector) 연결 검증 ===")
    try:
        safe_print("[DB] 연결 시도 중...")
        conn = get_postgres_conn()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        safe_print(f"[성공] DB 연결 완료: {cur.fetchone()[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        safe_print(f"❌ [오류] PostgreSQL 연결에 실패했습니다: {e}")
        safe_print("도커 컨테이너 상태 및 .env의 DB 설정을 확인하세요.")
        exit(1)

    safe_print("\n=== 🚀 [단계 2] 로컬 문서 탐색 및 하이브리드 청킹 ===")
    all_chunks = []
    
    # 1. PDF 처리
    pdf_path = "./esg_pdf_files" 
    if os.path.exists(pdf_path):
        pdf_files = glob.glob(os.path.join(pdf_path, "*.pdf"))
        safe_print(f"[탐색] 발견된 PDF 파일: {len(pdf_files)}개")
        for f in pdf_files:
            all_chunks.extend(extract_and_chunk_pdf(f))
            
    # 2. Excel 처리
    excel_path = "./esg_excel_files"
    if os.path.exists(excel_path):
        excel_files = glob.glob(os.path.join(excel_path, "*.xlsx")) + glob.glob(os.path.join(excel_path, "*.xls"))
        safe_print(f"[탐색] 발견된 엑셀 파일: {len(excel_files)}개")
        for f in excel_files:
            all_chunks.extend(extract_and_chunk_excel(f))

    # 3. 파이프라인 트리거 (pgvector 적재 후 바로 허깅페이스 업로드)
    if all_chunks:
        safe_print(f"\n=== 🚀 [단계 3] pgvector & BM25 지식 적재 시작 (총 {len(all_chunks)}개) ===")
        # 3-1. PostgreSQL 및 HNSW 인덱스 빌드
        init_and_save_to_pgvector(all_chunks)
        # 3-2. BM25 인덱스 빌드
        initialize_bm25(all_chunks)
        
        # 💡 [변경] 무거운 AI 답변 생성(ask_esg_chatbot)을 건너뛰고, 바로 데이터셋 발행을 수행합니다.
        safe_print("\n=== 🚀 [단계 4] 로컬 멀티포맷 백업 및 허깅페이스 데이터셋 발행 ===")
        try:
            # repo_id는 본인의 Hugging Face 레포지토리 주소에 맞게 수정하셔도 됩니다.
            export_pgvector_to_file_and_hf(repo_id="Makesols/esg-vector-dataset3")
            safe_print("\n🎉 [완료] 전체 데이터 수집 및 허깅페이스 업로드 파이프라인이 성공적으로 끝났습니다!")
        except Exception as e:
            safe_print(f"\n❌ [오류] 데이터 백업/업로드 과정에서 문제가 발생했습니다: {e}")
            
    else:
        safe_print("\n❌ [경고] 지정된 폴더 내에 처리할 PDF/Excel 파일이 존재하지 않습니다.")