import os
from typing import Optional

class Settings:
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Photo Validation Service"
    
    # Database
    # Для локальной разработки используем localhost
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/photo_validation"
    )
    
    # Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./local_storage")
    
    # Validation settings
    MIN_IMAGE_WIDTH: int = 420
    MIN_IMAGE_HEIGHT: int = 525
    MAX_FILE_SIZE_BYTES: int = 1 * 1024 * 1024  # 1MB
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
