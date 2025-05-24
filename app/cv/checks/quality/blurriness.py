"""
Проверка размытости изображения.
"""
import cv2
import numpy as np
from typing import Dict, Any
import math
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger

logger = get_logger(__name__)

class BlurrinessCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка размытости изображения в области лица с использованием дисперсии Лапласиана.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="blurriness",
            display_name="Проверка размытости",
            description="Проверяет размытость изображения в области лица с использованием дисперсии Лапласиана",
            category="image_quality",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="laplacian_threshold",
                    type="int",
                    default=40,
                    description="Минимальное значение дисперсии Лапласиана для считания изображения четким",
                    min_value=10,
                    max_value=200,
                    required=True
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    # Инициализация и run() метод унаследованы из StandardCheckMixin
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform blurriness check on the image.
        
        Args:
            image: Image to check
            context: Context with previous check results, should contain face["bbox"]
            
        Returns:
            Check results
        """
        # Проверяем контекст лица с bbox
        context_error = self._validate_face_bbox_context(context, "blurriness")
        if context_error:
            return context_error

        # Get face region from context
        x, y, width, height = context["face"]["bbox"]
        face_region = image[y:y+height, x:x+width]

        if face_region.size == 0:
            logger.warning("Область лица пуста, пропускаем проверку размытости")
            return {
                "check": "blurriness",
                "status": "NEEDS_REVIEW",
                "reason": "Пустая область лица",
                "details": {"laplacian_variance": None}
            }
            
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian and its variance
            laplacian_var_np = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Check for NaN or Inf
            if laplacian_var_np is None or math.isnan(laplacian_var_np):
                laplacian_var = 0.0
                logger.warning("Дисперсия Лапласиана равна NaN, принимаем за 0.0 для проверки размытости")
            else:
                laplacian_var = float(laplacian_var_np)
                
            # Get threshold from configuration
            threshold = self.parameters["laplacian_threshold"]
            details = {
                "laplacian_variance": round(laplacian_var, 2),
                "threshold": threshold,
                "parameters_used": self.parameters
            }
            
            # Check blurriness
            if laplacian_var < threshold:
                logger.info(f"Лицо размыто: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
                return {
                    "check": "blurriness",
                    "status": "FAILED",
                    "reason": f"Изображение размыто (значение Лапласиана: {laplacian_var:.2f} < {threshold})",
                    "details": details
                }
            else:
                logger.info(f"Лицо четкое: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
                return {
                    "check": "blurriness",
                    "status": "PASSED",
                    "details": details
                }
        except Exception as e:
            return self._create_error_result("blurriness", e)