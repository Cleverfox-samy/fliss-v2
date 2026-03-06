from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Postgres
    database_url: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_environment: str = ""
    pinecone_top_k: int = 5

    # Anthropic
    anthropic_api_key: str
    fliss_model: str = "claude-3-haiku-20240307"

    # Google Maps
    google_maps_api_key: str = ""

    @property
    def use_live_db(self) -> bool:
        return bool(self.database_url and "localhost" not in self.database_url)

    @property
    def use_live_pinecone(self) -> bool:
        return bool(self.pinecone_api_key and not self.pinecone_api_key.startswith("your-"))

    @property
    def use_live_geocoding(self) -> bool:
        return bool(self.google_maps_api_key and not self.google_maps_api_key.startswith("your-"))

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
