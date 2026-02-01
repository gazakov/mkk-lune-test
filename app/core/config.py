from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Organization Directory API"
    DATABASE_URL: str = Field(..., description="PostgreSQL Async Connection String")
    API_KEY: str = Field(..., description="Static API Key for security")
    
    # дебаг режим
    DEBUG: bool = False

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env"
    )

settings = Settings()
