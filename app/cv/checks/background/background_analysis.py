"""
Модуль для анализа фона изображения.
"""
import cv2
import numpy as np
from typing import Dict, Any
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger

logger = get_logger(__name__)

class BackgroundCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка однородности и яркости фона.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="background",
            display_name="Анализ фона",
            description="Проверяет однородность и качество фона",
            category="background",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="background_std_dev_threshold",
                    type="float",
                    default=110.0,
                    description="Порог стандартного отклонения для однородности фона",
                    min_value=50.0,
                    max_value=200.0,
                    required=True
                ),
                CheckParameter(
                    name="is_dark_threshold",
                    type="int",
                    default=80,
                    description="Порог яркости для определения тёмного фона",
                    min_value=30,
                    max_value=150,
                    required=True
                ),
                CheckParameter(
                    name="edge_density_threshold",
                    type="float",
                    default=0.08,
                    description="Порог плотности краёв для обнаружения текстур",
                    min_value=0.01,
                    max_value=0.5,
                    required=False
                ),
                CheckParameter(
                    name="grad_mean_threshold",
                    type="int",
                    default=45,
                    description="Порог среднего градиента для гладкого фона",
                    min_value=10,
                    max_value=100,
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет анализ фона изображения.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать face
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("No face found in context for background check")
            return {
                "check": "background",
                "status": "SKIPPED",
                "reason": "Лицо не обнаружено",
                "details": None
            }

        try:
            h, w = image.shape[:2]
            fx, fy, fw, fh = context["face"]["bbox"]

            # Expand face area for mask
            margin_x = int(fw * 0.3)
            margin_y = int(fh * 0.3)
            x1 = max(0, fx - margin_x)
            y1 = max(0, fy - margin_y)
            x2 = min(w, fx + fw + margin_x)
            y2 = min(h, fy + fh + margin_y)

            # Create background mask (1 - background, 0 - face and margin)
            background_mask = np.ones((h, w), dtype=np.uint8)
            cv2.rectangle(background_mask, (x1, y1), (x2, y2), 0, -1)

            # Check if there's enough background for analysis
            if np.sum(background_mask) < 0.1 * w * h:
                logger.warning("Background area too small for analysis")
                return {
                    "check": "background",
                    "status": "NEEDS_REVIEW",
                    "reason": "Область фона слишком мала для анализа",
                    "details": None
                }

            # Convert to grayscale and analyze background
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            background_gray = cv2.bitwise_and(gray, gray, mask=background_mask)

            # Background statistics
            background_pixels = background_gray[background_mask > 0]
            background_mean = np.mean(background_pixels)
            background_std_dev = np.std(background_pixels)

            # BGR background statistics
            background_bgr = cv2.bitwise_and(image, image, mask=background_mask)
            mean_bgr = cv2.mean(background_bgr)[:3]

            # Background gradient analysis
            sobel_x = cv2.Sobel(background_gray, cv2.CV_64F, 1, 0, ksize=3)
            sobel_y = cv2.Sobel(background_gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)

            # Ignore zero pixels (face area)
            gradient_magnitude_masked = gradient_magnitude[background_mask > 0]
            grad_mean = np.mean(gradient_magnitude_masked) if gradient_magnitude_masked.size > 0 else 0

            # Edge detection for texture search
            edges = cv2.Canny(background_gray, 50, 150)
            edge_pixels = np.sum(edges > 0) / max(1, np.sum(background_mask))
            edge_density = float(edge_pixels)

            # Get thresholds from parameters
            background_std_dev_threshold = self.parameters["background_std_dev_threshold"]
            is_dark_threshold = self.parameters["is_dark_threshold"]
            edge_density_threshold = self.parameters["edge_density_threshold"]
            grad_mean_threshold = self.parameters["grad_mean_threshold"]

            # Collect analysis results
            details = {
                "background_mean": float(background_mean),
                "background_std_dev": float(background_std_dev),
                "background_mean_bgr": [float(x) for x in mean_bgr],
                "gradient_mean": float(grad_mean),
                "edge_density": float(edge_density),
                "is_dark_background": background_mean < is_dark_threshold,
                "thresholds": {
                    "std_dev": background_std_dev_threshold,
                    "dark": is_dark_threshold,
                    "edge_density": edge_density_threshold,
                    "gradient": grad_mean_threshold
                },
                "parameters_used": self.parameters
            }

            # Determine background issues
            is_uniform = background_std_dev <= background_std_dev_threshold
            is_plain_background = (grad_mean < grad_mean_threshold and 
                                 edge_density < edge_density_threshold)
            is_dark = background_mean < is_dark_threshold

            issues = []
            if not is_uniform:
                issues.append(f"Фон неоднородный (σ: {background_std_dev:.1f}, порог: {background_std_dev_threshold})")

            if not is_plain_background:
                issues.append(f"Фон имеет текстуры или узоры (градиент: {grad_mean:.1f}, плотность краев: {edge_density:.3f})")

            if is_dark:
                issues.append(f"Фон слишком темный (яркость: {background_mean:.1f}, должна быть > {is_dark_threshold})")

            # Final result
            if issues:
                return {
                    "check": "background",
                    "status": "FAILED",
                    "reason": "; ".join(issues),
                    "details": details
                }
            else:
                return {
                    "check": "background",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Ошибка при анализе фона: {e}")
            return {
                "check": "background",
                "status": "PASSED",  # Skip check in case of error
                "reason": f"Ошибка анализа фона: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }