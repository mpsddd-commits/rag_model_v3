# utils/settings.py
import os
import re
import sys
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    host_ip: str
    domain: str
    
    # --------------------------
    # kafka config
    # --------------------------
    kafka_server: str = "kafka:9092"
    kafka_topic: str = "email"
    kafka_self_assess_topic: str = "self_assess"
    
    # --------------------------
    # email config
    # --------------------------
    mail_username: str
    mail_password: str
    mail_from: str
    mail_port: int = 587
    mail_server: str = "smtp.gmail.com"
    mail_from_name: str = "W.I.T.H"
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    use_credentials: bool = True
    validate_certs: bool = True
    
    # tokenset.py
    # --------------------------
    private_key: str = "secrets/authpr.pem"
    public_key: str = "secrets/authpb.pem"
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    invite_token_expire_days: int
    
    # --------------------------
    # rediscl.py
    # --------------------------
    redis_host: str
    redis_port: int
    redis_db1: int
    redis_db2: int
    redis_db3: int
    
    # --------------------------
    # file.py
    # --------------------------
    service_key: str
    
    # --------------------------
    # ocr.py
    # --------------------------
    ocr_key_path: str = "secrets/ocr_key.json"
    
    # --------------------------
    # MariaDB (공통 적용)
    # --------------------------
    maria_db_user: str
    maria_db_password: str
    maria_db_host: str
    maria_db_database: str
    maria_db_external: str
    maria_db_port: int
    maria_db_key: str
    cookie_key: str

    # --------------------------
    # ➕ [AI 엔진에서 이식] PostgreSQL (pgvector Storage)
    # --------------------------
    postgres_user: str 
    postgres_password: str
    postgres_host: str 
    postgres_database: str
    postgres_port: int

    # --------------------------
    # ➕ [AI 엔진에서 이식] Models & Ollama / HuggingFace
    # --------------------------
    ollama_host: str
    mariadb_ollama_model: str
    embed_model: str 
    rerank_model: str 
    hf_repo: str

    # 💡 PostgreSQL 연결 문자열 프로퍼티 이식
    @property
    def postgresConnStr(self) -> str:
        return (
            f"dbname={self.postgres_database} user={self.postgres_user} "
            f"password={self.postgres_password} host={self.postgres_host} port={self.postgres_port}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore", # .env에 다른 변수들이 더 있어도 에러 나지 않도록 방어
    )

# 싱글톤 인스턴스 생성
settings = Settings()


# =====================================================================
# ➕ [AI 엔진에서 이식] 엔진 구동에 필수적인 공유 유틸리티 함수 레이어
# =====================================================================

def safePrint(*args, sep=" ", end="\n", **kwargs) -> None:
    """인코딩 깨짐을 방지하고 터미널에 안전하게 로그를 출력하는 함수"""
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
    """BM25 검색 알고리즘을 위한 알파벳/숫자 기반 간단 토크나이저"""
    if not text:
        return []
    return re.sub(r"[^\w\s]", " ", text.lower()).split()


def checkAndPullOllamaModel(ollamaClient, modelName: str) -> None:
    """Ollama 로컬 모델 설치 상태를 검사하고, 없으면 자동으로 pull하는 함수"""
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
            safePrint(f"[알림] 로컬에 '{modelName}' 모델이 발견되지 않아 다운로드를 시작합니다. 시간이 다소 소요될 수 있습니다.")
            ollamaClient.pull(modelName)
            safePrint(f"[완료] '{modelName}' 모델 다운로드 완료.")
        else:
            safePrint(f"[확인] 로컬에 '{modelName}' 모델이 이미 준비되어 있습니다.")
    except Exception as e:
        safePrint(f"[경고] Ollama 모델 상태 확인 중 예외가 발생했으나 프로세스를 계속 진행합니다: {e}")