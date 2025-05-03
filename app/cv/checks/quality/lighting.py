"""
Модуль для проверки освещения на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any
import math
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class LightingCheck(BaseCheck):
    """
    Проверка освещения на изображении.
    """
    check_id = "lighting"
    name = "Lighting Check"
    description = "Checks if the lighting is appropriate (not too dark, bright, or low contrast)"
    
    default_config = {
        "underexposure_threshold": 25,    # Порог для недоэкспонирования
        "overexposure_threshold": 240,    # Порог для переэкспонирования
        "low_contrast_threshold": 20,     # Порог для низкого контраста
        "shadow_ratio_threshold": 0.4,    # Порог для доли темных пикселей
        "highlight_ratio_threshold": 0.3   # Порог для доли ярких пикселей
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку освещения.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать context["face"]["bbox"]
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("No face found in context for lighting check")
            return {
                "status": "SKIPPED",
                "reason": "No face detected",
                "details": None
            }
            
        try:
            # Получаем область лица из контекста
            x, y, width, height = context["face"]["bbox"]
            face_region = image[y:y+height, x:x+width]
            
            if face_region.size == 0:
                logger.warning("Face region is empty, skipping lighting check")
                return {
                    "status": "NEEDS_REVIEW",
                    "reason": "Empty face region",
                    "details": {}
                }
                
            # Конвертируем в оттенки серого
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            
            # Вычисляем среднюю яркость и стандартное отклонение
            mean_brightness_np = np.mean(gray)
            std_brightness_np = np.std(gray)
            
            # Вычисляем гистограмму для анализа темных и светлых областей
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_norm = hist.ravel() / hist.sum()
            
            # Доля темных и светлых пикселей
            underexposure_threshold = self.config["underexposure_threshold"]
            overexposure_threshold = self.config["overexposure_threshold"]
            shadow_ratio = np.sum(hist_norm[:underexposure_threshold])
            highlight_ratio = np.sum(hist_norm[overexposure_threshold:])
            
            # Проверка на NaN и конвертация в Python типы
            mean_brightness = float(mean_brightness_np) if not math.isnan(mean_brightness_np) else 0.0
            std_brightness = float(std_brightness_np) if not math.isnan(std_brightness_np) else 0.0
            shadow_ratio = float(shadow_ratio) if not math.isnan(shadow_ratio) else 0.0
            highlight_ratio = float(highlight_ratio) if not math.isnan(highlight_ratio) else 0.0
            
            # Детали для ответа
            details = {
                "mean_brightness": round(mean_brightness, 2),
                "std_dev_brightness": round(std_brightness, 2),
                "shadow_pixel_ratio": round(shadow_ratio, 3),
                "highlight_pixel_ratio": round(highlight_ratio, 3)
            }
            
            # Пороговые значения из конфигурации
            low_contrast_threshold = self.config["low_contrast_threshold"]
            shadow_ratio_threshold = self.config["shadow_ratio_threshold"]
            highlight_ratio_threshold = self.config["highlight_ratio_threshold"]
            
            # Список проблем с освещением
            issues = []
            
            # Проверки на недостаточное/избыточное освещение и низкий контраст
            if mean_brightness < underexposure_threshold or shadow_ratio > shadow_ratio_threshold:
                issues.append(f"UNDEREXPOSED (mean={mean_brightness:.1f}, shadow_ratio={shadow_ratio:.3f})")
                
            if mean_brightness > overexposure_threshold or highlight_ratio > highlight_ratio_threshold:
                issues.append(f"OVEREXPOSED (mean={mean_brightness:.1f}, highlight_ratio={highlight_ratio:.3f})")
                
            if std_brightness < low_contrast_threshold:
                issues.append(f"LOW_CONTRAST (std_dev={std_brightness:.1f})")
            
            # Итоговый результат
            if issues:
                return {
                    "status": "FAILED",
                    "reason": ", ".join(issues),
                    "details": details
                }
            else:
                return {
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error during lighting check: {e}")
            return {
                "status": "NEEDS_REVIEW",
                "reason": f"Lighting check error: {str(e)}",
                "details": {"error": str(e)}
            }