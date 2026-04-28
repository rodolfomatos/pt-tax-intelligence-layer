from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    ptdata_api_key: str = Field(default="", alias="PTDATA_API_KEY")
    ptdata_api_url: str = Field(default="https://api.ptdata.org/mcp", alias="PTDATA_API_URL")
    
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    llm_model: str = Field(default="gpt-4", alias="LLM_MODEL")
    
    iaedu_api_key: str = Field(default="", alias="IAEDU_API_KEY")
    iaedu_endpoint: str = Field(default="", alias="IAEDU_ENDPOINT")
    iaedu_channel_id: str = Field(default="", alias="IAEDU_CHANNEL_ID")
    iaedu_model_name: str = Field(default="iaedu-gpt4o", alias="IAEDU_MODEL_NAME")
    use_iaedu: bool = Field(default=False, alias="USE_IAEDU")
    
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/tax_intelligence", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_key: str = Field(default="", alias="API_KEY")
    
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    cache_ttl_seconds: int = Field(default=86400, alias="CACHE_TTL_SECONDS")
    
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")
    rate_limit_burst: int = Field(default=10, alias="RATE_LIMIT_BURST")
    
    chroma_persist_dir: str = Field(default="/data/chroma", alias="CHROMA_PERSIST_DIR")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
