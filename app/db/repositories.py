from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from app.core.config import settings
from app.db.models import ValidationRequest
from app.core.logging import get_logger

logger = get_logger(__name__)

# Создаем соединение с базой данных
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session():
    """Контекстный менеджер для сессий SQLAlchemy"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

class ValidationRequestRepository:
    """
    Репозиторий для работы с запросами на валидацию
    """
    @staticmethod
    def create(request_id: str, status: str = "PENDING") -> ValidationRequest:
        """
        Создает новый запрос на валидацию
        """
        with get_db_session() as db:
            db_request = ValidationRequest(
                request_id=request_id,
                status=status,
                created_at=datetime.utcnow()
            )
            
            db.add(db_request)
            db.flush()
            
            # Создаем копию данных, чтобы вернуть их после закрытия сессии
            result_dict = db_request.to_dict()
            
            logger.info(f"Created validation request with ID: {request_id}")
            
            # Создаем новый объект ValidationRequest с теми же данными
            result = ValidationRequest()
            for key, value in result_dict.items():
                setattr(result, key, value)
                
            return result
    
    @staticmethod
    def get_by_id(request_id: str) -> Optional[ValidationRequest]:
        """
        Получает запрос на валидацию по ID
        """
        with get_db_session() as db:
            db_request = db.query(ValidationRequest).filter(
                ValidationRequest.request_id == request_id
            ).first()
            
            if not db_request:
                return None
                
            # Создаем копию данных
            result_dict = db_request.to_dict()
            
            # Создаем новый объект ValidationRequest с теми же данными
            result = ValidationRequest()
            for key, value in result_dict.items():
                setattr(result, key, value)
                
            return result
    
    @staticmethod
    def update_status(request_id: str, status: str) -> Optional[ValidationRequest]:
        """
        Обновляет статус запроса
        """
        with get_db_session() as db:
            db_request = db.query(ValidationRequest).filter(
                ValidationRequest.request_id == request_id
            ).first()
            
            if not db_request:
                logger.warning(f"Request with ID {request_id} not found for status update")
                return None
            
            db_request.status = status
            db.flush()
            
            # Создаем копию данных
            result_dict = db_request.to_dict()
            
            logger.info(f"Updated status for request {request_id} to {status}")
            
            # Создаем новый объект ValidationRequest с теми же данными
            result = ValidationRequest()
            for key, value in result_dict.items():
                setattr(result, key, value)
                
            return result
    
    @staticmethod
    def update_result(
        request_id: str,
        status: str,
        overall_status: str,
        checks: List[Dict[str, Any]],
        issues: List[str],
        processed_at: datetime,
        processing_time: float = None
    ) -> Optional[ValidationRequest]:
        """
        Обновляет результат валидации
        """
        with get_db_session() as db:
            db_request = db.query(ValidationRequest).filter(
                ValidationRequest.request_id == request_id
            ).first()
            
            if not db_request:
                logger.warning(f"Request with ID {request_id} not found for result update")
                return None
            
            db_request.status = status
            db_request.overall_status = overall_status
            db_request.checks = checks
            db_request.issues = issues
            db_request.processed_at = processed_at
            db_request.processing_time = processing_time
            
            db.flush()
            
            # Создаем копию данных
            result_dict = db_request.to_dict()
            
            logger.info(f"Updated result for request {request_id}, overall status: {overall_status}, processing time: {processing_time:.2f}s" if processing_time else f"Updated result for request {request_id}, overall status: {overall_status}")
            
            # Создаем новый объект ValidationRequest с теми же данными
            result = ValidationRequest()
            for key, value in result_dict.items():
                setattr(result, key, value)
                
            return result
    
    @staticmethod
    def update_error(
        request_id: str,
        status: str = "FAILED",
        error_message: str = "Unknown error",
        checks: List[Dict[str, Any]] = None,
        issues: List[str] = None,
        overall_status: str = None,
        processing_time: float = None
    ) -> Optional[ValidationRequest]:
        """
        Обновляет запрос в случае ошибки
        """
        with get_db_session() as db:
            db_request = db.query(ValidationRequest).filter(
                ValidationRequest.request_id == request_id
            ).first()
            
            if not db_request:
                logger.warning(f"Request with ID {request_id} not found for error update")
                return None
            
            db_request.status = status
            db_request.error_message = error_message
            db_request.processed_at = datetime.utcnow()
            db_request.checks = checks
            db_request.issues = issues
            db_request.overall_status = overall_status
            db_request.processing_time = processing_time
            
            db.flush()
            
            # Создаем копию данных
            result_dict = db_request.to_dict()
            
            logger.error(f"Updated error for request {request_id}: {error_message}, processing time: {processing_time:.2f}s" if processing_time else f"Updated error for request {request_id}: {error_message}")
            
            # Создаем новый объект ValidationRequest с теми же данными
            result = ValidationRequest()
            for key, value in result_dict.items():
                setattr(result, key, value)
                
            return result
