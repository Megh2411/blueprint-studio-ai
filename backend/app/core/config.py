from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    DATABASE_URL: str
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    REDIS_URL: str
    GEMINI_API_KEY: str
    # Add this line so Pydantic maps your .env variable to the settings object:
    HUGGINGFACE_API_KEY: str

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()