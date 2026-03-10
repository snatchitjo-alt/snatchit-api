from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # Firebase
    FIREBASE_CREDENTIALS_PATH: str

    # SMS
    SMS_LOGIN: str
    SMS_PASSWORD: str
    SMS_FROM: str

    # App
    APP_NAME: str = "Snatchit"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    BASE_URL: str = "http://192.168.0.159:8000"   # override in production .env / Railway env vars

    # Optional: Firebase credentials as JSON string (alternative to file path)
    FIREBASE_CREDENTIALS_JSON: str = ""

    class Config:
        env_file = ".env"

settings = Settings()