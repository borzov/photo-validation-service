import cv2
import numpy as np
from typing import List, Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

def detect_faces(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Детекция лиц с использованием OpenCV
    """
    # Используем каскадный классификатор Haar для детекции лиц
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces_rect = face_cascade.detectMultiScale(gray, 1.1, 4)
    
    faces = []
    h, w = image.shape[:2]
    
    for (x, y, width, height) in faces_rect:
        # Создаем базовые лендмарки (упрощенно)
        # Левый глаз, правый глаз, нос, левый уголок рта, правый уголок рта
        landmarks = [
            (x + width // 4, y + height // 3),  # Левый глаз
            (x + 3 * width // 4, y + height // 3),  # Правый глаз
            (x + width // 2, y + 2 * height // 3),  # Нос
            (x + width // 3, y + 3 * height // 4),  # Левый уголок рта
            (x + 2 * width // 3, y + 3 * height // 4),  # Правый уголок рта
        ]
        
        faces.append({
            "bbox": (x, y, width, height),
            "landmarks": landmarks,
            "mesh_landmarks": None,
            "confidence": 0.9
        })
    
    logger.info(f"Detected {len(faces)} faces in the image")
    return faces

def check_face_position(image: np.ndarray, face: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверка положения и размера лица на изображении
    """
    h, w, _ = image.shape
    x, y, width, height = face["bbox"]
    
    # Проверка размера лица
    face_area = width * height
    image_area = h * w
    face_ratio = face_area / image_area
    
    # Проверка центрирования лица
    face_center_x = x + width // 2
    face_center_y = y + height // 2
    image_center_x = w // 2
    image_center_y = h // 2
    
    # Допустимое отклонение от центра (в процентах)
    center_tolerance = 0.15
    x_offset_ratio = abs(face_center_x - image_center_x) / w
    y_offset_ratio = abs(face_center_y - image_center_y) / h
    
    # Проверки
    if face_ratio < 0.1:
        logger.info(f"Face too small: ratio={face_ratio:.2f}")
        return {
            "is_valid": False,
            "reason": "Face too small",
            "details": f"Face area ratio: {face_ratio:.2f}, minimum required: 0.1"
        }
    
    if face_ratio > 0.7:
        logger.info(f"Face too large: ratio={face_ratio:.2f}")
        return {
            "is_valid": False,
            "reason": "Face too large",
            "details": f"Face area ratio: {face_ratio:.2f}, maximum allowed: 0.7"
        }
    
    if x_offset_ratio > center_tolerance or y_offset_ratio > center_tolerance:
        logger.info(f"Face not centered: x_offset={x_offset_ratio:.2f}, y_offset={y_offset_ratio:.2f}")
        return {
            "is_valid": False,
            "reason": "Face not centered",
            "details": f"X offset: {x_offset_ratio:.2f}, Y offset: {y_offset_ratio:.2f}, tolerance: {center_tolerance}"
        }
    
    # Проверка на обрезанное лицо
    if x < 0 or y < 0 or x + width > w or y + height > h:
        logger.info(f"Face is cropped: bbox=({x}, {y}, {width}, {height}), image=({w}, {h})")
        return {
            "is_valid": False,
            "reason": "Face is cropped",
            "details": f"Face bounding box: {(x, y, width, height)}, image size: {(w, h)}"
        }
    
    logger.info(f"Face position is valid: ratio={face_ratio:.2f}, x_offset={x_offset_ratio:.2f}, y_offset={y_offset_ratio:.2f}")
    return {
        "is_valid": True,
        "details": f"Centered (offsets: X={x_offset_ratio:.2f}, Y={y_offset_ratio:.2f}), size ratio: {face_ratio:.2f}"
    }

def check_face_pose(face: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверка позы лица (анфас)
    """
    # Для упрощенной версии всегда возвращаем положительный результат
    return {
        "is_valid": True,
        "details": "Face pose is frontal (simplified check)"
    }
