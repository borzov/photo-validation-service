"""
Модуль для определения позы лица на изображениях.
"""
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
import math
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.cv.checks.face.detector import estimate_pose
from app.core.logging import get_logger

logger = get_logger(__name__)

class FacePoseCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка позы лица (фронтальное положение) на изображении.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Возвращает метаданные для этого модуля проверки."""
        return CheckMetadata(
            name="face_pose",
            display_name="Проверка позы лица",
            description="Проверяет, что лицо повёрнуто фронтально (смотрит в камеру)",
            category="face_detection",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="max_yaw",
                    type="float",
                    default=25.0,
                    description="Максимальный поворот головы влево/вправо (в градусах)",
                    min_value=5.0,
                    max_value=90.0,
                    required=True
                ),
                CheckParameter(
                    name="max_pitch",
                    type="float",
                    default=25.0,
                    description="Максимальный наклон головы вверх/вниз (в градусах)",
                    min_value=5.0,
                    max_value=90.0,
                    required=True
                ),
                CheckParameter(
                    name="max_roll",
                    type="float",
                    default=25.0,
                    description="Максимальный поворот головы (в градусах)",
                    min_value=5.0,
                    max_value=90.0,
                    required=True
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform face pose check.
        
        Args:
            image: Image to check
            context: Context with previous check results, should contain facial landmarks
            
        Returns:
            Check results
        """
        if not context or "face" not in context:
            logger.warning("No face found in context for face pose check")
            return {
                "check": "face_pose",
                "status": "SKIPPED",
                "reason": "Лицо не обнаружено",
                "details": None
            }

        landmarks = context["face"].get("landmarks")
        if not landmarks or len(landmarks) < 68:
            logger.warning("Missing or incomplete landmarks for pose estimation")
            return {
                "check": "face_pose",
                "status": "NEEDS_REVIEW",
                "reason": "Невозможно оценить позу лица из-за отсутствующих ориентиров",
                "details": None
            }

        try:
            h, w = image.shape[:2]
            
            # Estimate pose from facial landmarks
            pose_angles = estimate_pose((h, w), landmarks)
            yaw = pose_angles["yaw"]
            pitch = pose_angles["pitch"]
            roll = pose_angles["roll"]
            
            details_str = f"Yaw: {yaw:.1f}, Pitch: {pitch:.1f}, Roll: {roll:.1f} (degrees)"
            logger.info(f"Estimated pose: {details_str}")
            
            # Check compliance with requirements
            max_yaw = self.parameters["max_yaw"]
            max_pitch = self.parameters["max_pitch"]
            max_roll = self.parameters["max_roll"]
            
            reasons = []
            if abs(yaw) > max_yaw:
                reasons.append(f"Поворот головы {yaw:.1f}° превышает предел ±{max_yaw}°")
            if abs(pitch) > max_pitch:
                reasons.append(f"Наклон головы {pitch:.1f}° превышает предел ±{max_pitch}°")

            # Account for "circular" nature of roll angle
            roll_deviation = min(abs(roll) % 180, 180 - (abs(roll) % 180))
            if roll_deviation > max_roll:
                reasons.append(f"Поворот головы {roll:.1f}° превышает предел (отклонение: {roll_deviation:.1f}°, максимум: {max_roll}°)")

            # Additional data for response
            details = {
                "yaw": float(yaw),
                "pitch": float(pitch),
                "roll": float(roll),
                "thresholds": {
                    "max_yaw": max_yaw,
                    "max_pitch": max_pitch,
                    "max_roll": max_roll
                },
                "parameters_used": self.parameters
            }
            
            if reasons:
                return {
                    "check": "face_pose",
                    "status": "FAILED",
                    "reason": "; ".join(reasons),
                    "details": details
                }
            else:
                return {
                    "check": "face_pose",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error during face pose check: {e}")
            return {
                "check": "face_pose",
                "status": "FAILED",
                "reason": f"Ошибка при проверке позы лица: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }