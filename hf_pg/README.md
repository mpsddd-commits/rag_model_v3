# Enterprise ESG RAG & Verification Engine 🚀

This repository contains a modular, production-ready, and dual-database ESG (Environmental, Social, Governance) compliance and verification RAG (Retrieval-Augmented Generation) pipeline designed for aluminum supply chains.

It integrates both **MariaDB-based structured criteria checklist audit** and **PostgreSQL (pgvector) + BM25 hybrid semantics document retrieval** with CrossEncoder reranking.

---

## 🏗️ Architecture & Modular Layout

The repository has been refactored from a flat, high-coupling structure into a clean, decoupled, and highly maintainable Python application layout. 

```
hf_pg/
├── .env                       # Environment variables (Loaded via Pydantic)
├── pyproject.toml             # uv & pip dependencies
├── main.py                    # RAG indexing & pipeline demo (Facade)
├── mariadb_rag.py             # MariaDB checklist analyzer (Facade)
├── verify_chatbot.py          # Interactive verification CLI (Facade)
├── db.py                      # Compatibility facade mapping camelCase to snake_case
├── settings.py                # Compatibility facade for Settings object
│
├── config/
│   └── settings.py            # Unified settings (MariaDB, PostgreSQL, Ollama, Models)
│
├── database/
│   ├── mariadb_client.py      # Refactored connection pool and MariaDB wrapper queries
│   └── postgres_client.py     # Decoupled pgvector connections & database auto-creator
│
├── pipeline/
│   ├── document_processor.py  # PDF semantic chunker and Excel metadata parser
│   ├── dataset_exporter.py    # Chemical element tagger, numeric parser & HF exporter
│   └── checklist_uploader.py  # Uploads and syncs Excel checklist sheets to MariaDB (New)
│
├── search/
│   ├── hybrid_retriever.py    # pgvector Dense + BM25 Sparse 2-phase retrieval & Reranking
│   ├── generator.py           # Citation handling, system prompts and Ollama generator
│   └── checklist_matcher.py   # MariaDB matching, regex extraction & LLM numeric validation
│
└── utils/
    └── helpers.py             # Windows console safety printer, tokenizers & Ollama pullers
```

---

## ⚙️ Configuration (`.env`)

Create a `.env` file in the root `hf_pg/` directory. Pydantic will dynamically parse environment variables with high type-safety.

```env
# MariaDB Database Configurations
MARIA_DB_USER=user
MARIA_DB_PASSWORD=1234
MARIA_DB_HOST=localhost
MARIA_DB_DATABASE=edu
MARIA_DB_PORT=23306

# PostgreSQL (pgvector) Configurations
POSTGRES_USER=root
POSTGRES_PASSWORD=1234
POSTGRES_HOST=localhost
POSTGRES_DATABASE=rag3_db
POSTGRES_PORT=5432

# Model Configurations
EMBED_MODEL=bge-m3
RERANK_MODEL=BAAI/bge-reranker-large
OLLAMA_HOST=http://127.0.0.1:11434
MARIADB_OLLAMA_MODEL=gemma4:e2b
VERIFY_OLLAMA_MODEL=qwen3.5:9b
```

---

## 🛠️ Execution & Facade Guides

To maintain absolute **100% backward compatibility** and zero disruption, the original scripts at the root level remain unchanged in their invocations, but act as high-level facades calling under-the-hood packages.

### 1. Document Indexing and Main Pipeline
To parse PDFs inside `./esg_pdf_files`, Excel files inside `./esg_excel_files`, calculate dense embeddings, initialize the pgvector database and HNSW indexes, build the BM25 sparse index, and run a demo query:
```bash
python main.py
```
*Outputs are saved locally in both `esg_vector_backup.csv` and compressed `esg_vector_backup.parquet`, and uploaded dynamically to Hugging Face Hub dataset repository.*

### 2. ESG Checklist Sync (Excel to MariaDB)
To parse the Excel checklist master sheet (`esg_excel_files/알루미늄_Al3003_ESG_지표셋_대처방안추가.xlsx`) and upload/sync the entire set to MariaDB's `esg_checklist` table:
```bash
python pipeline/checklist_uploader.py
```

### 3. Structured Checklist Analyzer (MariaDB RAG)
To match user questions to MariaDB's `esg_checklist` table using BM25, extract numeric limits via Ollama, execute strict numerical comparisons in Python, output the safety guideline, and log results into `ai_logs` table:
```bash
python mariadb_rag.py
```

### 3. Interactive Integrity Verification CLI
To test out of-domain questions, analyze context gaps, and run multi-level rule evaluations with CrossEncoder reranking iteratively in a command-line interface:
```bash
python verify_chatbot.py
```
*Interactive logs are written dynamically to local disk file `rag_integrity_test_log.txt` with time-stamped entries.*

---

## 💡 Key Design Enhancements
- **Dynamic Namespaces**: `main.py` uses module-level `__getattr__` and `__setattr__` (Python 3.7+) to dynamically synchronize global BM25 states (`bm25_index` and `global_chunks_pool`) across different modules, eliminating reference conflicts.
- **Robust Database Safe-guards**: PostgreSQL client automatically initializes database `rag3_db` and installs `vector` extensions on-demand if missing.
- **Windows Terminal Polish**: Enforces unicode replacement safety across all scripts, eliminating encoding crashes in PowerShell and CMD when rendering non-ASCII Korean text or mathematical symbols.
