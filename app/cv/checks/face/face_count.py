"""
Модуль для подсчета количества лиц на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.cv.checks.face.detector import detect_faces
from app.core.logging import get_logger

logger = get_logger(__name__)

class FaceCountCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка количества лиц на изображении.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="face_count",
            display_name="Количество лиц",
            description="Проверяет, что изображение содержит требуемое количество лиц",
            category="face_detection",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="min_count",
                    type="int",
                    default=1,
                    description="Минимальное количество лиц",
                    min_value=0,
                    max_value=10,
                    required=True
                ),
                CheckParameter(
                    name="max_count",
                    type="int",
                    default=1,
                    description="Максимальное количество лиц",
                    min_value=1,
                    max_value=10,
                    required=True
                ),
                CheckParameter(
                    name="face_confidence_threshold",
                    type="float",
                    default=0.45,
                    description="Порог уверенности для детекции лиц",
                    min_value=0.1,
                    max_value=0.9,
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    # Инициализация и run() метод унаследованы из StandardCheckMixin
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку количества лиц на изображении.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            # Используем детектор лиц
            faces = detect_faces(image, confidence_threshold=self.parameters["face_confidence_threshold"])
            face_count = len(faces)
            
            # Сохраняем результаты детекции лиц в контексте для других проверок
            if context is not None and faces:
                # Берем первое лицо как основное (для проверок, которые работают с одним лицом)
                main_face = faces[0]
                context["face"] = {
                    "bbox": main_face.get("bbox"),
                    "landmarks": main_face.get("landmarks"),
                    "confidence": main_face.get("confidence")
                }
                # Сохраняем все лица
                context["faces"] = faces
            
            min_count = self.parameters["min_count"]
            max_count = self.parameters["max_count"]
            
            # Формируем детали
            face_details = []
            for i, face in enumerate(faces):
                bbox = face.get("bbox", [0, 0, 0, 0])
                confidence = face.get("confidence", 0.0)
                face_details.append({
                    "id": i + 1,
                    "bbox": bbox,
                    "confidence": float(confidence),
                    "area": bbox[2] * bbox[3] if len(bbox) >= 4 else 0
                })
            
            details = {
                "face_count": face_count,
                "min_count_required": min_count,
                "max_count_allowed": max_count,
                "faces": face_details,
                "confidence_threshold": self.parameters["face_confidence_threshold"],
                "parameters_used": self.parameters
            }
            
            # Определяем результат
            if face_count < min_count:
                return {
                    "check": "face_count",
                    "status": "FAILED",
                    "reason": f"Недостаточно лиц: найдено {face_count}, требуется минимум {min_count}",
                    "details": details
                }
            elif face_count > max_count:
                return {
                    "check": "face_count",
                    "status": "FAILED",
                    "reason": f"Слишком много лиц: найдено {face_count}, максимум {max_count}",
                    "details": details
                }
            else:
                return {
                    "check": "face_count",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            return self._create_error_result("face_count", e)