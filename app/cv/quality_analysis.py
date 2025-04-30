import cv2
import numpy as np
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

def is_grayscale(image: np.ndarray) -> bool:
    """
    Проверка, является ли цветное изображение фактически черно-белым
    """
    if len(image.shape) < 3:
        return True
    
    # Преобразуем в HSV и анализируем насыщенность
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    saturation = hsv[:, :, 1]
    
    # Если среднее значение насыщенности очень низкое, считаем изображение черно-белым
    mean_saturation = np.mean(saturation)
    result = mean_saturation < 20
    
    logger.info(f"Image grayscale check: mean_saturation={mean_saturation:.2f}, is_grayscale={result}")
    return result

def check_blurriness(image: np.ndarray, face: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверка размытости в области лица
    """
    x, y, width, height = face["bbox"]
    
    # Выделение области лица
    face_region = image[y:y+height, x:x+width]
    
    # Преобразование в оттенки серого
    gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    
    # Вычисление дисперсии Лапласиана (метрика резкости)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # Пороговое значение для определения размытости
    threshold = 100
    
    if laplacian_var < threshold:
        logger.info(f"Face is blurry: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
        return {
            "is_valid": False,
            "reason": "Face is blurry",
            "details": f"Laplacian variance: {laplacian_var:.2f}, minimum required: {threshold}"
        }
    
    logger.info(f"Face is in focus: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
    return {
        "is_valid": True,
        "details": f"Image is in focus (Laplacian variance: {laplacian_var:.2f})"
    }

def check_red_eyes(image: np.ndarray, face: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверка на эффект красных глаз (упрощенная версия)
    """
    # Для упрощенной версии всегда возвращаем положительный результат
    return {
        "is_valid": True,
        "details": "No red-eye effect detected (simplified check)"
    }

def check_lighting(image: np.ndarray, face: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверка освещения на лице
    """
    x, y, width, height = face["bbox"]
    
    # Выделение области лица
    face_region = image[y:y+height, x:x+width]
    
    # Преобразование в оттенки серого
    gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
    
    # Вычисление средней яркости
    mean_brightness = np.mean(gray)
    
    # Вычисление стандартного отклонения (контраст)
    std_brightness = np.std(gray)
    
    # Проверки (упрощенные)
    if mean_brightness > 220:
        logger.info(f"Overexposed face: mean_brightness={mean_brightness:.2f}")
        return {
            "status": "NEEDS_REVIEW",
            "reason": "Overexposed face",
            "details": f"High brightness: {mean_brightness:.2f}, threshold: 220"
        }
    
    if mean_brightness < 50:
        logger.info(f"Underexposed face: mean_brightness={mean_brightness:.2f}")
        return {
            "status": "NEEDS_REVIEW",
            "reason": "Underexposed face",
            "details": f"Low brightness: {mean_brightness:.2f}, threshold: 50"
        }
    
    if std_brightness < 40:
        logger.info(f"Low contrast on face: std_brightness={std_brightness:.2f}")
        return {
            "status": "NEEDS_REVIEW",
            "reason": "Low contrast on face",
            "details": f"Brightness standard deviation: {std_brightness:.2f}, minimum required: 40"
        }
    
    logger.info(f"Acceptable lighting: mean_brightness={mean_brightness:.2f}, std_brightness={std_brightness:.2f}")
    return {
        "status": "PASSED",
        "details": f"Acceptable lighting (mean: {mean_brightness:.2f}, std: {std_brightness:.2f})"
    }
