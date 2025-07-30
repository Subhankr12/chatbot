from pydantic import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Chatbot Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = "postgresql://chatbot_user:chatbot_pass@localhost:5432/chatbot_platform"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # NLP Models
    SENTENCE_TRANSFORMER_MODEL: str = "all-MiniLM-L6-v2"
    SPACY_MODEL: str = "en_core_web_sm"
    
    # OpenAI (optional for enhanced NLP)
    OPENAI_API_KEY: Optional[str] = None
    
    # Vector Database
    VECTOR_DB_PATH: str = "./data/vector_db"
    
    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    MODELS_DIR: str = "./data/models"
    
    # API
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    # Training
    MAX_TRAINING_EXAMPLES: int = 10000
    MIN_CONFIDENCE_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()