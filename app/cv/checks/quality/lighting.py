"""
Модуль для проверки качества освещения изображения.
"""
import cv2
import numpy as np
from typing import Dict, Any
import math
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger

logger = get_logger(__name__)

class LightingCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка качества освещения изображения.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="lighting",
            display_name="Проверка освещения",
            description="Проверяет качество освещения (недоэкспонирование, переэкспонирование, низкий контраст)",
            category="image_quality",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="underexposure_threshold",
                    type="int",
                    default=25,
                    description="Порог для недоэкспонирования (средняя яркость)",
                    min_value=5,
                    max_value=100,
                    required=True
                ),
                CheckParameter(
                    name="overexposure_threshold",
                    type="int",
                    default=240,
                    description="Порог для переэкспонирования (средняя яркость)",
                    min_value=200,
                    max_value=255,
                    required=True
                ),
                CheckParameter(
                    name="low_contrast_threshold",
                    type="int",
                    default=20,
                    description="Порог для низкого контраста (стандартное отклонение)",
                    min_value=5,
                    max_value=100,
                    required=True
                ),
                CheckParameter(
                    name="shadow_ratio_threshold",
                    type="float",
                    default=0.4,
                    description="Максимальное соотношение темных пикселей",
                    min_value=0.1,
                    max_value=0.8,
                    required=False
                ),
                CheckParameter(
                    name="highlight_ratio_threshold",
                    type="float",
                    default=0.3,
                    description="Максимальное соотношение ярких пикселей",
                    min_value=0.1,
                    max_value=0.8,
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку качества освещения изображения.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            # Convert to grayscale for brightness analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Basic statistics
            mean_brightness = np.mean(gray)
            std_brightness = np.std(gray)
            
            # Analyze dark and bright areas
            total_pixels = gray.size
            dark_pixels = np.sum(gray < 50)
            bright_pixels = np.sum(gray > 200)
            
            shadow_ratio = dark_pixels / total_pixels
            highlight_ratio = bright_pixels / total_pixels
            
            # Get thresholds from parameters
            underexposure_threshold = self.parameters["underexposure_threshold"]
            overexposure_threshold = self.parameters["overexposure_threshold"]
            low_contrast_threshold = self.parameters["low_contrast_threshold"]
            shadow_ratio_threshold = self.parameters["shadow_ratio_threshold"]
            highlight_ratio_threshold = self.parameters["highlight_ratio_threshold"]
            
            details = {
                "mean_brightness": float(mean_brightness),
                "std_brightness": float(std_brightness),
                "shadow_ratio": float(shadow_ratio),
                "highlight_ratio": float(highlight_ratio),
                "thresholds": {
                    "underexposure": underexposure_threshold,
                    "overexposure": overexposure_threshold,
                    "low_contrast": low_contrast_threshold,
                    "shadow_ratio": shadow_ratio_threshold,
                    "highlight_ratio": highlight_ratio_threshold
                },
                "parameters_used": self.parameters
            }
            
            # Check various lighting issues
            issues = []
            
            # Underexposure
            if mean_brightness < underexposure_threshold:
                issues.append(f"Недоэкспонирование (яркость: {mean_brightness:.1f} < {underexposure_threshold})")
            
            # Overexposure
            if mean_brightness > overexposure_threshold:
                issues.append(f"Переэкспонирование (яркость: {mean_brightness:.1f} > {overexposure_threshold})")
            
            # Low contrast
            if std_brightness < low_contrast_threshold:
                issues.append(f"Низкий контраст (σ: {std_brightness:.1f} < {low_contrast_threshold})")
            
            # Too many shadows
            if shadow_ratio > shadow_ratio_threshold:
                issues.append(f"Слишком много теней ({shadow_ratio:.1%} > {shadow_ratio_threshold:.1%})")
            
            # Too many highlights
            if highlight_ratio > highlight_ratio_threshold:
                issues.append(f"Слишком много бликов ({highlight_ratio:.1%} > {highlight_ratio_threshold:.1%})")
            
            # Final result
            if issues:
                return {
                    "check": "lighting",
                    "status": "FAILED",
                    "reason": "; ".join(issues),
                    "details": details
                }
            else:
                return {
                    "check": "lighting",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Ошибка при проверке освещения: {e}")
            return {
                "check": "lighting",
                "status": "NEEDS_REVIEW",
                "reason": f"Ошибка при проверке освещения: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }