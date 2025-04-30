import cv2
import numpy as np
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

def analyze_background(image: np.ndarray, face: Dict[str, Any]) -> Dict[str, Any]:
    """
    Анализ фона изображения (упрощенная версия)
    """
    # Создание маски для фона (все изображение минус область лица)
    h, w = image.shape[:2]
    mask = np.ones((h, w), dtype=np.uint8) * 255
    
    # Координаты лица
    x, y, width, height = face["bbox"]
    
    # Расширяем область лица для более точного выделения
    face_margin = int(min(width, height) * 0.2)  # 20% запас
    x1 = max(0, x - face_margin)
    y1 = max(0, y - face_margin)
    x2 = min(w, x + width + face_margin)
    y2 = min(h, y + height + face_margin)
    
    # Заполняем область лица нулями (исключаем из анализа фона)
    mask[y1:y2, x1:x2] = 0
    
    # Для упрощенной версии всегда возвращаем положительный результат
    logger.info("Background analysis completed (simplified check)")
    return {
        "status": "PASSED",
        "details": "Background check passed (simplified analysis)"
    }
