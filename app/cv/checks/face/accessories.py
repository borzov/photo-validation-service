"""
Модуль для проверки аксессуаров на лице.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger
from app.cv.checks.face.detector import glasses_cascade  # Импортируем глобальную переменную из модуля detector

logger = get_logger(__name__)

class AccessoriesCheck(BaseCheck):
    """
    Проверка наличия аксессуаров на лице (очки, головной убор, руки у лица).
    """
    check_id = "accessories"
    name = "Проверка аксессуаров"
    description = "Проверяет наличие аксессуаров на лице (очки, головной убор, руки)"
    
    default_config = {
        "glasses_detection_enabled": False,
        "headwear_detection_enabled": True,
        "hand_detection_enabled": True
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку наличия аксессуаров на лице.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать лицо с landmarks
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("No face found in context for accessories check")
            return {
                "status": "SKIPPED",
                "reason": "No face detected",
                "details": {"accessories_list": []}
            }
            
        landmarks = context["face"].get("landmarks")
        if not landmarks or len(landmarks) < 68:
            logger.warning("No facial landmarks found for accessories check")
            return {
                "status": "NEEDS_REVIEW",
                "reason": "No facial landmarks available",
                "details": {"accessories_list": []}
            }
            
        try:
            x, y, width, height = context["face"]["bbox"]
            
            # Вырезаем область лица
            face_img = image[y:y+height, x:x+width].copy()
            if face_img.size == 0:
                logger.warning("Empty face region for accessories detection")
                return {
                    "status": "NEEDS_REVIEW",
                    "reason": "Empty face region",
                    "details": {"accessories_list": []}
                }
                
            gray_face = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            accessories_found = []
            details = {"accessories_list": []}
            
            # Детекция очков (если включена)
            if self.config["glasses_detection_enabled"] and glasses_cascade is not None:
                glasses_detected = self._detect_glasses(face_img, landmarks, x, y)
                if glasses_detected:
                    accessories_found.append("glasses")
            
            # Детекция головного убора (если включена)
            if self.config["headwear_detection_enabled"]:
                headwear_detected = self._detect_headwear(face_img, landmarks, gray_face)
                if headwear_detected:
                    accessories_found.append("headwear")
            
            # Детекция рук у лица (если включена)
            if self.config["hand_detection_enabled"]:
                hands_detected = self._detect_hands_near_face(face_img, landmarks)
                if hands_detected:
                    accessories_found.append("hand_near_face")
            
            # Детекция бороды/усов
            beard_detected = self._detect_beard(face_img, landmarks, gray_face)
            if beard_detected:
                accessories_found.append("beard_mustache")
            
            # Удаление дубликатов
            details["accessories_list"] = list(set(accessories_found))
            
            # Формирование результата
            if details["accessories_list"]:
                return {
                    "status": "NEEDS_REVIEW",
                    "reason": f"{', '.join(details['accessories_list'])} detected",
                    "details": details
                }
            else:
                return {
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error during accessories check: {e}")
            return {
                "status": "PASSED",
                "reason": f"Accessories check error: {str(e)}",
                "details": {"accessories_list": [], "error": str(e)}
            }
    
    def _detect_glasses(self, face_img: np.ndarray, landmarks: List, x_offset: int, y_offset: int) -> bool:
        """
        Определяет наличие очков на лице.
        
        Args:
            face_img: Изображение области лица
            landmarks: Координаты лицевых точек
            x_offset, y_offset: Смещение лица относительно исходного изображения
            
        Returns:
            True, если очки обнаружены, иначе False
        """
        if glasses_cascade is None:
            return False
            
        try:
            # Преобразуем координаты точек в относительные
            eye_points = np.array(landmarks[36:48], dtype=np.int32)
            eye_points_rel = [(p[0] - x_offset, p[1] - y_offset) for p in eye_points]
            
            # Получаем более точную область глаз для поиска очков
            ex, ey, ew, eh = cv2.boundingRect(np.array(eye_points_rel, dtype=np.int32))
            
            # Расширяем область немного
            margin = int(max(ew, eh) * 0.2)
            ex, ey = max(0, ex - margin), max(0, ey - margin)
            ew, eh = min(face_img.shape[1] - ex, ew + 2*margin), min(face_img.shape[0] - ey, eh + 2*margin)
            
            # Вырезаем область глаз
            eye_roi_gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)[ey:ey+eh, ex:ex+ew]
            
            if eye_roi_gray.size <= 0:
                return False
                
            # Детекция очков с помощью cascade classifier
            glasses = glasses_cascade.detectMultiScale(
                eye_roi_gray,
                scaleFactor=1.2,
                minNeighbors=20,
                minSize=(int(ew*0.6), int(eh*0.6))
            )
            
            if len(glasses) > 0:
                # Проверка на симметричность (для уменьшения ложных срабатываний)
                if len(glasses) >= 2:
                    glasses_centers = [(gx + gw//2, gy + gh//2) for (gx, gy, gw, gh) in glasses]
                    y_diff = abs(glasses_centers[0][1] - glasses_centers[1][1])
                    if y_diff > eh * 0.2:
                        logger.info("Skipping glasses detection due to asymmetric detection")
                        return False
                
                logger.info("Glasses detected")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error detecting glasses: {e}")
            return False
    
    def _detect_headwear(self, face_img: np.ndarray, landmarks: List, gray_face: np.ndarray) -> bool:
        """
        Определяет наличие головного убора.
        
        Args:
            face_img: Изображение области лица
            landmarks: Координаты лицевых точек
            gray_face: Изображение лица в оттенках серого
            
        Returns:
            True, если головной убор обнаружен, иначе False
        """
        try:
            height, width = face_img.shape[:2]
            
            # Находим точки бровей
            brow_points_y = [p[1] for p in landmarks[17:27]]
            min_brow_y = min(brow_points_y)
            
            # Проверяем, что есть область над бровями
            if min_brow_y <= height * 0.1:
                return False
                
            # Определяем области для анализа
            forehead_top_y = max(0, int(min_brow_y * 0.7))  # Чуть выше бровей
            forehead_bottom_y = max(0, int(min_brow_y * 0.95))
            above_forehead_y = max(0, int(forehead_top_y * 0.8))  # Еще выше
            
            # Вырезаем области
            region_above = gray_face[above_forehead_y:forehead_top_y, :]
            region_forehead = gray_face[forehead_top_y:forehead_bottom_y, :]
            
            # Проверяем размеры областей
            if region_above.size < 50 or region_forehead.size < 50:
                return False
                
            # Анализируем текстуру и яркость
            mean_above, std_above = cv2.meanStdDev(region_above)
            mean_forehead, std_forehead = cv2.meanStdDev(region_forehead)
            
            # Определяем признаки головного убора
            brightness_diff = abs(mean_above[0][0] - mean_forehead[0][0])
            texture_diff = abs(std_above[0][0] - std_forehead[0][0])
            
            # Пороги для определения головного убора
            if brightness_diff > 120 or (std_above[0][0] > 60 and texture_diff > 55):
                logger.info(f"Headwear detected (brightness_diff: {brightness_diff:.1f}, texture_diff: {texture_diff:.1f})")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error detecting headwear: {e}")
            return False
    
    def _detect_hands_near_face(self, face_img: np.ndarray, landmarks: List) -> bool:
        """
        Определяет наличие рук у лица.
        
        Args:
            face_img: Изображение области лица
            landmarks: Координаты лицевых точек
            
        Returns:
            True, если руки у лица обнаружены, иначе False
        """
        try:
            height, width = face_img.shape[:2]
            
            # Конвертируем в YCrCb для лучшего обнаружения кожи
            ycrcb = cv2.cvtColor(face_img, cv2.COLOR_BGR2YCrCb)
            
            # Определяем область интереса - боковые части лица
            face_rect = cv2.boundingRect(np.array(landmarks, dtype=np.int32))
            face_center_x = face_rect[0] + face_rect[2] // 2
            face_width = face_rect[2]
            
            # Создаем маски для левой и правой стороны лица
            left_region = np.zeros((height, width), dtype=np.uint8)
            right_region = np.zeros((height, width), dtype=np.uint8)
            
            # Левая часть
            left_x2 = max(0, face_center_x - int(face_width * 0.1))
            cv2.rectangle(left_region, (0, 0), (left_x2, height), 255, -1)
            
            # Правая часть
            right_x1 = min(width-1, face_center_x + int(face_width * 0.1))
            cv2.rectangle(right_region, (right_x1, 0), (width, height), 255, -1)
            
            # Обнаружение кожи
            min_YCrCb = np.array([0, 135, 85], np.uint8)
            max_YCrCb = np.array([255, 180, 135], np.uint8)
            skin_mask = cv2.inRange(ycrcb, min_YCrCb, max_YCrCb)
            
            # Морфологические операции для улучшения маски
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
            
            # Применяем маски сторон к маске кожи
            left_skin = cv2.bitwise_and(skin_mask, skin_mask, mask=left_region)
            right_skin = cv2.bitwise_and(skin_mask, skin_mask, mask=right_region)
            
            # Находим контуры кожи
            left_contours, _ = cv2.findContours(left_skin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            right_contours, _ = cv2.findContours(right_skin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Порог для определения руки
            hand_threshold_ratio = 0.07  # % от площади лица
            hand_threshold = width * height * hand_threshold_ratio
            
            left_hand_detected = False
            right_hand_detected = False
            
            # Проверяем левую сторону
            if left_contours:
                largest_left = max(left_contours, key=cv2.contourArea)
                left_area = cv2.contourArea(largest_left)
                if left_area > hand_threshold:
                    left_hand_detected = True
                    logger.info(f"Hand detected on left side (area: {left_area:.1f})")
            
            # Проверяем правую сторону
            if right_contours:
                largest_right = max(right_contours, key=cv2.contourArea)
                right_area = cv2.contourArea(largest_right)
                if right_area > hand_threshold:
                    right_hand_detected = True
                    logger.info(f"Hand detected on right side (area: {right_area:.1f})")
            
            return left_hand_detected or right_hand_detected
            
        except Exception as e:
            logger.error(f"Error detecting hands: {e}")
            return False
    
    def _detect_beard(self, face_img: np.ndarray, landmarks: List, gray_face: np.ndarray) -> bool:
        """
        Определяет наличие бороды или усов.
        
        Args:
            face_img: Изображение области лица
            landmarks: Координаты лицевых точек
            gray_face: Изображение лица в оттенках серого
            
        Returns:
            True, если борода или усы обнаружены, иначе False
        """
        try:
            height, width = face_img.shape[:2]
            
            # Находим область от рта до подбородка
            chin_points_y = [p[1] for p in landmarks[0:17]]
            mouth_points_y = [p[1] for p in landmarks[48:68]]
            
            lower_face_start_y = max(0, int(np.mean(mouth_points_y)))
            lower_face_end_y = min(height, int(np.max(chin_points_y)))
            
            # Проверяем наличие области
            if lower_face_end_y <= lower_face_start_y + 10:
                return False
                
            # Вырезаем область для анализа
            lower_face_region = gray_face[lower_face_start_y:lower_face_end_y, :]
            
            if lower_face_region.size < 50:
                return False
                
            # Анализируем текстуру с помощью Лапласиана
            laplacian_var = cv2.Laplacian(lower_face_region, cv2.CV_64F).var()
            
            # Проверяем симметричность текстуры (для уменьшения ложных срабатываний)
            h, w = lower_face_region.shape
            left_region = lower_face_region[:, :w//2]
            right_region = lower_face_region[:, w//2:]
            
            left_var = cv2.Laplacian(left_region, cv2.CV_64F).var()
            right_var = cv2.Laplacian(right_region, cv2.CV_64F).var()
            
            # Пороги для определения бороды
            if laplacian_var > 500 and abs(left_var - right_var) < laplacian_var * 0.5:
                logger.info(f"Beard/mustache detected (Laplacian var: {laplacian_var:.1f})")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error detecting beard: {e}")
            return False