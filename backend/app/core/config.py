import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Multimodal AI Chatbot"
    API_V1_STR: str = "/api"
    DEBUG: bool = True
    
    # CORS Origins (accepts comma-separated string or list)
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database: Defaults to local PostgreSQL with pgvector
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/mm_chatbot"
    
    # Upload Storage
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: List[str] = [
        ".txt", ".md", ".pdf", ".docx", 
        ".png", ".jpg", ".jpeg", ".webp", ".gif",
        ".mp3", ".wav", ".m4a", ".webm", ".ogg"
    ]

    # AI Model Providers: 'openai', 'gemini', or 'mock'
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"

    # Embeddings: 'openai', 'gemini', or 'mock'
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIM: int = 3072

    # Web Search: 'tavily', 'duckduckgo', or 'mock'
    SEARCH_PROVIDER: str = "duckduckgo"
    TAVILY_API_KEY: str = ""

    # RAG Tuning
    RAG_CHUNK_SIZE: int = 600
    RAG_CHUNK_OVERLAP: int = 100
    RAG_TOP_K: int = 4
    RAG_SIMILARITY_THRESHOLD: float = 0.35

    # Authentication & JWT Security
    JWT_SECRET: str = "aura-chatbot-secure-jwt-secret-key-prod-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
