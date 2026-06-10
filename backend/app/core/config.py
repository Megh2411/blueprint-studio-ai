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
    STABILITY_API_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None

    class Config:
        env_file = ".env"

settings = Settings()