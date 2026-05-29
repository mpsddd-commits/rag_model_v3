"""
Main ESG RAG Pipeline Runner.
Coordinates PDF/Excel ingestion, pgvector storage, BM25 indexing,
hybrid retrieval, and dataset export.
"""
import os
import glob

from settings import settings, safe_print
from rag import (
    extract_and_chunk_pdf,
    extract_and_chunk_excel,
    init_and_save_to_pgvector,
    initialize_bm25,
    ask_esg_chatbot,
    export_pgvector_to_file_and_hf,
    # Re-export for verify.py compatibility
    search_similar_documents,
    bm25_index,
    global_chunks_pool,
    ollama_client,
)

# ────────────────────────────────────────────────────────
# Re-exported constants (backward compat)
# ────────────────────────────────────────────────────────
EMBED_MODEL = settings.embed_model
RERANK_MODEL = settings.rerank_model
DB_CONN_STR = settings.postgres_conn_str

# ────────────────────────────────────────────────────────
# Sync mutable module-level state to/from rag.py
# ────────────────────────────────────────────────────────
import rag as _rag

def __getattr__(name):
    if name in ("bm25_index", "global_chunks_pool"):
        return getattr(_rag, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __setattr__(name, value):
    if name in ("bm25_index", "global_chunks_pool"):
        setattr(_rag, name, value)
    else:
        globals()[name] = value


# ────────────────────────────────────────────────────────
# Pipeline
# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_chunks = []

    # 1. PDF ingestion
    pdf_dir = "./esg_pdf_files"
    os.makedirs(pdf_dir, exist_ok=True)
    for pdf_path in glob.glob(os.path.join(pdf_dir, "*.pdf")):
        try:
            all_chunks.extend(extract_and_chunk_pdf(pdf_path))
        except Exception as e:
            safe_print(f"[오류] {pdf_path} 읽기 실패: {e}")

    # 2. Excel ingestion
    excel_dir = "./esg_excel_files"
    os.makedirs(excel_dir, exist_ok=True)
    for pattern in ("*.xlsx", "*.xls"):
        for excel_path in glob.glob(os.path.join(excel_dir, pattern)):
            try:
                all_chunks.extend(extract_and_chunk_excel(excel_path))
            except Exception as e:
                safe_print(f"[오류] {excel_path} 읽기 실패: {e}")

    # 3. Build pgvector + BM25
    if all_chunks:
        try:
            init_and_save_to_pgvector(all_chunks)
            initialize_bm25(all_chunks)
        except Exception as e:
            safe_print(f"[오류] 지식 베이스 구축 실패: {e}")

    # 4. Demo chatbot query
    if all_chunks:
        test_query = "협력사의 탄소 배출량 실사 의무 규정과 제재 조치는 어떻게 되나요?"
        target_model = settings.mariadb_ollama_model
        try:
            answer, citations = ask_esg_chatbot(target_model, test_query)
            safe_print(f"\n========= [답변] {target_model} =========")
            safe_print(answer)
            safe_print("\n========= 참고 출처 =========")
            for idx, c in enumerate(citations):
                safe_print(f"[{idx+1}] {c}")
        except Exception as e:
            safe_print(f"\n[오류] 답변 생성 실패: {e}")

        # 5. Dataset backup & HF upload
        export_pgvector_to_file_and_hf(repo_id="Makesols/esg-vector-dataset3")
