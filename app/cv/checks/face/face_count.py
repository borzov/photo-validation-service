"""
Модуль для проверки количества лиц на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger
from app.cv.checks.face.detector import detect_faces

logger = get_logger(__name__)

class FaceCountCheck(BaseCheck):
    """
    Проверка количества лиц на изображении.
    """
    check_id = "faceCount"
    name = "Face Count Check"
    description = "Checks if the image contains the required number of faces"
    
    default_config = {
        "min_count": 1,
        "max_count": 1,
        "face_confidence_threshold": 0.4
    }

    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку количества лиц на изображении.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            # Обнаружение лиц
            # Используем импортированную функцию detect_faces напрямую
            faces = detect_faces(image)
            
            # Фильтрация лиц по уровню уверенности
            confidence_threshold = self.config["face_confidence_threshold"]
            faces = [face for face in faces if face.get("confidence", 0) > confidence_threshold]
            
            # Количество обнаруженных лиц
            face_count = len(faces)
            
            # Проверка соответствия требованиям
            min_count = self.config["min_count"]
            max_count = self.config["max_count"]
            
            if face_count < min_count:
                status = "FAILED"
                reason = f"Too few faces detected: {face_count} (min: {min_count})"
            elif face_count > max_count:
                status = "FAILED"
                reason = f"Too many faces detected: {face_count} (max: {max_count})"
            else:
                status = "PASSED"
                reason = None
            
            # Сохраняем информацию о лицах в контексте для использования в других проверках
            if context is not None:
                # Если есть хотя бы одно лицо, сохраняем первое (или единственное) лицо
                if faces:
                    context["face"] = faces[0]
                context["faces"] = faces
            
            # Формируем детали для ответа
            details = {
                "count": face_count,
                "required_min": min_count,
                "required_max": max_count,
                "face_confidences": [round(face.get("confidence", 0), 2) for face in faces]
            }
            
            logger.info(f"Face count check: {face_count} faces detected, status: {status}")
            
            return {
                "status": status,
                "reason": reason,
                "details": details
            }
            
        except Exception as e:
            logger.error(f"Error during face count check: {e}")
            return {
                "status": "FAILED",
                "reason": f"Face detection error: {str(e)}",
                "details": {"error": str(e)}
            }