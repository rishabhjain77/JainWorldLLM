# backend/config.py

from pydantic_settings import BaseSettings
from typing import Literal
import os
from pathlib import Path

# Get project root directory
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
SCRAPED_DIR = DATA_DIR / "scraped_content"
MODULES_DIR = DATA_DIR / "learning_modules"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
SCRAPED_DIR.mkdir(exist_ok=True)
MODULES_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Application settings"""
    
    # API Keys
    groq_api_key: str
    openai_api_key: str | None = None
    elevenlabs_api_key: str | None = None
    
    # App Settings
    app_name: str = "Jain Gyan Yatra"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # LLM Configuration
    llm_provider: Literal["groq", "openai"] = "groq"
    llm_model: str = "llama-3.1-8b-instant"  # Groq's free 70B model
    llm_temperature: float = 0.7
    llm_max_tokens: int = 1500
    
    # Embedding Configuration
    embedding_model: str = "all-MiniLM-L6-v2"  # Local, fast, 80MB
    
    # Vector DB Configuration
    chroma_persist_directory: str = str(CHROMA_DIR)
    collection_name: str = "jain_knowledge"
    
    # RAG Configuration
    top_k_results: int = 5  # Number of relevant chunks to retrieve
    chunk_size: int = 1000  # Characters per chunk
    chunk_overlap: int = 200  # Overlap between chunks
    
    # Audio Configuration
    tts_provider: Literal["elevenlabs", "openai", "local"] = "elevenlabs"
    
    # Session Configuration
    session_timeout: int = 3600  # 1 hour in seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Initialize settings
settings = Settings()


# Helper function to check if API keys are set
def check_api_keys():
    """Check if required API keys are configured"""
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY not found in .env file")
    print("✅ Groq API key configured")
    
    if settings.openai_api_key:
        print("✅ OpenAI API key configured")
    
    if settings.elevenlabs_api_key:
        print("✅ ElevenLabs API key configured")


if __name__ == "__main__":
    # Test configuration
    print(f"App Name: {settings.app_name}")
    print(f"LLM Model: {settings.llm_model}")
    print(f"Chroma Directory: {settings.chroma_persist_directory}")
    check_api_keys()