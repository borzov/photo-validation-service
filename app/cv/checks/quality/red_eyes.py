"""
Проверка на эффект красных глаз.
"""
import cv2
import numpy as np
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger

logger = get_logger(__name__)

class RedEyeCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка на эффект красных глаз в области глаз.
    
    Алгоритм анализирует области глаз на изображении для определения
    эффекта красных глаз, вызванного вспышкой. Использует комбинацию методов:
    1. Анализ соотношения каналов RGB в области зрачка
    2. Проверка на наличие ярких красных пикселей
    3. Сегментация области зрачка с использованием адаптивных порогов
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Return metadata for this check module."""
        return CheckMetadata(
            name="red_eye",
            display_name="Проверка красных глаз",
            description="Проверяет наличие эффекта красных глаз, вызванного вспышкой камеры",
            category="image_quality",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="red_threshold",
                    type="int",
                    default=180,
                    description="Минимальная яркость красного канала для обнаружения красных глаз",
                    min_value=100,
                    max_value=255,
                    required=True
                ),
                CheckParameter(
                    name="red_ratio_threshold",
                    type="float",
                    default=1.8,
                    description="Минимальное соотношение красного канала к другим каналам",
                    min_value=1.2,
                    max_value=3.0,
                    required=True
                ),
                CheckParameter(
                    name="min_red_pixel_ratio",
                    type="float",
                    default=0.15,
                    description="Минимальное соотношение ярких красных пикселей в области зрачка",
                    min_value=0.05,
                    max_value=0.5,
                    required=True
                ),
                CheckParameter(
                    name="pupil_relative_size",
                    type="float",
                    default=0.3,
                    description="Относительный размер зрачка к области глаза",
                    min_value=0.1,
                    max_value=0.8,
                    required=False
                ),
                CheckParameter(
                    name="adaptive_threshold",
                    type="bool",
                    default=True,
                    description="Использовать адаптивный порог для сегментации зрачка",
                    required=False
                ),
                CheckParameter(
                    name="hsv_detection",
                    type="bool",
                    default=True,
                    description="Использовать цветовое пространство HSV для улучшенного обнаружения красного",
                    required=False
                ),
                CheckParameter(
                    name="debug_mode",
                    type="bool",
                    default=False,
                    description="Включить подробное логирование для отладки",
                    required=False
                ),
                CheckParameter(
                    name="save_debug_images",
                    type="bool",
                    default=False,
                    description="Сохранять отладочные изображения для анализа",
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def __init__(self, **parameters):
        """Initialize with parameters and debug directory."""
        super().__init__(**parameters)
        
        # Initialize debug directory if needed
        if self.parameters["save_debug_images"]:
            debug_dir = "/app/local_storage/debug"
            if not os.path.exists(debug_dir):
                os.makedirs(debug_dir, exist_ok=True)
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку на эффект красных глаз.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать face["landmarks"]
            
        Returns:
            Результаты проверки с подробными метриками
        """
        if not context or "face" not in context:
            return {
                "check": "red_eye",
                "status": "SKIPPED",
                "reason": "Лицо не обнаружено",
                "details": None
            }

        landmarks = context["face"].get("landmarks")
        if not landmarks or len(landmarks) < 68:
            return {
                "check": "red_eye",
                "status": "SKIPPED",
                "reason": "Нет ориентиров для проверки красных глаз",
                "details": None
            }

        try:
            # Получаем области глаз из landmarks
            left_eye = np.array(landmarks[36:42], dtype=np.int32)
            right_eye = np.array(landmarks[42:48], dtype=np.int32)
            
            # Проверка каждого глаза
            left_red, left_metrics = self._check_eye_region(image, left_eye, "left")
            right_red, right_metrics = self._check_eye_region(image, right_eye, "right")
            
            affected_eyes = []
            if left_red: affected_eyes.append("left")
            if right_red: affected_eyes.append("right")
            
            details = {
                "affected_eyes": affected_eyes,
                "left_eye_metrics": left_metrics,
                "right_eye_metrics": right_metrics,
                "parameters_used": self.parameters
            }
            
            if affected_eyes:
                return {
                    "check": "red_eye",
                    "status": "FAILED",
                    "reason": f"Обнаружен эффект красных глаз в {' и '.join(affected_eyes)} глазу(ах)",
                    "details": details
                }
            else:
                return {
                    "check": "red_eye",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error during red eye check: {e}")
            return {
                "check": "red_eye",
                "status": "NEEDS_REVIEW",
                "reason": f"Ошибка при проверке красных глаз: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }
    
    def _check_eye_region(self, image: np.ndarray, eye_points: np.ndarray, eye_side: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Проверяет один глаз на наличие эффекта "красных глаз" с расширенным анализом.
        
        Args:
            image: Изображение
            eye_points: Координаты точек глаза (6 точек)
            eye_side: Строка "left" или "right" для обозначения глаза
            
        Returns:
            Tuple из (результат_проверки, метрики)
        """
        # Создаем словарь для хранения метрик и результатов анализа
        metrics = {
            "eye_side": eye_side,
            "detection_methods": {},
            "red_eye_detected": False,
            "roi_info": {}
        }
        
        # Получаем регион интереса (ROI) для глаза
        x, y, w, h = cv2.boundingRect(eye_points)
        
        # Расширяем область немного
        margin = int(max(w, h) * 0.2)
        x_with_margin = max(0, x - margin)
        y_with_margin = max(0, y - margin)
        w_with_margin = min(image.shape[1] - x_with_margin, w + 2*margin)
        h_with_margin = min(image.shape[0] - y_with_margin, h + 2*margin)
        
        # Сохраняем информацию о ROI для отладки
        metrics["roi_info"] = {
            "original": {"x": x, "y": y, "width": w, "height": h},
            "with_margin": {"x": x_with_margin, "y": y_with_margin, 
                           "width": w_with_margin, "height": h_with_margin}
        }
        
        eye_roi = image[y_with_margin:y_with_margin+h_with_margin, 
                       x_with_margin:x_with_margin+w_with_margin]
        if eye_roi.size == 0:
            metrics["error"] = "Empty ROI after applying margins"
            return False, metrics
        
        # Размеры ROI для отладки
        metrics["roi_info"]["roi_shape"] = eye_roi.shape
    
        # Вычисляем центр и радиус для круговой маски зрачка
        eye_center_x = w_with_margin // 2
        eye_center_y = h_with_margin // 2
        
        # Определяем размер зрачка - обычно 20-30% от размера глаза
        pupil_radius = int(min(w_with_margin, h_with_margin) * self.parameters["pupil_relative_size"])
        metrics["roi_info"]["pupil_radius"] = pupil_radius
        
        # Создаем маску для зрачка (центральная часть глаза)
        pupil_mask = np.zeros((h_with_margin, w_with_margin), dtype=np.uint8)
        cv2.circle(pupil_mask, (eye_center_x, eye_center_y), pupil_radius, 255, -1)
        
        # Разделяем на каналы RGB
        b, g, r = cv2.split(eye_roi)
        
        # Применяем маску зрачка
        pupil_r = cv2.bitwise_and(r, r, mask=pupil_mask)
        pupil_g = cv2.bitwise_and(g, g, mask=pupil_mask)
        pupil_b = cv2.bitwise_and(b, b, mask=pupil_mask)
        
        # Вычисляем метрики для зрачка
        pupil_pixels = np.count_nonzero(pupil_mask)
        if pupil_pixels == 0:
            metrics["error"] = "No pupil pixels detected in mask"
            return False, metrics
            
        r_mean = np.sum(pupil_r) / pupil_pixels
        g_mean = np.sum(pupil_g) / pupil_pixels
        b_mean = np.sum(pupil_b) / pupil_pixels
        
        # Сохраняем основные метрики RGB
        metrics["rgb_analysis"] = {
            "r_mean": float(r_mean),
            "g_mean": float(g_mean),
            "b_mean": float(b_mean),
            "r_to_g_ratio": float(r_mean / (g_mean + 0.1)),
            "r_to_b_ratio": float(r_mean / (b_mean + 0.1))
        }
        
        # Получаем параметры из конфигурации
        red_threshold = self.parameters["red_threshold"]
        red_ratio_threshold = self.parameters["red_ratio_threshold"]
        min_red_pixel_ratio = self.parameters["min_red_pixel_ratio"]
        
        # Логирование для отладки
        logger.debug(f"Red eye check for {eye_side} eye: R={r_mean:.1f}, G={g_mean:.1f}, B={b_mean:.1f}")
        
        # МЕТОД 1: Детекция красных глаз по доминированию красного канала и его яркости
        method1_result = (r_mean > red_threshold and 
                         r_mean / (g_mean + 0.1) > red_ratio_threshold and 
                         r_mean / (b_mean + 0.1) > red_ratio_threshold)
        
        metrics["detection_methods"]["rgb_mean_ratios"] = {
            "result": method1_result,
            "r_mean_exceeds_threshold": r_mean > red_threshold,
            "r_to_g_exceeds_threshold": r_mean / (g_mean + 0.1) > red_ratio_threshold,
            "r_to_b_exceeds_threshold": r_mean / (b_mean + 0.1) > red_ratio_threshold
        }
        
        # МЕТОД 2: Проверка на наличие ярких красных пикселей
        high_red_pixels = np.sum((pupil_r > red_threshold) & 
                                (pupil_r > red_ratio_threshold * pupil_g) & 
                                (pupil_r > red_ratio_threshold * pupil_b))
        red_pixel_ratio = high_red_pixels / max(1, pupil_pixels)
        
        method2_result = red_pixel_ratio > min_red_pixel_ratio
        
        metrics["detection_methods"]["bright_red_pixels"] = {
            "result": method2_result,
            "high_red_pixels_count": int(high_red_pixels),
            "total_pupil_pixels": int(pupil_pixels),
            "red_pixel_ratio": float(red_pixel_ratio),
            "threshold": float(min_red_pixel_ratio)
        }
        
        if method2_result:
            logger.info(f"Red eye detected in {eye_side} eye via pixel ratio: {red_pixel_ratio:.3f}")
        
        # МЕТОД 3: Анализ в HSV цветовом пространстве, если включен
        method3_result = False
        if self.parameters["hsv_detection"]:
            # Конвертируем в HSV для лучшего обнаружения красного цвета
            eye_hsv = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2HSV)
            
            # Красный цвет в HSV находится в двух диапазонах
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 70, 50])
            upper_red2 = np.array([180, 255, 255])
            
            # Создаем маски для красного цвета
            red_mask1 = cv2.inRange(eye_hsv, lower_red1, upper_red1)
            red_mask2 = cv2.inRange(eye_hsv, lower_red2, upper_red2)
            red_mask = cv2.bitwise_or(red_mask1, red_mask2)
            
            # Применяем маску зрачка
            pupil_red_mask = cv2.bitwise_and(red_mask, pupil_mask)
            
            # Оцениваем долю красных пикселей в зрачке
            hsv_red_pixels = np.count_nonzero(pupil_red_mask)
            hsv_red_ratio = hsv_red_pixels / max(1, pupil_pixels)
            
            method3_result = hsv_red_ratio > min_red_pixel_ratio
            
            metrics["detection_methods"]["hsv_analysis"] = {
                "result": method3_result,
                "hsv_red_pixels": int(hsv_red_pixels),
                "hsv_red_ratio": float(hsv_red_ratio),
                "threshold": float(min_red_pixel_ratio)
            }
            
            if method3_result:
                logger.info(f"Red eye detected in {eye_side} eye via HSV analysis: {hsv_red_ratio:.3f}")
        
        # Объединяем результаты всех методов
        is_red_eye = method1_result or method2_result
        if self.parameters["hsv_detection"]:
            is_red_eye = is_red_eye or method3_result
        
        metrics["red_eye_detected"] = is_red_eye
        
        if is_red_eye:
            logger.info(f"Red eye detected in {eye_side} eye: RGB=({r_mean:.1f}, {g_mean:.1f}, {b_mean:.1f}), "
                       f"Pixel ratio={red_pixel_ratio:.3f}")
        
        return is_red_eye, metrics
    
    def _save_debug_info(self, image: np.ndarray, eye_regions: Optional[List[np.ndarray]], debug_info: Dict[str, Any]) -> None:
        """
        Сохраняет отладочную информацию, изображения и логи.
        
        Args:
            image: Исходное изображение
            eye_regions: Список массивов с координатами глаз или None
            debug_info: Словарь с отладочной информацией
        """
        if not self.parameters["save_debug_images"]:
            return
        
        try:
            # Создаем уникальное имя файла на основе времени
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            base_name = f"{self.parameters['debug_output_dir']}/red_eye_check_{timestamp}"
            
            # Сохраняем JSON с результатами анализа
            with open(f"{base_name}_data.json", 'w') as f:
                json.dump(debug_info, f, indent=2, default=lambda x: str(x) if isinstance(x, np.ndarray) else x)
            
            if image is not None:
                # Создаем копию изображения для визуализации
                debug_image = image.copy()
                
                # Если есть информация о глазах, визуализируем их
                if eye_regions is not None:
                    for i, eye_points in enumerate(eye_regions):
                        eye_side = "left" if i == 0 else "right"
                        # Рисуем контур глаза
                        color = (0, 0, 255) if eye_side in debug_info.get("affected_eyes", []) else (0, 255, 0)
                        cv2.polylines(debug_image, [eye_points], True, color, 2)
                        
                        # Получаем ROI глаза для отладки
                        x, y, w, h = cv2.boundingRect(eye_points)
                        margin = int(max(w, h) * 0.2)
                        x_with_margin = max(0, x - margin)
                        y_with_margin = max(0, y - margin)
                        w_with_margin = min(image.shape[1] - x_with_margin, w + 2*margin)
                        h_with_margin = min(image.shape[0] - y_with_margin, h + 2*margin)
                        
                        # Рисуем прямоугольник ROI
                        cv2.rectangle(debug_image, (x_with_margin, y_with_margin), 
                                     (x_with_margin + w_with_margin, y_with_margin + h_with_margin), 
                                     color, 1)
                        
                        # Рисуем центр зрачка и его примерную область
                        center_x = x_with_margin + w_with_margin // 2
                        center_y = y_with_margin + h_with_margin // 2
                        pupil_radius = int(min(w_with_margin, h_with_margin) * self.parameters["pupil_relative_size"])
                        cv2.circle(debug_image, (center_x, center_y), pupil_radius, color, 1)
                        
                        # Добавляем текст с результатом
                        result_text = "RED EYE" if eye_side in debug_info.get("affected_eyes", []) else "OK"
                        cv2.putText(debug_image, f"{eye_side}: {result_text}", 
                                   (x_with_margin, y_with_margin - 5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
                
                # Сохраняем изображение
                cv2.imwrite(f"{base_name}_visualization.jpg", debug_image)
                
                # Если обнаружены красные глаза, сохраняем индивидуальные ROI для каждого глаза
                if "affected_eyes" in debug_info and debug_info["affected_eyes"]:
                    for i, eye_points in enumerate(eye_regions):
                        eye_side = "left" if i == 0 else "right"
                        if eye_side in debug_info["affected_eyes"]:
                            x, y, w, h = cv2.boundingRect(eye_points)
                            margin = int(max(w, h) * 0.2)
                            x_with_margin = max(0, x - margin)
                            y_with_margin = max(0, y - margin)
                            w_with_margin = min(image.shape[1] - x_with_margin, w + 2*margin)
                            h_with_margin = min(image.shape[0] - y_with_margin, h + 2*margin)
                            
                            eye_roi = image[y_with_margin:y_with_margin+h_with_margin, 
                                           x_with_margin:x_with_margin+w_with_margin]
                            
                            # Сохраняем оригинальный ROI
                            cv2.imwrite(f"{base_name}_{eye_side}_roi.jpg", eye_roi)
                            
                            # Создаем визуализацию каналов RGB
                            b, g, r = cv2.split(eye_roi)
                            
                            # Увеличиваем контрастность для лучшей видимости
                            r_enhanced = cv2.equalizeHist(r)
                            g_enhanced = cv2.equalizeHist(g)
                            b_enhanced = cv2.equalizeHist(b)
                            
                            # Сохраняем каналы как отдельные изображения
                            cv2.imwrite(f"{base_name}_{eye_side}_red_channel.jpg", r)
                            cv2.imwrite(f"{base_name}_{eye_side}_green_channel.jpg", g)
                            cv2.imwrite(f"{base_name}_{eye_side}_blue_channel.jpg", b)
                            
                            # Если используется HSV анализ, сохраняем и его результаты
                            if self.parameters["hsv_detection"]:
                                eye_hsv = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2HSV)
                                h, s, v = cv2.split(eye_hsv)
                                cv2.imwrite(f"{base_name}_{eye_side}_hsv_hue.jpg", h)
                                cv2.imwrite(f"{base_name}_{eye_side}_hsv_saturation.jpg", s)
                                cv2.imwrite(f"{base_name}_{eye_side}_hsv_value.jpg", v)
                                
                                # Создаем цветовую маску красного
                                lower_red1 = np.array([0, 70, 50])
                                upper_red1 = np.array([10, 255, 255])
                                lower_red2 = np.array([170, 70, 50])
                                upper_red2 = np.array([180, 255, 255])
                                
                                red_mask1 = cv2.inRange(eye_hsv, lower_red1, upper_red1)
                                red_mask2 = cv2.inRange(eye_hsv, lower_red2, upper_red2)
                                red_mask = cv2.bitwise_or(red_mask1, red_mask2)
                                
                                cv2.imwrite(f"{base_name}_{eye_side}_red_mask.jpg", red_mask)
            
            logger.info(f"Saved red eye debug info to {base_name}_*")
            
        except Exception as e:
            logger.error(f"Error saving debug information: {e}")


def import_traceback_if_available():
    """
    Импортирует модуль traceback для сохранения стека вызовов, если доступен.
    """
    try:
        import traceback
        return traceback.format_exc()
    except ImportError:
        return "Traceback module not available"