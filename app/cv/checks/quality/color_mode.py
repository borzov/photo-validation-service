"""
Модуль для проверки цветового режима изображения.
"""
import cv2
import numpy as np
from typing import Dict, Any
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class ColorModeCheck(BaseCheck):
    """
    Проверка, является ли изображение цветным или черно-белым.
    """
    check_id = "colorMode"
    name = "Color Mode Check"
    description = "Checks if the image is in color or grayscale"
    
    default_config = {
        "grayscale_saturation_threshold": 15  # Порог насыщенности для определения ч/б изображения
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку цветового режима изображения.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            # Проверяем количество каналов
            if len(image.shape) < 3 or image.shape[2] < 3:
                return {
                    "status": "FAILED",
                    "reason": "Image is not in color (channels < 3)",
                    "details": f"Shape: {image.shape}"
                }
                
            # Для цветного изображения проверяем уровень насыщенности
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            saturation = hsv[:, :, 1]
            
            # Вычисляем среднюю насыщенность
            mean_saturation_np = np.mean(saturation)
            mean_saturation = float(mean_saturation_np)
            
            # Порог из конфигурации
            threshold = self.config["grayscale_saturation_threshold"]
            
            # Определяем, является ли изображение по существу серым
            is_grayscale = mean_saturation < threshold
            
            if is_grayscale:
                logger.info(f"Image appears to be grayscale: mean_saturation={mean_saturation:.2f}, threshold={threshold}")
                return {
                    "status": "FAILED",
                    "reason": "Image appears to be grayscale (low saturation)",
                    "details": f"Mean saturation: {mean_saturation:.2f} (threshold: {threshold})"
                }
            else:
                logger.info(f"Image is in color: mean_saturation={mean_saturation:.2f}, threshold={threshold}")
                return {
                    "status": "PASSED",
                    "details": "Color"
                }
                
        except Exception as e:
            logger.error(f"Error during color mode check: {e}")
            return {
                "status": "FAILED",
                "reason": f"Color mode check error: {str(e)}",
                "details": {"error": str(e)}
            }