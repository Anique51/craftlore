from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = ""
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_dir: str = "data/chroma"


settings = Settings()
