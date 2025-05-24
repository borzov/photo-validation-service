from sqlalchemy import Column, String, Text, TIMESTAMP, Float, Integer, create_engine, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from app.core.config import settings
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import os

Base = declarative_base()

# Helper function to determine JSON type based on database
def get_json_type():
    """
    Returns appropriate JSON type based on database dialect.
    JSONB for PostgreSQL, JSON for SQLite and others.
    """
    if "postgresql" in settings.DATABASE_URL.lower():
        return JSONB
    else:
        return JSON

class ValidationRequest(Base):
    """
    Model for storing validation requests and their results.
    """
    __tablename__ = "validation_requests"
    
    request_id = Column(String, primary_key=True, index=True)
    filename = Column(String, nullable=True)  # Имя файла
    file_size = Column(Integer, nullable=True)  # Размер файла в байтах
    status = Column(String, nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    overall_status = Column(String, nullable=True)  # APPROVED, REJECTED, MANUAL_REVIEW
    checks = Column(get_json_type(), nullable=True)  # Dynamic JSON type
    issues = Column(get_json_type(), nullable=True)  # Dynamic JSON type
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    processed_at = Column(TIMESTAMP, nullable=True)
    processing_time = Column(Float, nullable=True)  # Processing time in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converts record to dictionary.
        """
        result = {
            "request_id": self.request_id,
            "filename": self.filename,
            "file_size": self.file_size,
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

def init_db():
    """Initialize database and create tables."""
    engine = create_engine(
        settings.DATABASE_URL,
        # Additional parameters for PostgreSQL
        pool_pre_ping=True,  # Check connection before use
        pool_recycle=3600,   # Reconnect every hour
        pool_size=5,         # Connection pool size
        max_overflow=10      # Max additional connections
    )
    Base.metadata.create_all(engine)
    return engine
