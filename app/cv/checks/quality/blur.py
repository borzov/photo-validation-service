"""
Проверка размытости изображения (для тестов).
Упрощенная версия BlurCheck для совместимости с тестами.
"""
import cv2
import numpy as np
from typing import Dict, Any


class BlurCheck:
    """
    Упрощенная проверка размытости для тестов.
    """
    name = "blur"
    
    def check(self, image: np.ndarray, context) -> 'CheckResult':
        """
        Проверка размытости изображения.
        """
        try:
            # Конвертируем в серый
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Вычисляем Лапласиан
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            blur_score = float(laplacian.var())
            
            # Получаем threshold из настроек
            if hasattr(context, 'settings'):
                threshold = context.settings.get("blur_threshold", 100)
            else:
                threshold = context.get("blur_threshold", 100)
            
            passed = blur_score > threshold
            message = f"Blur score: {blur_score:.2f}, threshold: {threshold}"
            
            # Результат для тестов
            class CheckResult:
                def __init__(self, passed, blur_score, message):
                    self.passed = passed
                    self.blur_score = blur_score
                    self.message = message
            
            return CheckResult(passed, blur_score, message)
            
        except Exception as e:
            class CheckResult:
                def __init__(self, passed, blur_score, message):
                    self.passed = passed
                    self.blur_score = blur_score
                    self.message = message
            
            return CheckResult(False, 0.0, f"Error: {str(e)}")


class BrightnessCheck:
    """
    Упрощенная проверка яркости для тестов.
    """
    name = "brightness"
    
    def check(self, image: np.ndarray, context) -> 'CheckResult':
        """
        Проверка яркости изображения.
        """
        try:
            # Вычисляем среднюю яркость
            brightness_score = float(np.mean(image))
            
            # Получаем пороги из настроек
            if hasattr(context, 'settings'):
                min_brightness = context.settings.get("brightness_min", 50)
                max_brightness = context.settings.get("brightness_max", 200)
            else:
                min_brightness = context.get("brightness_min", 50)
                max_brightness = context.get("brightness_max", 200)
            
            passed = min_brightness <= brightness_score <= max_brightness
            
            if brightness_score < min_brightness:
                message = f"Too dark: {brightness_score:.1f} < {min_brightness}"
            elif brightness_score > max_brightness:
                message = f"Too bright: {brightness_score:.1f} > {max_brightness}"
            else:
                message = f"Brightness OK: {brightness_score:.1f}"
            
            # Результат для тестов
            class CheckResult:
                def __init__(self, passed, brightness_score, message):
                    self.passed = passed
                    self.brightness_score = brightness_score
                    self.message = message
            
            return CheckResult(passed, brightness_score, message)
            
        except Exception as e:
            class CheckResult:
                def __init__(self, passed, brightness_score, message):
                    self.passed = passed
                    self.brightness_score = brightness_score
                    self.message = message
            
            return CheckResult(False, 0.0, f"Error: {str(e)}") 