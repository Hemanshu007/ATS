from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://ats:ats_secret@localhost:5432/ats_db"
    SECRET_KEY: str  # No default — must be set via env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    UPLOAD_DIR: str = "./uploads"

    # SMTP
    SMTP_HOST: str = "smtp.fastmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    MAIL_FROM: str = ""

    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str = ""

    # Email transport: "smtp" or "ses" or "" (disabled)
    EMAIL_TRANSPORT: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
