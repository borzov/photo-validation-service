"""
Проверка на эффект красных глаз.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class RedEyeCheck(BaseCheck):
    """
    Проверка на эффект красных глаз в области глаз.
    """
    check_id = "redEye"
    name = "Red Eye Check"
    description = "Checks if the eyes have red-eye effect caused by flash"
    
    default_config = {
        "red_threshold": 180,         # Минимальная яркость красного канала
        "red_ratio_threshold": 1.8,   # Минимальное соотношение красного к другим каналам
        "min_red_pixel_ratio": 0.15,  # Минимальная доля ярких красных пикселей
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку на эффект красных глаз.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать face["landmarks"]
            
        Returns:
            Результаты проверки
        """
        landmarks = context.get("face", {}).get("landmarks") if context else None
        
        if not landmarks or len(landmarks) < 68:
            logger.warning("Skipping red eye check due to missing landmarks")
            return {
                "status": "PASSED",
                "reason": "No landmarks available for red eye check",
                "details": None
            }
    
        try:
            # Получаем области глаз из landmarks
            left_eye = np.array(landmarks[36:42], dtype=np.int32)
            right_eye = np.array(landmarks[42:48], dtype=np.int32)
            
            # Проверка каждого глаза
            left_red = self._check_eye_region(image, left_eye)
            right_red = self._check_eye_region(image, right_eye)
            
            affected_eyes = []
            if left_red: affected_eyes.append("left")
            if right_red: affected_eyes.append("right")
            
            if affected_eyes:
                return {
                    "status": "FAILED",
                    "reason": f"Red eye effect detected in {' and '.join(affected_eyes)} eye(s)",
                    "details": {"affected_eyes": affected_eyes}
                }
            else:
                return {
                    "status": "PASSED",
                    "details": {"affected_eyes": []}
                }
                
        except Exception as e:
            logger.error(f"Error during red eye check: {e}")
            return {
                "status": "PASSED",
                "reason": f"Red eye check error: {str(e)}",
                "details": None
            }
    
    def _check_eye_region(self, image: np.ndarray, eye_points: np.ndarray) -> bool:
        """
        Проверяет один глаз на наличие эффекта "красных глаз".
        
        Args:
            image: Изображение
            eye_points: Координаты точек глаза (6 точек)
            
        Returns:
            True, если обнаружен эффект красных глаз, иначе False
        """
        x, y, w, h = cv2.boundingRect(eye_points)
        
        # Расширяем область немного
        margin = int(max(w, h) * 0.2)
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(image.shape[1] - x, w + 2*margin)
        h = min(image.shape[0] - y, h + 2*margin)
        
        eye_roi = image[y:y+h, x:x+w]
        if eye_roi.size == 0:
            return False
    
        # Находим центр глаза для более точного анализа зрачка
        eye_center_x = w // 2
        eye_center_y = h // 2
        
        # Определяем размер зрачка - обычно 20-30% от размера глаза
        pupil_radius = int(min(w, h) * 0.2)
        
        # Создаем маску для зрачка (центральная часть глаза)
        pupil_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(pupil_mask, (eye_center_x, eye_center_y), pupil_radius, 255, -1)
        
        # Сначала проверяем, может ли быть красный глаз в принципе - 
        # в зрачке должно быть достаточно красного
        b, g, r = cv2.split(eye_roi)
        
        # Применяем маску зрачка
        pupil_r = cv2.bitwise_and(r, r, mask=pupil_mask)
        pupil_g = cv2.bitwise_and(g, g, mask=pupil_mask)
        pupil_b = cv2.bitwise_and(b, b, mask=pupil_mask)
        
        # Вычисляем средние значения цветов в зрачке
        pupil_pixels = np.count_nonzero(pupil_mask)
        if pupil_pixels == 0:
            return False
            
        r_mean = np.sum(pupil_r) / pupil_pixels
        g_mean = np.sum(pupil_g) / pupil_pixels
        b_mean = np.sum(pupil_b) / pupil_pixels
        
        # Получаем параметры из конфигурации
        red_threshold = self.config["red_threshold"]
        red_ratio_threshold = self.config["red_ratio_threshold"]
        min_red_pixel_ratio = self.config["min_red_pixel_ratio"]
        
        # Логирование для отладки
        logger.debug(f"Red eye check: R={r_mean:.1f}, G={g_mean:.1f}, B={b_mean:.1f}")
        
        # Детекция красных глаз по доминированию красного канала и его яркости
        is_red_eye = (r_mean > red_threshold and 
                      r_mean / (g_mean + 0.1) > red_ratio_threshold and 
                      r_mean / (b_mean + 0.1) > red_ratio_threshold)
        
        # Если первая проверка не сработала, проверяем наличие ярких красных пикселей
        if not is_red_eye:
            # Проверим наличие ярких красных пикселей, а не только средние значения
            high_red_pixels = np.sum((pupil_r > red_threshold) & 
                                    (pupil_r > red_ratio_threshold * pupil_g) & 
                                    (pupil_r > red_ratio_threshold * pupil_b))
            red_pixel_ratio = high_red_pixels / max(1, pupil_pixels)
            
            # Если достаточная доля пикселей в зрачке - яркие красные, это тоже считаем красным глазом
            is_red_eye = red_pixel_ratio > min_red_pixel_ratio
            
            if is_red_eye:
                logger.info(f"Red eye detected via pixel ratio check: ratio={red_pixel_ratio:.3f}")
        
        if is_red_eye:
            logger.info(f"Red eye detected: R={r_mean:.1f}, G={g_mean:.1f}, B={b_mean:.1f}")
        
        return is_red_eye