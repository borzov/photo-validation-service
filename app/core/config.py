# ФАЙЛ: app/core/config.py

import os
from typing import Optional, List

class Settings:
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Photo Validation Service"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/photo_validation"
    )

    # Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./local_storage")

    # Validation settings - Image Dimensions
    MIN_IMAGE_WIDTH: int = 400
    MIN_IMAGE_HEIGHT: int = 500
    MAX_FILE_SIZE_BYTES: int = int(os.getenv("MAX_FILE_SIZE_BYTES", 1 * 1024 * 1024))  # 1MB

    # Validation settings - Face Detection & Position
    FACE_CONFIDENCE_THRESHOLD: float = 0.4
    FACE_MIN_AREA_RATIO: float = 0.05
    FACE_MAX_AREA_RATIO: float = 0.8
    FACE_CENTER_TOLERANCE: float = 0.4

    # Validation settings - Face Pose (degrees)
    MAX_FACE_YAW: float = 25.0
    MAX_FACE_PITCH: float = 25.0
    MAX_FACE_ROLL: float = 25.0

    # Validation settings - Quality Analysis
    GRAYSCALE_SATURATION_THRESHOLD: int = 15
    BLURRINESS_LAPLACIAN_THRESHOLD: int = 40
    RED_EYE_THRESHOLD: int = 180
    LIGHTING_UNDEREXPOSURE_THRESHOLD: int = 25
    LIGHTING_OVEREXPOSURE_THRESHOLD: int = 240
    LIGHTING_LOW_CONTRAST_THRESHOLD: int = 20

    # Validation settings - Background Analysis
    BACKGROUND_STD_DEV_THRESHOLD: float = 100.0

    # Validation settings - Object Detection
    HOG_PERSON_SCALE_FACTOR: float = 1.1
    HOG_PERSON_MIN_NEIGHBORS: int = 6
    MIN_OBJECT_CONTOUR_AREA_RATIO: float = 0.03

    # Security settings
    ALLOWED_ORIGINS: List[str] = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

    # Processing settings
    MAX_CONCURRENT_PROCESSING: int = int(os.getenv("MAX_CONCURRENT_PROCESSING", "5"))

    # Validation requirements tolerance (percentage)
    REQUIREMENTS_TOLERANCE: float = float(os.getenv("REQUIREMENTS_TOLERANCE", "0.4"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()
