"""
IntelliDesk Configuration
Loads settings from environment variables / .env file.

This file supports:
1. Local development using MySQL/XAMPP
2. Online deployment using DATABASE_URL, for example PostgreSQL on Koyeb
"""

import os
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


class Settings(BaseSettings):
    # Local MySQL database settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "intellidesk"

    # Cloud database URL
    # Example:
    # postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
    CLOUD_DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # JWT
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AI
    NLP_MODEL: str = "facebook/bart-large-mnli"
    CONFIDENCE_THRESHOLD: float = 0.30

    # Groq
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Unsplash
    UNSPLASH_ACCESS_KEY: str = os.getenv("UNSPLASH_ACCESS_KEY", "")

    # Email
    EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USER: str = os.getenv("EMAIL_USER", "")
    EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_FROM: str = os.getenv("EMAIL_FROM", "")

    # Base URL
    BASE_URL: str = os.getenv("BASE_URL", "http://localhost:8000")

    @property
    def DATABASE_URL(self) -> str:
        """
        If DATABASE_URL exists, use cloud database.
        Otherwise use local MySQL/XAMPP database.
        """
        if self.CLOUD_DATABASE_URL:
            return self.CLOUD_DATABASE_URL

        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# Database engine and session
engine = create_engine(settings.DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """Dependency to get DB session in route handlers."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
