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
MARIA_DB_USER=root
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
