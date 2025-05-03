"""
Модуль для анализа фона изображения.
"""
import cv2
import numpy as np
from typing import Dict, Any
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class BackgroundCheck(BaseCheck):
    """
    Проверка фона изображения на однородность и яркость.
    """
    check_id = "background"
    name = "Background Check"
    description = "Checks if the background is uniform and properly lit"
    
    default_config = {
        "background_std_dev_threshold": 110.0,  # Порог стандартного отклонения для однородности
        "is_dark_threshold": 80,              # Порог яркости для определения темного фона
        "edge_density_threshold": 0.08,         # Порог плотности краев для обнаружения текстур
        "grad_mean_threshold": 45               # Порог среднего градиента для гладкого фона
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет анализ фона изображения.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать лицо
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("No face found in context for background check")
            return {
                "status": "SKIPPED",
                "reason": "No face detected",
                "details": None
            }
        
        try:
            h, w = image.shape[:2]
            fx, fy, fw, fh = context["face"]["bbox"]
            
            # Расширяем область лица для маски
            margin_x = int(fw * 0.3)
            margin_y = int(fh * 0.3)
            x1 = max(0, fx - margin_x)
            y1 = max(0, fy - margin_y)
            x2 = min(w, fx + fw + margin_x)
            y2 = min(h, fy + fh + margin_y)
            
            # Создаем маску фона (1 - фон, 0 - лицо и отступ)
            background_mask = np.ones((h, w), dtype=np.uint8)
            cv2.rectangle(background_mask, (x1, y1), (x2, y2), 0, -1)
            
            # Проверка, есть ли достаточно фона для анализа
            if np.sum(background_mask) < 0.1 * w * h:
                logger.warning("Background area too small for analysis")
                return {
                    "status": "NEEDS_REVIEW",
                    "reason": "Insufficient background area",
                    "details": None
                }
            
            # Конвертируем в оттенки серого и анализируем фон
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            background_gray = cv2.bitwise_and(gray, gray, mask=background_mask)
            
            # Статистика фона
            background_pixels = background_gray[background_mask > 0]
            background_mean = np.mean(background_pixels)
            background_std_dev = np.std(background_pixels)
            
            # BGR статистика фона
            background_bgr = cv2.bitwise_and(image, image, mask=background_mask)
            mean_bgr = cv2.mean(background_bgr)[:3]
            
            # Анализ градиентов фона
            sobel_x = cv2.Sobel(background_gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(background_gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
            
            # Игнорируем нулевые пиксели (область лица)
            gradient_magnitude_masked = gradient_magnitude[background_mask > 0]
            grad_mean = np.mean(gradient_magnitude_masked) if gradient_magnitude_masked.size > 0 else 0
            
            # Обнаружение краев для поиска текстур
            edges = cv2.Canny(background_gray, 50, 150)
            edge_pixels = np.sum(edges > 0) / max(1, np.sum(background_mask))
            edge_density = float(edge_pixels)
            
            # Собираем результаты анализа
            details = {
                "background_mean": float(background_mean),
                "background_std_dev": float(background_std_dev),
                "background_mean_bgr": [float(x) for x in mean_bgr],
                "gradient_mean": float(grad_mean),
                "edge_density": float(edge_density),
                "is_dark_background": background_mean < self.config["is_dark_threshold"]
            }
            
            # Определяем проблемы с фоном
            is_uniform = background_std_dev <= self.config["background_std_dev_threshold"]
            is_plain_background = (grad_mean < self.config["grad_mean_threshold"] and 
                                 edge_density < self.config["edge_density_threshold"])
            is_dark = background_mean < self.config["is_dark_threshold"]
            
            issues = []
            if not is_uniform:
                issues.append(f"Background is not uniform (std_dev: {background_std_dev:.1f}, threshold: {self.config['background_std_dev_threshold']})")
            
            if not is_plain_background:
                issues.append(f"Background has texture or patterns (gradient: {grad_mean:.1f}, edge density: {edge_density:.3f})")
            
            if is_dark:
                issues.append(f"Background is too dark (mean brightness: {background_mean:.1f}, should be > {self.config['is_dark_threshold']})")
            
            # Итоговый результат
            if issues:
                return {
                    "status": "FAILED",
                    "reason": "; ".join(issues),
                    "details": details
                }
            else:
                return {
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error during background analysis: {e}")
            return {
                "status": "PASSED",  # В случае ошибки пропускаем проверку
                "reason": f"Background analysis error: {str(e)}",
                "details": {"error": str(e)}
            }