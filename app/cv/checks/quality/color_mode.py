"""
Модуль для проверки цветового режима изображения.
"""
import cv2
import numpy as np
from typing import Dict, Any
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.core.logging import get_logger
from app.cv.checks.mixins import StandardCheckMixin

logger = get_logger(__name__)

class ColorModeCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка цветности изображения (цветное или черно-белое).
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="color_mode",
            display_name="Проверка цветового режима",
            description="Проверяет, является ли изображение цветным или черно-белым",
            category="image_quality",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="grayscale_saturation_threshold",
                    type="int",
                    default=15,
                    description="Порог насыщенности для определения черно-белого изображения",
                    min_value=5,
                    max_value=50,
                    required=True
                ),
                CheckParameter(
                    name="require_color",
                    type="bool",
                    default=True,
                    description="Требовать цветное изображение (если False, любое принимается)",
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку цветового режима изображения.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            # Конвертируем в HSV для анализа насыщенности
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Извлекаем канал насыщенности (S)
            saturation = hsv[:, :, 1]
            
            # Вычисляем среднюю насыщенность
            mean_saturation = np.mean(saturation)
            
            threshold = self.parameters["grayscale_saturation_threshold"]
            require_color = self.parameters["require_color"]
            
            # Определяем, является ли изображение цветным
            is_color = mean_saturation > threshold
            
            details = {
                "mean_saturation": float(mean_saturation),
                "threshold": threshold,
                "is_color": is_color,
                "parameters_used": self.parameters
            }
            
            # Проверяем соответствие требованиям
            if require_color and not is_color:
                return {
                    "check": "color_mode",
                    "status": "FAILED",
                    "reason": f"Изображение черно-белое (насыщенность: {mean_saturation:.1f} <= {threshold})",
                    "details": details
                }
            elif not require_color or is_color:
                return {
                    "check": "color_mode", 
                    "status": "PASSED",
                    "details": details
                }
            else:
                return {
                    "check": "color_mode",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Ошибка при проверке цветового режима: {e}")
            return {
                "check": "color_mode",
                "status": "NEEDS_REVIEW",
                "reason": f"Ошибка при проверке цветового режима: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }