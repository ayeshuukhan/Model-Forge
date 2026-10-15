from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "modelforge"
    postgres_user: str = "modelforge"
    postgres_password: str = "modelforge"

    redis_host: str = "localhost"
    redis_port: int = 6379

    sentiment_service_url: str = "http://localhost:8001"
    image_service_url: str = "http://localhost:8002"
    regression_service_url: str = "http://localhost:8003"

    model_service_timeout: float = 5.0

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"


settings = Settings()
