from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
  host_ip: str

  # --------------------------
  # db.py
  # --------------------------
  maria_db_user: str
  maria_db_password: str
  maria_db_host: str
  maria_db_database: str
  maria_db_port: int

  redis_host: str
  redis_port: int
  redis_db1: int
  redis_db2: int
  redis_db3: int
    # tokenset.py
  # --------------------------
  # secret_key: str
  private_key: str = "secrets/authpr.pem"
  public_key: str = "secrets/authpb.pem"
  access_token_expire_minutes: int
  refresh_token_expire_days: int
  invite_token_expire_days: int

  model_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
  )

settings = Settings()
