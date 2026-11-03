import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "nyayaguide-default-secret-key-change-in-prod")
    DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "instance" / "nyayaguide.db"))
    
    # AI / LLM Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    
    # Limits & Defaults
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", 12))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    JSON_SORT_KEYS = False

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # In production, ensure SECRET_KEY is set securely

class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    DATABASE_PATH = BASE_DIR / "instance" / "test_nyayaguide.db"

config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
