"""
Модуль для проверки положения лица на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger

logger = get_logger(__name__)

class FacePositionCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка положения и размера лица на изображении.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="face_position",
            display_name="Позиция лица",
            description="Проверяет правильное положение и размер лица на изображении",
            category="face_detection",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="face_min_area_ratio",
                    type="float",
                    default=0.05,
                    description="Минимальное соотношение площади лица к изображению",
                    min_value=0.01,
                    max_value=0.5,
                    required=True
                ),
                CheckParameter(
                    name="face_max_area_ratio",
                    type="float",
                    default=0.8,
                    description="Максимальное соотношение площади лица к изображению",
                    min_value=0.5,
                    max_value=1.0,
                    required=True
                ),
                CheckParameter(
                    name="face_center_tolerance",
                    type="float",
                    default=0.4,
                    description="Допустимое отклонение центра лица от центра изображения",
                    min_value=0.1,
                    max_value=0.8,
                    required=True
                ),
                CheckParameter(
                    name="min_width_ratio",
                    type="float",
                    default=0.15,
                    description="Минимальное соотношение ширины лица к изображению",
                    min_value=0.05,
                    max_value=0.5,
                    required=True
                ),
                CheckParameter(
                    name="min_height_ratio",
                    type="float",
                    default=0.2,
                    description="Минимальное соотношение высоты лица к изображению",
                    min_value=0.05,
                    max_value=0.5,
                    required=True
                ),
                CheckParameter(
                    name="min_margin_ratio",
                    type="float",
                    default=0.03,
                    description="Минимальный отступ вокруг лица",
                    min_value=0.01,
                    max_value=0.2,
                    required=True
                ),
                CheckParameter(
                    name="boundary_tolerance",
                    type="int",
                    default=5,
                    description="Допуск для определения границ лица в пикселях",
                    min_value=1,
                    max_value=20,
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    # Инициализация и run() метод унаследованы из StandardCheckMixin

    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Проверяет положение лица на изображении.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать face["bbox"]
            
        Returns:
            Результаты проверки
        """
        # Проверяем контекст лица с bbox
        context_error = self._validate_face_bbox_context(context, "face_position")
        if context_error:
            return context_error

        try:
            h, w = image.shape[:2]
            x, y, width, height = context["face"]["bbox"]
            
            # Анализ позиции лица
            face_center_x = x + width // 2
            face_center_y = y + height // 2
            image_center_x = w // 2
            image_center_y = h // 2
            
            # Отклонения от центра
            center_deviation_x = abs(face_center_x - image_center_x) / w
            center_deviation_y = abs(face_center_y - image_center_y) / h
            
            # Соотношения размеров
            face_area_ratio = (width * height) / (w * h)
            width_ratio = width / w
            height_ratio = height / h
            
            # Отступы от границ
            left_margin_ratio = x / w
            right_margin_ratio = (w - x - width) / w
            top_margin_ratio = y / h
            bottom_margin_ratio = (h - y - height) / h
            
            # Получаем параметры
            min_area_ratio = self.parameters["face_min_area_ratio"]
            max_area_ratio = self.parameters["face_max_area_ratio"]
            center_tolerance = self.parameters["face_center_tolerance"]
            min_width_ratio = self.parameters["min_width_ratio"]
            min_height_ratio = self.parameters["min_height_ratio"]
            min_margin_ratio = self.parameters["min_margin_ratio"]
            boundary_tolerance = self.parameters["boundary_tolerance"]
            
            details = {
                "face_center": [face_center_x, face_center_y],
                "image_center": [image_center_x, image_center_y],
                "center_deviation": [center_deviation_x, center_deviation_y],
                "face_area_ratio": face_area_ratio,
                "width_ratio": width_ratio,
                "height_ratio": height_ratio,
                "margins": {
                    "left": left_margin_ratio,
                    "right": right_margin_ratio,
                    "top": top_margin_ratio,
                    "bottom": bottom_margin_ratio
                },
                "parameters_used": self.parameters
            }
            
            # Проверки
            issues = []
            
            # Размер лица
            if face_area_ratio < min_area_ratio:
                issues.append(f"Лицо слишком маленькое ({face_area_ratio:.1%} < {min_area_ratio:.1%})")
            elif face_area_ratio > max_area_ratio:
                issues.append(f"Лицо слишком большое ({face_area_ratio:.1%} > {max_area_ratio:.1%})")
            
            # Позиция лица
            if center_deviation_x > center_tolerance:
                issues.append(f"Лицо смещено по горизонтали ({center_deviation_x:.1%} > {center_tolerance:.1%})")
            if center_deviation_y > center_tolerance:
                issues.append(f"Лицо смещено по вертикали ({center_deviation_y:.1%} > {center_tolerance:.1%})")
            
            # Проверка обрезки
            is_close_to_boundary = (x <= boundary_tolerance or 
                                  y <= boundary_tolerance or
                                  x + width >= w - boundary_tolerance or
                                  y + height >= h - boundary_tolerance)
            
            if is_close_to_boundary:
                issues.append("Лицо обрезано по краю изображения")
            
            # Проверка минимальных отступов
            if (left_margin_ratio < min_margin_ratio or 
                right_margin_ratio < min_margin_ratio or 
                top_margin_ratio < min_margin_ratio or 
                bottom_margin_ratio < min_margin_ratio):
                issues.append(f"Лицо слишком близко к краю изображения (минимальный отступ: {min_margin_ratio:.0%})")
            
            # Проверка соотношений размеров
            if width_ratio < min_width_ratio:
                issues.append(f"Ширина лица слишком мала ({width_ratio:.1%} < {min_width_ratio:.1%})")
            if height_ratio < min_height_ratio:
                issues.append(f"Высота лица слишком мала ({height_ratio:.1%} < {min_height_ratio:.1%})")
            
            # Результат
            if issues:
                return {
                    "check": "face_position",
                    "status": "FAILED",
                    "reason": "; ".join(issues),
                    "details": details
                }
            else:
                return {
                    "check": "face_position",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            return self._create_error_result("face_position", e)