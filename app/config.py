from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://hotel:hotel@db:5432/hotel"
    secret_key: str = "change-this-secret-before-deployment"
    access_token_minutes: int = 480
    upload_dir: str = "uploads"
    max_upload_mb: int = 12
    gcs_bucket: str | None = None
    cors_origins: str = "*"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
