from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    DEMO_MODE: bool = True
    DEEPSEEK_API_KEY: str = ''
    DEEPSEEK_API_BASE: str = 'https://api.deepseek.com/v1'
    MODEL_NAME: str = 'deepseek-chat'
    tavily_api_key: str = ''
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / '.chroma_data' / 'novel_knowledge')
    EMBEDDING_MODEL: str = 'sentence-transformers/all-MiniLM-L6-v2'
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / '.env'), env_file_encoding='utf-8', extra='ignore')

settings = Settings()
