from sqlalchemy import Column, String, Text, TIMESTAMP, Float, create_engine, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from app.core.config import settings
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import os

Base = declarative_base()

class ValidationRequest(Base):
    """
    Модель для хранения запросов на валидацию и их результатов
    """
    __tablename__ = "validation_requests"
    
    request_id = Column(String, primary_key=True, index=True)
    status = Column(String, nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    overall_status = Column(String, nullable=True)  # APPROVED, REJECTED, MANUAL_REVIEW
    checks = Column(JSONB, nullable=True)  # Используем JSONB вместо JSON
    issues = Column(JSONB, nullable=True)  # Используем JSONB вместо JSON
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    processed_at = Column(TIMESTAMP, nullable=True)
    processing_time = Column(Float, nullable=True)  # Время обработки в секундах
    
    # Опционально: индексы для JSONB-полей
    __table_args__ = (
        Index('ix_validation_requests_checks_gin', checks, postgresql_using='gin'),
        Index('ix_validation_requests_issues_gin', issues, postgresql_using='gin'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразует запись в словарь
        """
        result = {
            "request_id": self.request_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "processed_at": self.processed_at.isoformat() if isinstance(self.processed_at, datetime) else self.processed_at,
            "processing_time": self.processing_time
        }
        
        if self.status == "COMPLETED":
            result["overall_status"] = self.overall_status
            result["checks"] = self.checks
            
            if self.overall_status != "APPROVED":
                result["issues"] = self.issues
        
        if self.status == "FAILED":
            result["error_message"] = self.error_message
            
        return result

# Функция для инициализации базы данных
def init_db():
    """Инициализация базы данных и создание таблиц"""
    engine = create_engine(
        settings.DATABASE_URL,
        # Дополнительные параметры для PostgreSQL
        pool_pre_ping=True,  # Проверка соединения перед использованием
        pool_recycle=3600,   # Переподключение каждый час
        pool_size=5,         # Размер пула соединений
        max_overflow=10      # Максимальное количество дополнительных соединений
    )
    Base.metadata.create_all(engine)
    return engine
