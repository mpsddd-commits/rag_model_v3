"""
Application settings and shared utility functions.
"""
import os
import re
import sys
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ────────────────────────────────────────────────────────
# Settings
# ────────────────────────────────────────────────────────
class Settings(BaseSettings):
    # MariaDB
    maria_db_user: str = Field(default="root")
    maria_db_password: str = Field(default="1234")
    maria_db_host: str = Field(default="localhost")
    maria_db_database: str = Field(default="edu")
    maria_db_port: int = Field(default=23306)
    # maria_db_user: str = Field(default="root")
    # maria_db_password: str = Field(default="1234")
    # maria_db_host: str = Field(default="aiedu.tplinkdns.com")
    # maria_db_database: str = Field(default="triplevalues")
    # maria_db_port: int = Field(default=55306)

    # PostgreSQL
    postgres_user: str = Field(default="root")
    postgres_password: str = Field(default="1234")
    postgres_host: str = Field(default="localhost")
    postgres_database: str = Field(default="rag3_db")
    postgres_port: int = Field(default=5432)

    # Models & Ollama
    embed_model: str = Field(default="bge-m3")
    rerank_model: str = Field(default="BAAI/bge-reranker-large")
    ollama_host: str = Field(default="http://localhost:11434")
    mariadb_ollama_model: str = Field(default="gemma4:e2b")
    verify_ollama_model: str = Field(default="qwen3.5:9b")

    @property
    def postgres_conn_str(self) -> str:
        return (
            f"dbname={self.postgres_database} user={self.postgres_user} "
            f"password={self.postgres_password} host={self.postgres_host} port={self.postgres_port}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


# ────────────────────────────────────────────────────────
# Shared Utilities
# ────────────────────────────────────────────────────────
def safe_print(*args, **kwargs):
    """
    Windows console encoding safety wrapper to prevent UnicodeEncodeError
    when printing special characters or non-ASCII text to stdout.
    """
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    file = kwargs.get("file", sys.stdout)
    text = sep.join(str(a) for a in args)
    try:
        file.write(text + end)
        file.flush()
    except UnicodeEncodeError:
        enc = getattr(file, "encoding", "utf-8") or "utf-8"
        file.write(text.encode(enc, errors="replace").decode(enc) + end)
        file.flush()


def simple_tokenizer(text: str) -> list[str]:
    """Strips punctuation, lowercases, and splits on whitespace for BM25."""
    if not text:
        return []
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def check_and_pull_ollama_model(ollama_client, model_name: str) -> None:
    """Ensures the target Ollama model is available locally, pulling if absent."""
    safe_print(f"[조회] Ollama 모델 '{model_name}' 로컬 설치 상태 검사 중...")
    try:
        models_list = ollama_client.list()
        downloaded = []
        for m in models_list.get("models", []):
            name = m.get("model", m.get("name", ""))
            downloaded.append(name)
            if ":" in name:
                downloaded.append(name.split(":")[0])

        if not any(model_name == m or model_name in m or m in model_name for m in downloaded):
            safe_print(f"[다운로드] '{model_name}' 모델 자동 다운로드 시작...")
            ollama_client.pull(model_name)
            safe_print(f"[성공] 모델 '{model_name}' 다운로드 완료!")
        else:
            safe_print(f"[성공] 모델 '{model_name}' 확인 완료 (사용 가능)")
    except Exception as e:
        safe_print(f"[경고] Ollama 서비스 모델 조회/다운로드 실패: {e}")

