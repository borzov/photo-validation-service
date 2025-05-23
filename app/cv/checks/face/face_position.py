"""
Модуль для проверки положения лица на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class FacePositionCheck(BaseCheck):
    """
    Проверка положения и размера лица на изображении.
    """
    check_id = "facePosition"
    name = "Проверка положения лица"
    description = "Проверяет правильность положения и размера лица на изображении"
    
    default_config = {
        "face_min_area_ratio": 0.05,
        "face_max_area_ratio": 0.8,
        "face_center_tolerance": 0.4,
        "min_width_ratio": 0.15,
        "min_height_ratio": 0.2,
        "min_margin_ratio": 0.03,
        "boundary_tolerance": 5
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку положения лица на изображении.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать context["face"]["bbox"]
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("No face found in context for face position check")
            return {
                "status": "SKIPPED",
                "reason": "No face detected",
                "details": None
            }
        
        try:
            h, w, _ = image.shape
            x, y, width, height = context["face"]["bbox"]
            
            # Проверка размера лица
            face_area = width * height
            image_area = h * w
            face_ratio = face_area / image_area
            
            # Проверка центрирования лица
            face_center_x = x + width / 2
            face_center_y = y + height / 2
            image_center_x = w / 2
            image_center_y = h / 2
            
            # Расчет отклонения от центра
            effective_tolerance_x = w * self.config["face_center_tolerance"]
            effective_tolerance_y = h * self.config["face_center_tolerance"]
            
            x_offset = abs(face_center_x - image_center_x)
            y_offset = abs(face_center_y - image_center_y)
            
            # Детали для ответа
            details = {
                "face_bbox": [int(x), int(y), int(width), int(height)],
                "face_area_ratio": round(face_ratio, 3),
                "center_offset_x_px": round(x_offset, 1),
                "center_offset_y_px": round(y_offset, 1),
                "image_size": [w, h]
            }
            
            # Список причин для отклонения
            reasons = []
            
            # Проверка площади лица
            min_area_ratio = self.config["face_min_area_ratio"]
            max_area_ratio = self.config["face_max_area_ratio"]
            
            if face_ratio < min_area_ratio:
                reasons.append(f"Face area ratio {face_ratio:.3f} too small (min: {min_area_ratio:.3f})")
            if face_ratio > max_area_ratio:
                reasons.append(f"Face area ratio {face_ratio:.3f} too large (max: {max_area_ratio:.3f})")
            
            # Проверка центрирования
            if x_offset > effective_tolerance_x:
                reasons.append(f"Face X offset {x_offset:.1f}px exceeds tolerance {effective_tolerance_x:.1f}px")
            if y_offset > effective_tolerance_y:
                reasons.append(f"Face Y offset {y_offset:.1f}px exceeds tolerance {effective_tolerance_y:.1f}px")
            
            # Проверка близости к краям изображения
            boundary_tolerance = self.config["boundary_tolerance"]
            is_close_to_left = x < boundary_tolerance
            is_close_to_top = y < boundary_tolerance
            is_close_to_right = (x + width) > (w - boundary_tolerance)
            is_close_to_bottom = (y + height) > (h - boundary_tolerance)
            
            # Расчет отступов от краев изображения
            left_margin_ratio = x / w
            right_margin_ratio = (w - (x + width)) / w
            top_margin_ratio = y / h
            bottom_margin_ratio = (h - (y + height)) / h
            
            # Добавляем информацию о границах в детали
            details["margins"] = {
                "left": round(left_margin_ratio, 3),
                "right": round(right_margin_ratio, 3),
                "top": round(top_margin_ratio, 3),
                "bottom": round(bottom_margin_ratio, 3)
            }
            
            # Проверяем, касается ли лицо краев изображения
            if is_close_to_left:
                reasons.append(f"Face is cropped at left edge (margin: {left_margin_ratio:.3f})")
            if is_close_to_top:
                reasons.append(f"Face is cropped at top edge (margin: {top_margin_ratio:.3f})")
            if is_close_to_right:
                reasons.append(f"Face is cropped at right edge (margin: {right_margin_ratio:.3f})")
            if is_close_to_bottom:
                reasons.append(f"Face is cropped at bottom edge (margin: {bottom_margin_ratio:.3f})")
            
            # Проверка минимальных отступов
            min_margin_ratio = self.config["min_margin_ratio"]
            if (left_margin_ratio < min_margin_ratio or 
                right_margin_ratio < min_margin_ratio or 
                top_margin_ratio < min_margin_ratio or 
                bottom_margin_ratio < min_margin_ratio):
                if "Face is cropped" not in " ".join(reasons):
                    reasons.append(f"Face is too close to image boundary (minimum margin should be {min_margin_ratio:.0%})")
            
            # Проверка соотношений размеров
            portrait_ratio = h / w
            is_portrait = portrait_ratio > 1.3
            
            if is_portrait:
                min_width_ratio = self.config["min_width_ratio"] * 0.8  # Снижаем требования для портретных фото
                min_height_ratio = self.config["min_height_ratio"] * 0.8
                details["is_portrait"] = True
                details["portrait_ratio"] = round(portrait_ratio, 2)
            else:
                min_width_ratio = self.config["min_width_ratio"]
                min_height_ratio = self.config["min_height_ratio"]
            
            head_width_ratio = width / w
            head_height_ratio = height / h
            
            details["min_width_ratio"] = round(min_width_ratio, 2)
            details["min_height_ratio"] = round(min_height_ratio, 2)
            
            # Проверки на соответствие размеров головы требованиям
            # Если лицо достаточно большое, пропускаем эти проверки
            sufficient_face_ratio = 0.09  # 9% от площади изображения
            if face_ratio < sufficient_face_ratio:
                if head_width_ratio < min_width_ratio:
                    reasons.append(f"Head width {head_width_ratio:.2f} below minimum required ratio {min_width_ratio:.2f}")
                
                if head_height_ratio < min_height_ratio:
                    reasons.append(f"Head height {head_height_ratio:.2f} below minimum required ratio {min_height_ratio:.2f}")
            else:
                details["width_height_checks_skipped"] = True
                details["sufficient_face_ratio"] = sufficient_face_ratio
            
            # Финальный результат
            if reasons:
                logger.info(f"Face position invalid: {'; '.join(reasons)}")
                return {
                    "status": "FAILED",
                    "reason": "; ".join(reasons),
                    "details": details
                }
            else:
                logger.info("Face position is valid")
                return {
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error during face position check: {e}")
            return {
                "status": "FAILED",
                "reason": f"Face position check error: {str(e)}",
                "details": {"error": str(e)}
            }