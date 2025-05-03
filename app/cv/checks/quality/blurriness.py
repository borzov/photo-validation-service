"""
Проверка размытости изображения.
"""
import cv2
import numpy as np
from typing import Dict, Any
import math
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class BlurrinessCheck(BaseCheck):
    """
    Проверка размытости в области лица с использованием дисперсии Лапласиана.
    """
    check_id = "blurriness"
    name = "Blurriness Check"
    description = "Checks if the face region is blurry using Laplacian variance"
    
    default_config = {
        "laplacian_threshold": 40,  # Минимальное значение дисперсии Лапласиана
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку размытости изображения.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать face["bbox"]
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("Face region not found in context for blurriness check")
            return {
                "status": "SKIPPED",
                "reason": "No face region available",
                "details": {"laplacian_variance": None}
            }
        
        # Получаем область лица из контекста
        x, y, width, height = context["face"]["bbox"]
        face_region = image[y:y+height, x:x+width]
        
        if face_region.size == 0:
            logger.warning("Face region is empty, skipping blurriness check")
            return {
                "status": "NEEDS_REVIEW",
                "reason": "Empty face region",
                "details": {"laplacian_variance": None}
            }
            
        try:
            # Конвертируем в оттенки серого
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            
            # Вычисляем значение Лапласиана и его дисперсию
            laplacian_var_np = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Проверяем на NaN или Inf
            if laplacian_var_np is None or math.isnan(laplacian_var_np):
                laplacian_var = 0.0
                logger.warning("Laplacian variance resulted in NaN, treating as 0.0 for blur check")
            else:
                laplacian_var = float(laplacian_var_np)
                
            # Определяем порог из конфигурации
            threshold = self.config["laplacian_threshold"]
            details = {"laplacian_variance": round(laplacian_var, 2)}
            
            # Проверяем размытость
            if laplacian_var < threshold:
                logger.info(f"Face seems blurry: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
                return {
                    "status": "FAILED",
                    "reason": "Face is blurry",
                    "details": details
                }
            else:
                logger.info(f"Face seems sharp: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
                return {
                    "status": "PASSED",
                    "details": details
                }
        except Exception as e:
            logger.error(f"Error checking blurriness: {e}")
            return {
                "status": "NEEDS_REVIEW",
                "reason": f"Blurriness check failed: {str(e)}",
                "details": {"error": str(e)}
            }