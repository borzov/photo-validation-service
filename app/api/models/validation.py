from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class ValidationResponse(BaseModel):
    """
    Модель ответа при загрузке фото на валидацию
    """
    requestId: str = Field(..., description="Уникальный идентификатор запроса")

class CheckResult(BaseModel):
    """
    Результат отдельной проверки
    """
    check: str = Field(..., description="Название проверки")
    status: str = Field(..., description="Статус проверки (PASSED, FAILED, NEEDS_REVIEW)")
    reason: Optional[str] = Field(None, description="Причина неуспешной проверки")
    details: Any = Field(..., description="Детали проверки")

class ValidationResult(BaseModel):
    """
    Модель результата валидации
    """
    requestId: str = Field(..., description="Уникальный идентификатор запроса")
    status: str = Field(..., description="Статус обработки (PENDING, PROCESSING, COMPLETED, FAILED)")
    overallStatus: Optional[str] = Field(None, description="Итоговый статус валидации (APPROVED, REJECTED, MANUAL_REVIEW)")
    processedAt: Optional[datetime] = Field(None, description="Время завершения обработки")
    processingTime: Optional[float] = Field(None, description="Время обработки в секундах")
    checks: Optional[List[CheckResult]] = Field(None, description="Результаты отдельных проверок")
    issues: Optional[List[str]] = Field(None, description="Коды обнаруженных проблем")
    errorMessage: Optional[str] = Field(None, description="Сообщение об ошибке (если status=FAILED)")

class ErrorResponse(BaseModel):
    """
    Модель ответа с ошибкой
    """
    detail: str = Field(..., description="Описание ошибки")
    code: Optional[str] = Field(None, description="Код ошибки")
