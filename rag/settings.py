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
    maria_db_user: str
    maria_db_password: str
    maria_db_host: str
    maria_db_database: str
    maria_db_port: int

    # PostgreSQL
    postgres_user: str 
    postgres_password: str
    postgres_host: str 
    postgres_database: str
    postgres_port: int

    # Models & Ollama
    ollama_host: str
    mariadb_ollama_model: str
    embed_model: str 
    rerank_model: str 

    #huggingface
    hf_repo: str

    @property
    def postgresConnStr(self) -> str:
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
def safePrint(*args, **kwargs):
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


def simpleTokenizer(text: str) -> list[str]:
    """Strips punctuation, lowercases, and splits on whitespace for BM25."""
    if not text:
        return []
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def checkAndPullOllamaModel(ollamaClient, modelName: str) -> None:
    """Ensures the target Ollama model is available locally, pulling if absent."""
    safePrint(f"[조회] Ollama 모델 '{modelName}' 로컬 설치 상태 검사 중...")
    try:
        modelsList = ollamaClient.list()
        downloaded = []
        for m in modelsList.get("models", []):
            name = m.get("model", m.get("name", ""))
            downloaded.append(name)
            if ":" in name:
                downloaded.append(name.split(":")[0])

        if not any(modelName == m or modelName in m or m in modelName for m in downloaded):
            safePrint(f"[다운로드] '{modelName}' 모델 자동 다운로드 시작...")
            ollamaClient.pull(modelName)
            safePrint(f"[성공] 모델 '{modelName}' 다운로드 완료!")
        else:
            safePrint(f"[성공] 모델 '{modelName}' 확인 완료 (사용 가능)")
    except Exception as e:
        safePrint(f"[경고] Ollama 서비스 모델 조회/다운로드 실패: {e}")