import os

class Settings:
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "scanner")
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Pentest Scanner Orchestrator"

settings = Settings()
