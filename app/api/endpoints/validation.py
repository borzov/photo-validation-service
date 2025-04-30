from typing import Any
from fastapi import APIRouter, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
import uuid
import cv2
import numpy as np
from datetime import datetime
import os
import threading
import time

from app.api.models.validation import ValidationResponse, ValidationResult
from app.db.repositories import ValidationRequestRepository
from app.storage.client import storage_client
from app.core.config import settings
from app.core.exceptions import FileValidationError, StorageError
from app.core.logging import get_logger
from app.cv import face_detection, quality_analysis, background_analysis, object_detection

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
        
        # Запуск обработки в отдельном потоке
        threading.Thread(
            target=process_image,
            args=(request_id, file_path),
            daemon=True
        ).start()
        
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


def process_image(request_id: str, file_path: str) -> None:
    """
    Функция для обработки и валидации изображения
    """
    logger.info(f"Starting image processing for request: {request_id}")
    
    start_time = time.time()  # Начинаем отсчет времени
    
    try:
        # Обновление статуса в БД
        ValidationRequestRepository.update_status(request_id, "PROCESSING")
        
        # Получение изображения из хранилища
        image_bytes = storage_client.get_file(file_path)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise Exception("Failed to decode image")
        
        # Инициализация результатов проверок
        checks = []
        overall_status = "APPROVED"  # Изначально предполагаем, что фото валидно
        issues = []
        
        # Проверка формата и размера файла (уже выполнена на уровне API)
        checks.append({
            "check": "fileFormat",
            "status": "PASSED",
            "details": "jpeg"
        })
        
        checks.append({
            "check": "fileSize",
            "status": "PASSED",
            "details": f"{len(image_bytes) // 1024}KB"
        })
        
        # Технические проверки
        # 1. Проверка размеров
        height, width = image.shape[:2]
        if width < settings.MIN_IMAGE_WIDTH or height < settings.MIN_IMAGE_HEIGHT:
            checks.append({
                "check": "dimensions",
                "status": "FAILED",
                "reason": "Image dimensions too small",
                "details": f"{width}x{height}px"
            })
            issues.append("DIMENSIONS_TOO_SMALL")
            overall_status = "REJECTED"
        else:
            checks.append({
                "check": "dimensions",
                "status": "PASSED",
                "details": f"{width}x{height}px"
            })
        
        # 2. Проверка цветности
        if len(image.shape) < 3 or image.shape[2] < 3:
            checks.append({
                "check": "colorMode",
                "status": "FAILED",
                "reason": "Image is not in color",
                "details": "Grayscale or binary"
            })
            issues.append("NOT_COLOR_IMAGE")
            overall_status = "REJECTED"
        else:
            # Дополнительная проверка на черно-белое изображение
            is_grayscale = quality_analysis.is_grayscale(image)
            if is_grayscale:
                checks.append({
                    "check": "colorMode",
                    "status": "FAILED",
                    "reason": "Image appears to be grayscale",
                    "details": "Low color variance"
                })
                issues.append("LOW_COLOR_VARIANCE")
                overall_status = "REJECTED"
            else:
                checks.append({
                    "check": "colorMode",
                    "status": "PASSED",
                    "details": "Color"
                })
        
        # CV анализ (если базовые проверки пройдены)
        if overall_status != "REJECTED":
            # 3. Детекция лиц
            faces = face_detection.detect_faces(image)
            
            if len(faces) == 0:
                checks.append({
                    "check": "faceCount",
                    "status": "FAILED",
                    "reason": "No faces detected",
                    "details": "0 faces detected"
                })
                issues.append("NO_FACE_DETECTED")
                overall_status = "REJECTED"
            elif len(faces) > 1:
                checks.append({
                    "check": "faceCount",
                    "status": "FAILED",
                    "reason": "Multiple faces detected",
                    "details": f"{len(faces)} faces detected"
                })
                issues.append("MULTIPLE_FACES_DETECTED")
                overall_status = "REJECTED"
            else:
                checks.append({
                    "check": "faceCount",
                    "status": "PASSED",
                    "details": "1 face detected"
                })
                
                # Получаем единственное лицо
                face = faces[0]
                
                # 4. Положение и размер лица
                face_position_result = face_detection.check_face_position(image, face)
                if not face_position_result["is_valid"]:
                    checks.append({
                        "check": "facePosition",
                        "status": "FAILED",
                        "reason": face_position_result["reason"],
                        "details": face_position_result["details"]
                    })
                    issues.append(f"FACE_POSITION_{face_position_result['reason'].upper().replace(' ', '_')}")
                    overall_status = "REJECTED"
                else:
                    checks.append({
                        "check": "facePosition",
                        "status": "PASSED",
                        "details": face_position_result["details"]
                    })
                
                # 5. Поза лица (анфас)
                face_pose_result = face_detection.check_face_pose(face)
                if not face_pose_result["is_valid"]:
                    checks.append({
                        "check": "facePose",
                        "status": "FAILED",
                        "reason": face_pose_result["reason"],
                        "details": face_pose_result["details"]
                    })
                    issues.append(f"FACE_POSE_{face_pose_result['reason'].upper().replace(' ', '_')}")
                    overall_status = "REJECTED"
                else:
                    checks.append({
                        "check": "facePose",
                        "status": "PASSED",
                        "details": face_pose_result["details"]
                    })
                
                # 6. Размытость
                blur_result = quality_analysis.check_blurriness(image, face)
                if not blur_result["is_valid"]:
                    checks.append({
                        "check": "blurriness",
                        "status": "FAILED",
                        "reason": blur_result["reason"],
                        "details": blur_result["details"]
                    })
                    issues.append("IMAGE_BLURRY")
                    overall_status = "REJECTED"
                else:
                    checks.append({
                        "check": "blurriness",
                        "status": "PASSED",
                        "details": blur_result["details"]
                    })
                
                # 7. Красные глаза
                red_eye_result = quality_analysis.check_red_eyes(image, face)
                if not red_eye_result["is_valid"]:
                    checks.append({
                        "check": "redEye",
                        "status": "FAILED",
                        "reason": red_eye_result["reason"],
                        "details": red_eye_result["details"]
                    })
                    issues.append("RED_EYE_DETECTED")
                    overall_status = "REJECTED"
                else:
                    checks.append({
                        "check": "redEye",
                        "status": "PASSED",
                        "details": red_eye_result["details"]
                    })
                
                # 8. Анализ фона
                background_result = background_analysis.analyze_background(image, face)
                if background_result["status"] == "NEEDS_REVIEW":
                    checks.append({
                        "check": "background",
                        "status": "NEEDS_REVIEW",
                        "reason": background_result["reason"],
                        "details": background_result["details"]
                    })
                    issues.append(f"BACKGROUND_{background_result['reason'].upper().replace(' ', '_')}")
                    if overall_status == "APPROVED":  # Не перезаписываем REJECTED
                        overall_status = "MANUAL_REVIEW"
                elif background_result["status"] == "FAILED":
                    checks.append({
                        "check": "background",
                        "status": "FAILED",
                        "reason": background_result["reason"],
                        "details": background_result["details"]
                    })
                    issues.append(f"BACKGROUND_{background_result['reason'].upper().replace(' ', '_')}")
                    overall_status = "REJECTED"
                else:
                    checks.append({
                        "check": "background",
                        "status": "PASSED",
                        "details": background_result["details"]
                    })
                
                # 9. Детекция посторонних объектов/людей
                objects_result = object_detection.detect_objects(image, face)
                if objects_result["status"] == "FAILED":
                    checks.append({
                        "check": "extraneousObjects",
                        "status": "FAILED",
                        "reason": objects_result["reason"],
                        "details": objects_result["details"]
                    })
                    issues.append("EXTRANEOUS_OBJECTS_DETECTED")
                    overall_status = "REJECTED"
                else:
                    checks.append({
                        "check": "extraneousObjects",
                        "status": "PASSED",
                        "details": objects_result["details"]
                    })
                
                # 10. Аксессуары
                accessories_result = object_detection.detect_accessories(image, face)
                if accessories_result["accessories"]:
                    checks.append({
                        "check": "accessories",
                        "status": "NEEDS_REVIEW",
                        "reason": f"{', '.join(accessories_result['accessories'])} detected",
                        "details": accessories_result["accessories"]
                    })
                    for acc in accessories_result["accessories"]:
                        issues.append(f"ACCESSORIES_{acc.upper()}_DETECTED")
                    if overall_status == "APPROVED":  # Не перезаписываем REJECTED
                        overall_status = "MANUAL_REVIEW"
                else:
                    checks.append({
                        "check": "accessories",
                        "status": "PASSED",
                        "details": "No accessories detected"
                    })
                
                # 11. Освещение
                lighting_result = quality_analysis.check_lighting(image, face)
                if lighting_result["status"] == "NEEDS_REVIEW":
                    checks.append({
                        "check": "lighting",
                        "status": "NEEDS_REVIEW",
                        "reason": lighting_result["reason"],
                        "details": lighting_result["details"]
                    })
                    issues.append(f"LIGHTING_{lighting_result['reason'].upper().replace(' ', '_')}")
                    if overall_status == "APPROVED":  # Не перезаписываем REJECTED
                        overall_status = "MANUAL_REVIEW"
                else:
                    checks.append({
                        "check": "lighting",
                        "status": "PASSED",
                        "details": lighting_result["details"]
                    })
        
        # Вычисляем время обработки
        processing_time = time.time() - start_time
        
        # Сохранение результатов в БД
        ValidationRequestRepository.update_result(
            request_id=request_id,
            status="COMPLETED",
            overall_status=overall_status,
            checks=checks,
            issues=issues,
            processed_at=datetime.utcnow(),
            processing_time=processing_time
        )
        
        # Удаление файла из хранилища
        storage_client.delete_file(file_path)
        
        logger.info(f"Completed processing for request: {request_id}, status: {overall_status}, time: {processing_time:.2f}s")
        
    except Exception as e:
        # Вычисляем время до ошибки
        processing_time = time.time() - start_time
        
        logger.error(f"Error processing image for request: {request_id}: {str(e)}, time: {processing_time:.2f}s")
        # Обновление статуса в случае ошибки
        ValidationRequestRepository.update_error(
            request_id=request_id,
            error_message=str(e),
            processing_time=processing_time
        )
        # Попытка удалить файл
        try:
            storage_client.delete_file(file_path)
        except:
            pass
