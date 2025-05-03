"""
Модуль для проверки позы лица на изображении.
"""
import cv2
import numpy as np
from typing import Dict, Any, List, Tuple
import math
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class FacePoseCheck(BaseCheck):
    """
    Проверка позы лица (анфас) на изображении.
    """
    check_id = "facePose"
    name = "Face Pose Check"
    description = "Checks if the face is in a frontal pose (looking at camera)"
    
    default_config = {
        "max_yaw": 25.0,
        "max_pitch": 25.0,
        "max_roll": 25.0
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку позы лица.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок, должен содержать лицевые точки
            
        Returns:
            Результаты проверки
        """
        if not context or "face" not in context:
            logger.warning("No face found in context for face pose check")
            return {
                "status": "SKIPPED",
                "reason": "No face detected",
                "details": None
            }
        
        landmarks = context["face"].get("landmarks")
        if not landmarks or len(landmarks) < 68:
            logger.warning("Missing or incomplete landmarks for pose estimation")
            return {
                "status": "NEEDS_REVIEW",
                "reason": "Unable to estimate face pose due to missing landmarks",
                "details": None
            }
        
        try:
            h, w = image.shape[:2]
            
            # Оценка позы по лицевым точкам
            pose_angles = self._estimate_pose((h, w), landmarks)
            yaw = pose_angles["yaw"]
            pitch = pose_angles["pitch"]
            roll = pose_angles["roll"]
            
            details_str = f"Yaw: {yaw:.1f}, Pitch: {pitch:.1f}, Roll: {roll:.1f} (degrees)"
            logger.info(f"Estimated pose: {details_str}")
            
            # Проверка на соответствие требованиям
            max_yaw = self.config["max_yaw"]
            max_pitch = self.config["max_pitch"]
            max_roll = self.config["max_roll"]
            
            reasons = []
            if abs(yaw) > max_yaw:
                reasons.append(f"Yaw angle {yaw:.1f}° exceeds limit +/-{max_yaw}°")
            if abs(pitch) > max_pitch:
                reasons.append(f"Pitch angle {pitch:.1f}° exceeds limit +/-{max_pitch}°")
            
            # Учитываем "круговую" природу угла roll
            roll_deviation = min(abs(roll) % 180, 180 - (abs(roll) % 180))
            if roll_deviation > max_roll:
                reasons.append(f"Roll angle {roll:.1f}° exceeds limit (deviation: {roll_deviation:.1f}°, max: {max_roll}°)")
            
            # Дополнительные данные для ответа
            details = {
                "yaw": float(yaw),
                "pitch": float(pitch),
                "roll": float(roll),
                "thresholds": {
                    "max_yaw": max_yaw,
                    "max_pitch": max_pitch,
                    "max_roll": max_roll
                }
            }
            
            if reasons:
                return {
                    "status": "FAILED",
                    "reason": "; ".join(reasons),
                    "details": details
                }
            else:
                return {
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error during face pose check: {e}")
            return {
                "status": "FAILED",
                "reason": f"Face pose check error: {str(e)}",
                "details": {"error": str(e)}
            }
    
    def _estimate_pose(self, image_shape: Tuple[int, int], landmarks: List[Tuple[int, int]]) -> Dict[str, float]:
        """
        Оценка углов позы лица (yaw, pitch, roll) по лицевым точкам.
        
        Args:
            image_shape: Размеры изображения (высота, ширина)
            landmarks: Список координат лицевых точек
            
        Returns:
            Словарь с углами позы в градусах
        """
        h, w = image_shape
        focal_length = w  # Приближенное значение
        center = (w / 2, h / 2)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]],
             [0, focal_length, center[1]],
             [0, 0, 1]], dtype="double"
        )
        dist_coeffs = np.zeros((4, 1))  # Без искажений
        
        # 3D модель лица (ключевые точки)
        model_points = np.array([
            (0.0, 0.0, 0.0),              # Нос (Nose tip - 30)
            (0.0, -330.0, -65.0),         # Подбородок (Chin - 8)
            (-225.0, 170.0, -135.0),      # Лев. угол глаза (Left eye left corner - 36)
            (225.0, 170.0, -135.0),       # Прав. угол глаза (Right eye right corner - 45)
            (-150.0, -150.0, -125.0),     # Лев. угол рта (Left Mouth corner - 48)
            (150.0, -150.0, -125.0)       # Прав. угол рта (Right mouth corner - 54)
        ])
        
        # Проверяем, что индексы в диапазоне
        if len(landmarks) <= 54:
            logger.warning("Landmark array too short for pose estimation")
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
        
        # 2D точки изображения, соответствующие 3D модели
        image_points = np.array([
            landmarks[30],  # Нос
            landmarks[8],   # Подбородок
            landmarks[36],  # Лев. угол глаза
            landmarks[45],  # Прав. угол глаза
            landmarks[48],  # Лев. угол рта
            landmarks[54]   # Прав. угол рта
        ], dtype="double")
        
        try:
            (success, rotation_vector, translation_vector) = cv2.solvePnP(
                model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
            )
            
            if not success:
                logger.warning("solvePnP failed to estimate pose")
                return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}
                
            # Получаем матрицу поворота
            rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
            
            # Вычисляем углы Эйлера (порядок: ZYX)
            pitch = math.degrees(math.atan2(-rotation_matrix[2, 0], 
                                         math.sqrt(rotation_matrix[2, 1]**2 + rotation_matrix[2, 2]**2)))
            yaw = math.degrees(math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
            roll = math.degrees(math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2]))
            
            # Нормализуем углы в диапазон [-180, 180]
            if abs(pitch) > 90:
                pitch = 180 - abs(pitch) if pitch > 0 else -(180 - abs(pitch))
                
            yaw = (yaw + 180) % 360 - 180
            pitch = (pitch + 180) % 360 - 180
            roll = (roll + 180) % 360 - 180
            
            return {"yaw": yaw, "pitch": pitch, "roll": roll}
            
        except Exception as e:
            logger.error(f"Error in pose estimation: {e}")
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}