"""
Модуль для проверки аксессуаров на лице.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger
from app.cv.checks.face.detector import glasses_cascade

logger = get_logger(__name__)

class AccessoriesCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка наличия аксессуаров на лице (очки, головной убор, руки у лица).
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="accessories",
            display_name="Проверка аксессуаров",
            description="Проверяет наличие аксессуаров на лице (очки, головной убор, руки)",
            category="face_detection",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="glasses_detection_enabled",
                    type="bool",
                    default=False,
                    description="Включить обнаружение очков",
                    required=False
                ),
                CheckParameter(
                    name="headwear_detection_enabled",
                    type="bool",
                    default=True,
                    description="Включить обнаружение головного убора",
                    required=False
                ),
                CheckParameter(
                    name="hand_detection_enabled",
                    type="bool",
                    default=True,
                    description="Включить обнаружение рук у лица",
                    required=False
                ),
                CheckParameter(
                    name="glasses_confidence_threshold",
                    type="float",
                    default=0.5,
                    description="Порог уверенности для обнаружения очков",
                    min_value=0.1,
                    max_value=0.9,
                    required=False
                ),
                CheckParameter(
                    name="skin_detection_threshold",
                    type="float",
                    default=0.5,
                    description="Порог обнаружения кожи для анализа рук",
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
        Выполняет проверку аксессуаров на лице.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context:
            return {
                "check": "accessories",
                "status": "SKIPPED",
                "reason": "Лицо не обнаружено",
                "details": None
            }

        try:
            accessories_found = []
            details = {"parameters_used": self.parameters}
            
            # Обнаружение очков
            if self.parameters["glasses_detection_enabled"]:
                glasses_result = self._detect_glasses(image, context)
                details["glasses"] = glasses_result
                if glasses_result["detected"]:
                    accessories_found.append("очки")
            
            # Обнаружение головного убора
            if self.parameters["headwear_detection_enabled"]:
                headwear_result = self._detect_headwear(image, context)
                details["headwear"] = headwear_result
                if headwear_result["detected"]:
                    accessories_found.append("головной убор")
            
            # Обнаружение рук
            if self.parameters["hand_detection_enabled"]:
                hand_result = self._detect_hands(image, context)
                details["hands"] = hand_result
                if hand_result["detected"]:
                    accessories_found.append("руки")
            
            details["accessories_found"] = accessories_found
            
            if accessories_found:
                return {
                    "check": "accessories",
                    "status": "FAILED",
                    "reason": f"Обнаружены аксессуары: {', '.join(accessories_found)}",
                    "details": details
                }
            else:
                return {
                    "check": "accessories",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Ошибка при проверке аксессуаров: {e}")
            return {
                "check": "accessories",
                "status": "NEEDS_REVIEW",
                "reason": f"Ошибка при проверке аксессуаров: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }

    def _detect_glasses(self, image: np.ndarray, context: Dict[str, Any]) -> Dict[str, Any]:
        """Обнаружение очков на лице."""
        try:
            if "bbox" not in context["face"]:
                return {"detected": False, "reason": "Нет bbox лица"}
            
            x, y, w, h = context["face"]["bbox"]
            face_roi = image[y:y+h, x:x+w]
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            # Используем каскад для очков
            if glasses_cascade is not None:
                glasses = glasses_cascade.detectMultiScale(
                    gray_face, 
                    scaleFactor=1.1, 
                    minNeighbors=5,
                    minSize=(20, 20)
                )
                
                detected = len(glasses) > 0
                confidence = len(glasses) * 0.2 if detected else 0.0
                
                return {
                    "detected": detected and confidence > self.parameters["glasses_confidence_threshold"],
                    "confidence": confidence,
                    "count": len(glasses)
                }
            else:
                return {"detected": False, "reason": "Каскад для очков недоступен"}
                
        except Exception as e:
            return {"detected": False, "error": str(e)}

    def _detect_headwear(self, image: np.ndarray, context: Dict[str, Any]) -> Dict[str, Any]:
        """Обнаружение головного убора над лицом."""
        try:
            if "bbox" not in context["face"]:
                return {"detected": False, "reason": "Нет bbox лица"}
            
            x, y, w, h = context["face"]["bbox"]
            
            # Проверяем область над лицом на однородность цвета/текстуры (признак головного убора)
            above_y_start = max(0, y - int(h * 0.5))
            above_y_end = y
            above_region = image[above_y_start:above_y_end, x:x+w]
            
            if above_region.size == 0:
                return {"detected": False, "reason": "Нет области над лицом"}
            
            # Анализируем однородность цвета
            gray_above = cv2.cvtColor(above_region, cv2.COLOR_BGR2GRAY)
            std_dev = np.std(gray_above)
            mean_brightness = np.mean(gray_above)
            
            # Простая эвристика: низкое стандартное отклонение может указывать на головной убор
            headwear_detected = std_dev < 30 and mean_brightness < 100
            
            return {
                "detected": headwear_detected,
                "std_dev": float(std_dev),
                "mean_brightness": float(mean_brightness)
            }
            
        except Exception as e:
            return {"detected": False, "error": str(e)}

    def _detect_hands(self, image: np.ndarray, context: Dict[str, Any]) -> Dict[str, Any]:
        """Обнаружение рук рядом с лицом с помощью анализа цвета кожи."""
        try:
            if "bbox" not in context["face"]:
                return {"detected": False, "reason": "Нет bbox лица"}
            
            x, y, w, h = context["face"]["bbox"]
            
            # Расширяем область поиска вокруг лица
            margin = int(max(w, h) * 0.3)
            x_start = max(0, x - margin)
            y_start = max(0, y - margin)
            x_end = min(image.shape[1], x + w + margin)
            y_end = min(image.shape[0], y + h + margin)
            
            search_region = image[y_start:y_end, x_start:x_end]
            
            # Область лица для эталона цвета кожи
            face_region = image[y:y+h, x:x+w]
            
            # Оцениваем цвет кожи по лицу
            face_hsv = cv2.cvtColor(face_region, cv2.COLOR_BGR2HSV)
            face_mask = cv2.inRange(face_hsv, (0, 20, 70), (20, 255, 255))
            
            # Применяем к области поиска
            search_hsv = cv2.cvtColor(search_region, cv2.COLOR_BGR2HSV)
            skin_mask = cv2.inRange(search_hsv, (0, 20, 70), (20, 255, 255))
            
            # Подсчитываем пиксели кожи вне области лица
            total_skin_pixels = np.sum(skin_mask > 0)
            search_area = search_region.shape[0] * search_region.shape[1]
            skin_ratio = total_skin_pixels / search_area
            
            hands_detected = skin_ratio > self.parameters["skin_detection_threshold"]
            
            return {
                "detected": hands_detected,
                "skin_ratio": float(skin_ratio),
                "skin_pixels": int(total_skin_pixels)
            }
            
        except Exception as e:
            return {"detected": False, "error": str(e)}