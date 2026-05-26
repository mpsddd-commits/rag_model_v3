from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
   # --------------------------
  # db.py
  # --------------------------
  maria_db_user: str
  maria_db_password: str
  maria_db_host: str
  maria_db_database: str
  maria_db_port: int


  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
  )

settings = Settings()
