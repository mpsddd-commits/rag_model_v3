"""
Main ESG RAG Pipeline Runner.
Coordinates PDF/Excel document parsing, embedding generation, pgvector storage,
hybrid retrieval (pgvector + BM25), and dataset exporting by delegating to specialized modules.
"""
import os
import glob
from config.settings import settings
from utils.helpers import safe_print, simple_tokenizer, check_and_pull_ollama_model
from database.postgres_client import get_postgres_conn
from pipeline.document_processor import extract_and_chunk_pdf, extract_and_chunk_excel
from pipeline.dataset_exporter import export_pgvector_to_file_and_hf
import search.hybrid_retriever as hr
from search.hybrid_retriever import (
    get_ollama_embedding,
    init_and_save_to_pgvector,
    initialize_bm25,
    search_similar_documents,
    reranker,
    ollama_client
)
from search.generator import ask_esg_chatbot

# ────────────────────────────────────────────────────────
# Constants & Connection Parameters (Re-exported for compatibility)
# ────────────────────────────────────────────────────────
EMBED_MODEL = settings.embed_model
RERANK_MODEL = settings.rerank_model
DB_CONN_STR = settings.postgres_conn_str
get_db_connection = get_postgres_conn

# ────────────────────────────────────────────────────────
# Dynamic Module Attribute Mapping (Python 3.7+)
# Syncs rebound attributes to search.hybrid_retriever namespace
# ────────────────────────────────────────────────────────
def __getattr__(name):
    if name == 'bm25_index':
        return hr.bm25_index
    if name == 'global_chunks_pool':
        return hr.global_chunks_pool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __setattr__(name, value):
    if name in ('bm25_index', 'global_chunks_pool'):
        setattr(hr, name, value)
    else:
        super().__setattr__(name, value)

# ────────────────────────────────────────────────────────
# Main pipeline execution flow
# ────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_chunks = []

    # 1. Process PDF directory
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
                safe_print(f"[오류] {pdf_path} 읽기 실패: {e}")

    # 2. Process Excel directory
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
                safe_print(f"[오류] {excel_path} 읽기 실패: {e}")

    # 3. Initialize pgvector & BM25 index
    if all_chunks:
        try:
            # Save dense embeddings to PostgreSQL pgvector
            init_and_save_to_pgvector(all_chunks)
            
            # Setup sparse BM25 keyword index
            initialize_bm25(all_chunks)
        except Exception as e:
            safe_print(f"[오류] 지식 베이스(Hybrid) 구축 실패: {e}")

    # 4. ESG Chatbot & Backup pipeline demo
    if all_chunks:
        test_query = "협력사의 탄소 배출량 실사 의무 규정과 제재 조치는 어떻게 되나요?"
        target_model = settings.mariadb_ollama_model
        try:
            gemma4_answer, citations = ask_esg_chatbot(target_model, test_query)
            safe_print(f"\n========= [답변] {target_model} =========")
            safe_print(gemma4_answer)
            safe_print("\n========= 참고 출처 =========")
            for idx, citation in enumerate(citations):
                safe_print(f"[{idx+1}] {citation}")
        except Exception as e:
            safe_print(f"\n[오류] 답변 생성 실패: {e}")

        # Dataset local backup and Hugging Face upload
        export_pgvector_to_file_and_hf(repo_id="Makesols/esg-vector-dataset3")