from typing import Any
from fastapi import APIRouter, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.responses import JSONResponse
import uuid
import cv2
import numpy as np
from datetime import datetime
import os
import time
import asyncio

from app.api.models.validation import ValidationResponse, ValidationResult
from app.db.repositories import ValidationRequestRepository
from app.storage.client import storage_client
from app.core.config import settings
from app.core.exceptions import FileValidationError, StorageError
from app.core.logging import get_logger
from app.worker.tasks import add_processing_task

logger = get_logger(__name__)

router = APIRouter()

@router.post(
    "/validate",
    response_model=ValidationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Загрузить фото для валидации",
    description="Загружает фотографию и инициирует процесс валидации"
)
async def validate_photo(
    file: UploadFile = File(..., description="JPEG фотография для валидации")
) -> Any:
    """
    Эндпоинт для загрузки фотографии на валидацию
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Received validation request: {request_id}")
    
    try:
        # Проверка формата файла
        if not file.filename.lower().endswith(('.jpg', '.jpeg')):
            raise FileValidationError(
                message="Only JPG/JPEG files are allowed",
                code="INVALID_FILE_FORMAT"
            )
        
        # Чтение содержимого файла
        content = await file.read()
        
        # Проверка размера файла
        if len(content) > settings.MAX_FILE_SIZE_BYTES:
            raise FileValidationError(
                message=f"File size exceeds {settings.MAX_FILE_SIZE_BYTES // 1024} KB limit",
                code="FILE_TOO_LARGE"
            )
        
        # Сохранение файла в хранилище
        file_path = f"{request_id}.jpg"
        storage_client.save_file(file_path, content)
        
        # Создание записи в БД
        ValidationRequestRepository.create(request_id)
        
        # Добавление задачи в очередь обработки
        await add_processing_task(request_id, file_path)
        
        return {"requestId": request_id}
    
    except FileValidationError as e:
        logger.warning(f"File validation error: {str(e)}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    
    except StorageError as e:
        logger.error(f"Storage error: {str(e)}", extra={"request_id": request_id})
        # Обновляем статус в БД в случае ошибки
        ValidationRequestRepository.update_error(
            request_id, error_message=f"Storage error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file to storage"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", extra={"request_id": request_id})
        # Обновляем статус в БД в случае ошибки
        ValidationRequestRepository.update_error(
            request_id, error_message=f"Unexpected error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get(
    "/results/{request_id}",
    response_model=ValidationResult,
    summary="Получить результат валидации",
    description="Возвращает статус и результат валидации по ID запроса"
)
async def get_validation_result(
    request_id: str
) -> Any:
    """
    Эндпоинт для получения результата валидации по ID запроса
    """
    logger.info(f"Retrieving results for request: {request_id}")
    
    try:
        # Получение запроса из БД
        db_request = ValidationRequestRepository.get_by_id(request_id)
        
        if not db_request:
            logger.warning(f"Request not found: {request_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )
        
        # Преобразование в модель ответа
        # Важно: создаем копию данных, а не используем сам объект
        result = db_request.to_dict()
        
        # Адаптация ключей для соответствия модели Pydantic (camelCase)
        if "overall_status" in result:
            result["overallStatus"] = result.pop("overall_status")
        if "created_at" in result:
            result["createdAt"] = result.pop("created_at")
        if "processed_at" in result:
            result["processedAt"] = result.pop("processed_at")
        if "error_message" in result:
            result["errorMessage"] = result.pop("error_message")
        if "request_id" in result:
            result["requestId"] = result.pop("request_id")
        if "processing_time" in result:
            result["processingTime"] = result.pop("processing_time")
        
        return result
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}", extra={"request_id": request_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation results"
        )
