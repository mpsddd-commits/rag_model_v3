from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # MariaDB Configuration
    maria_db_user: str = Field(default="root")
    maria_db_password: str = Field(default="1234")
    maria_db_host: str = Field(default="localhost")
    maria_db_database: str = Field(default="edu")
    maria_db_port: int = Field(default=23306)

    # PostgreSQL Configuration
    postgres_user: str = Field(default="root")
    postgres_password: str = Field(default="1234")
    postgres_host: str = Field(default="localhost")
    postgres_database: str = Field(default="rag3_db")
    postgres_port: int = Field(default=5432)

    # Model & Ollama Configurations
    embed_model: str = Field(default="bge-m3")
    rerank_model: str = Field(default="BAAI/bge-reranker-large")
    ollama_host: str = Field(default="http://127.0.0.1:11434")
    mariadb_ollama_model: str = Field(default="gemma4:e2b")
    verify_ollama_model: str = Field(default="qwen3.5:9b")

    @property
    def postgres_conn_str(self) -> str:
        """Dynamically builds PostgreSQL connection string."""
        return f"dbname={self.postgres_database} user={self.postgres_user} password={self.postgres_password} host={self.postgres_host} port={self.postgres_port}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # ignores extra fields in .env without raising an error
    )

settings = Settings()
