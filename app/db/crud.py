"""
CRUD операции для базы данных
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from app.db.repositories import ValidationRequestRepository


class ValidationRequestCRUD:
    """CRUD операции для запросов валидации"""
    
    @staticmethod
    def create(request_id: str, file_path: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Создать новый запрос валидации"""
        return ValidationRequestRepository.create(request_id, file_path, settings)
    
    @staticmethod
    def get_by_id(request_id: str) -> Optional[Dict[str, Any]]:
        """Получить запрос по ID"""
        return ValidationRequestRepository.get_by_id(request_id)
    
    @staticmethod
    def update_status(request_id: str, status: str) -> bool:
        """Обновить статус запроса"""
        return ValidationRequestRepository.update_status(request_id, status)
    
    @staticmethod
    def update_result(
        request_id: str,
        status: str,
        overall_status: str,
        checks: List[Dict[str, Any]],
        issues: List[str],
        processed_at: datetime,
        processing_time: float
    ) -> bool:
        """Обновить результат валидации"""
        return ValidationRequestRepository.update_result(
            request_id=request_id,
            status=status,
            overall_status=overall_status,
            checks=checks,
            issues=issues,
            processed_at=processed_at,
            processing_time=processing_time
        )
    
    @staticmethod
    def update_error(
        request_id: str,
        error_message: str,
        processing_time: float,
        status: str = "FAILED",
        checks: Optional[List[Dict[str, Any]]] = None,
        issues: Optional[List[str]] = None,
        overall_status: str = "FAILED"
    ) -> bool:
        """Обновить запрос с ошибкой"""
        return ValidationRequestRepository.update_error(
            request_id=request_id,
            error_message=error_message,
            processing_time=processing_time,
            status=status,
            checks=checks,
            issues=issues,
            overall_status=overall_status
        )


# Экспортируем для совместимости
validation_request_crud = ValidationRequestCRUD() 