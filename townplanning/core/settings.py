"""
Application Settings.

Loads configuration from the .env file.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # --------------------------------------------------
    # Application
    # --------------------------------------------------

    APP_NAME: str

    APP_VERSION: str

    DEBUG: bool = False

    HOST: str

    PORT: int

    LOG_LEVEL: str = "INFO"

    # --------------------------------------------------
    # Database
    # --------------------------------------------------

    DATABASE_URL: str

    SQL_ECHO: bool = False

    # --------------------------------------------------
    # OpenAI
    # --------------------------------------------------

    OPENAI_API_KEY: str = ""

    OPENAI_MODEL: str

    EMBEDDING_MODEL: str

    # --------------------------------------------------
    # Ollama
    # --------------------------------------------------

    OLLAMA_HOST: str

    OLLAMA_MODEL: str
    OLLAMA_TIMEOUT: int = 600

    # --------------------------------------------------
    # Vector Store
    # --------------------------------------------------

    #CHROMA_PATH: str
    AI_PROVIDER: str = "openai"

    #OPENAI_API_KEY: str

    #OPENAI_MODEL: str

    CHROMA_PATH: str = "./data/chroma"

    CHROMA_COLLECTION: str = "townplanning"

    EMBEDDING_PROVIDER: str = "ollama"


    EMBEDDING_BATCH_SIZE: int = 100

    SEARCH_TOP_K: int = 20

    SEARCH_MAX_RESULTS: int = 8 

    SEARCH_MIN_SCORE: float = 0.30
    MAX_CONTEXT_CHARS: int  = 12000
    ####################################################################
    # Semantic Search
    ####################################################################

    SEARCH_TOP_K:int = 50              # Retrieve candidates from Chroma
    SEARCH_MAX_RESULTS:int = 50        # Keep after filtering
    SEARCH_MIN_SCORE:float = 0.25

    ####################################################################
    # Reranking
    ####################################################################

    RERANK_TOP_K:int = 8               # Final documents for LLM
    RERANK_MIN_SCORE:float = -100.0

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()