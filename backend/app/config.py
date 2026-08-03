from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./student_os.db"
    APP_NAME: str = "Student Life OS"
    VERSION: str = "0.1.0"

    model_config = {"env_file": ".env"}


settings = Settings()
