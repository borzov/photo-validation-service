"""
Модуль для проверки наличия посторонних объектов на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger

logger = get_logger(__name__)

class ExtraneousObjectsCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка наличия посторонних объектов и людей на фоне.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="extraneous_objects",
            display_name="Проверка посторонних объектов",
            description="Проверяет наличие дополнительных людей или объектов на фоне",
            category="background",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="min_object_contour_area_ratio",
                    type="float",
                    default=0.03,
                    description="Минимальное соотношение площади контура объекта к изображению",
                    min_value=0.001,
                    max_value=0.5,
                    required=True
                ),
                CheckParameter(
                    name="person_scale_factor",
                    type="float",
                    default=1.1,
                    description="Коэффициент масштабирования для HOG детектора людей",
                    min_value=1.02,
                    max_value=1.5,
                    required=True
                ),
                CheckParameter(
                    name="person_min_neighbors",
                    type="int",
                    default=6,
                    description="Минимальное количество соседей для HOG детектора людей",
                    min_value=1,
                    max_value=20,
                    required=True
                ),
                CheckParameter(
                    name="canny_threshold1",
                    type="int",
                    default=50,
                    description="Нижний порог для детектора краёв Canny",
                    min_value=10,
                    max_value=200,
                    required=True
                ),
                CheckParameter(
                    name="canny_threshold2",
                    type="int",
                    default=150,
                    description="Верхний порог для детектора краёв Canny",
                    min_value=50,
                    max_value=300,
                    required=True
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку наличия посторонних объектов на изображении.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            h, w = image.shape[:2]
            
            # Create mask for background analysis
            background_mask = np.ones((h, w), dtype=np.uint8)
            
            # Exclude main face area if available
            if context and "face" in context and "bbox" in context["face"]:
                x, y, fw, fh = context["face"]["bbox"]
                # Expand face area slightly
                margin_x = int(fw * 0.2)
                margin_y = int(fh * 0.2)
                x1 = max(0, x - margin_x)
                y1 = max(0, y - margin_y)
                x2 = min(w, x + fw + margin_x)
                y2 = min(h, y + fh + margin_y)
                cv2.rectangle(background_mask, (x1, y1), (x2, y2), 0, -1)
            
            # 1. Detect people using HOG detector
            people_detected = self._detect_people(image, background_mask)
            
            # 2. Detect objects using contour analysis
            objects_detected = self._detect_objects_by_contours(image, background_mask)
            
            details = {
                "people_detection": people_detected,
                "object_detection": objects_detected,
                "parameters_used": self.parameters
            }
            
            # Determine result
            issues = []
            if people_detected["count"] > 0:
                issues.append(f"Обнаружено {people_detected['count']} дополнительных людей")
            if objects_detected["count"] > 0:
                issues.append(f"Обнаружено {objects_detected['count']} посторонних объектов")
            
            if issues:
                return {
                    "check": "extraneous_objects",
                    "status": "FAILED",
                    "reason": "; ".join(issues),
                    "details": details
                }
            else:
                return {
                    "check": "extraneous_objects",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Ошибка при проверке посторонних объектов: {e}")
            return {
                "check": "extraneous_objects",
                "status": "NEEDS_REVIEW",
                "reason": f"Ошибка при проверке посторонних объектов: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }

    def _detect_people(self, image: np.ndarray, background_mask: np.ndarray) -> Dict[str, Any]:
        """Detect people using HOG descriptor."""
        try:
            # Initialize HOG descriptor
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            # Apply background mask to focus on background areas
            masked_image = cv2.bitwise_and(image, image, mask=background_mask)
            
            # Detect people
            boxes, weights = hog.detectMultiScale(
                masked_image,
                winStride=(8, 8),
                padding=(8, 8),
                scale=self.parameters["person_scale_factor"],
                finalThreshold=self.parameters["person_min_neighbors"]
            )
            
            people_count = len(boxes)
            people_boxes = boxes.tolist() if people_count > 0 else []
            
            return {
                "count": people_count,
                "boxes": people_boxes,
                "method": "HOG_descriptor"
            }
            
        except Exception as e:
            return {
                "count": 0,
                "error": str(e),
                "method": "HOG_descriptor"
            }

    def _detect_objects_by_contours(self, image: np.ndarray, background_mask: np.ndarray) -> Dict[str, Any]:
        """Detect objects using contour analysis."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Apply background mask
            gray_masked = cv2.bitwise_and(gray, gray, mask=background_mask)
            
            # Edge detection
            edges = cv2.Canny(
                gray_masked, 
                self.parameters["canny_threshold1"], 
                self.parameters["canny_threshold2"]
            )
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size
            min_area = image.shape[0] * image.shape[1] * self.parameters["min_object_contour_area_ratio"]
            significant_contours = [c for c in contours if cv2.contourArea(c) > min_area]
            
            # Additional filtering: remove contours that are too elongated or irregular
            filtered_contours = []
            for contour in significant_contours:
                # Calculate aspect ratio
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / h if h > 0 else 0
                
                # Calculate solidity (area / convex hull area)
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                if hull_area > 0:
                    solidity = cv2.contourArea(contour) / hull_area
                else:
                    solidity = 0
                
                # Filter criteria: reasonable aspect ratio and solidity
                if 0.2 <= aspect_ratio <= 5.0 and solidity > 0.3:
                    filtered_contours.append(contour)
            
            object_count = len(filtered_contours)
            object_boxes = []
            for contour in filtered_contours:
                x, y, w, h = cv2.boundingRect(contour)
                object_boxes.append([x, y, w, h])
            
            return {
                "count": object_count,
                "boxes": object_boxes,
                "total_contours": len(contours),
                "significant_contours": len(significant_contours),
                "method": "contour_analysis"
            }
            
        except Exception as e:
            return {
                "count": 0,
                "error": str(e),
                "method": "contour_analysis"
            }