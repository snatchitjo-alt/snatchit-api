from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://localhost/snatchit"

    # Security
    SECRET_KEY: str = "changeme-set-in-env"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Firebase — use JSON string in cloud, file path locally
    FIREBASE_CREDENTIALS_PATH: str = "firebase-credentials.json"
    FIREBASE_CREDENTIALS_JSON: str = ""

    # SMS
    SMS_LOGIN: str = ""
    SMS_PASSWORD: str = ""
    SMS_FROM: str = "SnatchIt"

    # App
    APP_NAME: str = "Snatchit"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"

settings = Settings()