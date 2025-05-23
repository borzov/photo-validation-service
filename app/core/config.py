# ФАЙЛ: app/core/config.py

import os
from typing import Optional, List
import logging

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
    MIN_IMAGE_WIDTH: int = max(100, int(os.getenv("MIN_IMAGE_WIDTH", "400")))
    MIN_IMAGE_HEIGHT: int = max(100, int(os.getenv("MIN_IMAGE_HEIGHT", "500")))
    MAX_FILE_SIZE_BYTES: int = min(10 * 1024 * 1024, max(100 * 1024, int(os.getenv("MAX_FILE_SIZE_BYTES", str(1 * 1024 * 1024)))))  # Ограничение: 100KB - 10MB

    # Validation settings - Face Detection & Position
    FACE_CONFIDENCE_THRESHOLD: float = max(0.1, min(0.9, float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.4"))))
    FACE_MIN_AREA_RATIO: float = max(0.01, min(0.5, float(os.getenv("FACE_MIN_AREA_RATIO", "0.05"))))
    FACE_MAX_AREA_RATIO: float = max(0.5, min(1.0, float(os.getenv("FACE_MAX_AREA_RATIO", "0.8"))))
    FACE_CENTER_TOLERANCE: float = max(0.1, min(1.0, float(os.getenv("FACE_CENTER_TOLERANCE", "0.4"))))

    # Validation settings - Face Pose (degrees)
    MAX_FACE_YAW: float = max(5.0, min(90.0, float(os.getenv("MAX_FACE_YAW", "25.0"))))
    MAX_FACE_PITCH: float = max(5.0, min(90.0, float(os.getenv("MAX_FACE_PITCH", "25.0"))))
    MAX_FACE_ROLL: float = max(5.0, min(90.0, float(os.getenv("MAX_FACE_ROLL", "25.0"))))

    # Validation settings - Quality Analysis
    GRAYSCALE_SATURATION_THRESHOLD: int = max(5, min(50, int(os.getenv("GRAYSCALE_SATURATION_THRESHOLD", "15"))))
    BLURRINESS_LAPLACIAN_THRESHOLD: int = max(10, min(200, int(os.getenv("BLURRINESS_LAPLACIAN_THRESHOLD", "40"))))
    RED_EYE_THRESHOLD: int = max(100, min(255, int(os.getenv("RED_EYE_THRESHOLD", "180"))))
    LIGHTING_UNDEREXPOSURE_THRESHOLD: int = max(5, min(100, int(os.getenv("LIGHTING_UNDEREXPOSURE_THRESHOLD", "25"))))
    LIGHTING_OVEREXPOSURE_THRESHOLD: int = max(200, min(255, int(os.getenv("LIGHTING_OVEREXPOSURE_THRESHOLD", "240"))))
    LIGHTING_LOW_CONTRAST_THRESHOLD: int = max(5, min(100, int(os.getenv("LIGHTING_LOW_CONTRAST_THRESHOLD", "20"))))

    # Validation settings - Background Analysis
    BACKGROUND_STD_DEV_THRESHOLD: float = max(10.0, min(500.0, float(os.getenv("BACKGROUND_STD_DEV_THRESHOLD", "100.0"))))

    # Validation settings - Object Detection
    HOG_PERSON_SCALE_FACTOR: float = max(1.01, min(2.0, float(os.getenv("HOG_PERSON_SCALE_FACTOR", "1.1"))))
    HOG_PERSON_MIN_NEIGHBORS: int = max(1, min(20, int(os.getenv("HOG_PERSON_MIN_NEIGHBORS", "6"))))
    MIN_OBJECT_CONTOUR_AREA_RATIO: float = max(0.001, min(0.5, float(os.getenv("MIN_OBJECT_CONTOUR_AREA_RATIO", "0.03"))))

    # Security settings
    ALLOWED_ORIGINS: List[str] = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]

    # Processing settings
    MAX_CONCURRENT_PROCESSING: int = max(1, min(20, int(os.getenv("MAX_CONCURRENT_PROCESSING", "5"))))

    # Validation requirements tolerance (percentage)
    REQUIREMENTS_TOLERANCE: float = max(0.0, min(1.0, float(os.getenv("REQUIREMENTS_TOLERANCE", "0.4"))))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Дополнительные настройки безопасности
    ALLOWED_MIME_TYPES: List[str] = [
        "image/jpeg", "image/jpg", "image/png", "image/webp", 
        "image/bmp", "image/tiff", "image/x-ms-bmp"
    ]
    MAX_IMAGE_PIXELS: int = max(100000, min(50000000, int(os.getenv("MAX_IMAGE_PIXELS", "25000000"))))
    
    def __post_init__(self):
        """Валидация настроек после инициализации"""
        # Проверяем корректность LOG_LEVEL
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.LOG_LEVEL not in valid_log_levels:
            self.LOG_LEVEL = "INFO"
            
        # Проверяем корректность путей
        if not os.path.isabs(self.STORAGE_PATH):
            self.STORAGE_PATH = os.path.abspath(self.STORAGE_PATH)
            
        # Создаем директорию для хранения, если её нет
        os.makedirs(self.STORAGE_PATH, exist_ok=True)

settings = Settings()
# Вызываем валидацию
settings.__post_init__()
