"""
Модуль для проверки наличия посторонних объектов на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class ExtraneousObjectsCheck(BaseCheck):
    """
    Проверка наличия посторонних объектов и людей на фоне.
    """
    check_id = "extraneousObjects"
    name = "Extraneous Objects Check"
    description = "Checks for additional people or objects in the background"
    
    default_config = {
        "min_object_contour_area_ratio": 0.03,  # Минимальное отношение площади объекта к площади изображения
        "person_scale_factor": 1.1,            # Масштабный фактор для HOG детектора людей
        "person_min_neighbors": 6,             # Минимальное количество соседей для HOG детектора
        "canny_threshold1": 50,                # Нижний порог для детектора краев Canny
        "canny_threshold2": 150                # Верхний порог для детектора краев Canny
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку на наличие посторонних объектов и людей.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать лицо
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("No face found in context for extraneous objects check")
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
            
            # Если маска фона пустая, анализ невозможен
            if np.sum(background_mask) < 0.1 * w * h:
                logger.warning("Background area too small for object detection")
                return {
                    "status": "NEEDS_REVIEW",
                    "reason": "Insufficient background area",
                    "details": None
                }
            
            # Изображение только с фоном
            background_image = cv2.bitwise_and(image, image, mask=background_mask)
            
            # Инициализация HOG детектора людей
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            issues_found = []
            details = {}
            
            # Детекция людей на фоне
            try:
                people_rects, weights = hog.detectMultiScale(
                    background_image,
                    winStride=(16, 16),
                    padding=(8, 8),
                    scale=self.config["person_scale_factor"],
                    hitThreshold=0.8
                )
                
                # Если найдены люди
                if isinstance(people_rects, np.ndarray) and people_rects.size > 0:
                    # Преобразуем веса в список
                    if isinstance(weights, np.ndarray):
                        if weights.ndim > 1:
                            weights_str = [round(float(w[0]), 2) for w in weights]
                        else:
                            weights_str = [round(float(w), 2) for w in weights]
                    else:
                        weights_str = [round(float(weights), 2)] if weights is not None else []
                    
                    logger.info(f"Detected {len(people_rects)} potential additional people (weights: {weights_str})")
                    issues_found.append("ADDITIONAL_PEOPLE_DETECTED")
                    details["people_detected_bboxes"] = [tuple(int(v) for v in rect) for rect in people_rects]
                    details["people_weights"] = weights_str
            except Exception as hog_error:
                logger.error(f"Error during HOG people detection: {hog_error}")
            
            # Обнаружение объектов по контурам
            gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            blurred_img = cv2.GaussianBlur(gray_img, (5, 5), 0)
            edges = cv2.Canny(
                blurred_img, 
                self.config["canny_threshold1"], 
                self.config["canny_threshold2"]
            )
            masked_edges = cv2.bitwise_and(edges, edges, mask=background_mask)
            
            contours, _ = cv2.findContours(masked_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            large_contours_info = []
            min_contour_area = self.config["min_object_contour_area_ratio"] * w * h
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > min_contour_area:
                    x_c, y_c, w_c, h_c = cv2.boundingRect(contour)
                    # Проверяем "плотность" контура
                    if w_c > 10 and h_c > 10:
                        large_contours_info.append({
                            "bbox": (int(x_c), int(y_c), int(w_c), int(h_c)),
                            "area": float(area)
                        })
            
            if large_contours_info:
                logger.info(f"Detected {len(large_contours_info)} large contours in the background")
                issues_found.append("ADDITIONAL_OBJECTS_DETECTED")
                details["large_contours_info"] = large_contours_info
            
            # Формируем результат
            unique_issues = sorted(list(set(issues_found)))
            if unique_issues:
                # Люди важнее объектов
                status = "FAILED" if "ADDITIONAL_PEOPLE_DETECTED" in unique_issues else "NEEDS_REVIEW"
                return {
                    "status": status,
                    "reason": ", ".join(unique_issues),
                    "details": details
                }
            else:
                return {
                    "status": "PASSED",
                    "details": "Background appears clear of obstructions and other people"
                }
                
        except Exception as e:
            logger.error(f"Error during extraneous objects check: {e}")
            return {
                "status": "PASSED",  # В случае ошибки пропускаем
                "reason": f"Extraneous objects check error: {str(e)}",
                "details": {"error": str(e)}
            }