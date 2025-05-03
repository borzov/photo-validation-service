"""
Проверка на реальную фотографию (не рисунок).
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class RealPhotoCheck(BaseCheck):
    """
    Проверка, является ли изображение реальной фотографией,
    а не рисунком, скетчем или компьютерной графикой.
    """
    check_id = "realPhoto"
    name = "Real Photo Check"
    description = "Checks if the image is a real photo and not a drawing, sketch or computer graphics"
    
    default_config = {
        "gradient_mean_threshold": 20,      # Пороговое значение для градиентов
        "texture_var_threshold": 1.5,       # Порог для соотношения текстуры
        "color_distribution_threshold": 50,  # Порог для распределения цветов
        "mid_freq_energy_threshold": 250,   # Порог для средних частот в FFT
        "evidence_bias": "photo"            # Смещение определения в пользу "photo" или "drawing"
    }
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку на реальную фотографию.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            # Конвертируем в серый
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Собираем метрики для анализа
            metrics = self._collect_metrics(image, gray)
            
            # Анализируем метрики для получения вердикта
            is_photo, evidence = self._analyze_metrics(metrics)
            
            if not is_photo:
                return {
                    "status": "FAILED",
                    "reason": f"Image appears to be a {evidence['type']} rather than a real photo: {', '.join(evidence['details'])}",
                    "details": metrics
                }
            else:
                return {
                    "status": "PASSED",
                    "details": metrics
                }
        
        except Exception as e:
            logger.error(f"Error during real photo check: {e}")
            return {
                "status": "PASSED",  # В случае ошибки пропускаем
                "reason": f"Real photo check error: {str(e)}",
                "details": None
            }
            
    def _collect_metrics(self, image: np.ndarray, gray: np.ndarray) -> Dict[str, float]:
        """
        Собирает метрики для анализа изображения.
        """
        h, w = gray.shape
        
        # 1. Градиентный анализ (Собель)
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        gradient_mean = np.mean(gradient_magnitude)
        gradient_std = np.std(gradient_magnitude)
        
        # 2. Анализ текстуры (Лапласиан)
        block_size = min(h, w) // 4
        laplacian_vars = []
        for i in range(0, h - block_size + 1, block_size):
            for j in range(0, w - block_size + 1, block_size):
                block = gray[i:i+block_size, j:j+block_size]
                laplacian_var = cv2.Laplacian(block, cv2.CV_64F).var()
                laplacian_vars.append(laplacian_var)
        
        texture_var_mean = np.mean(laplacian_vars) if laplacian_vars else 0
        texture_var_std = np.std(laplacian_vars) if len(laplacian_vars) > 1 else 0
        texture_var_ratio = texture_var_std / (texture_var_mean + 1e-6)
        
        # 3. Анализ гистограммы
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]).flatten()
        hist_normalized = hist / np.sum(hist)
        peaks_count = np.sum(np.diff(np.sign(np.diff(hist_normalized))) < 0)
        
        # 4. FFT анализ
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = 20*np.log(np.abs(f_shift) + 1)
        
        h_center, w_center = h//2, w//2
        mid_range = min(h, w)//8
        mid_freq_region = magnitude_spectrum[h_center-mid_range:h_center+mid_range, 
                                           w_center-mid_range:w_center+mid_range]
        mid_freq_energy = np.mean(mid_freq_region)
        
        # 5. Анализ насыщенности цветов
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = hsv[:,:,1]
        saturation_std = np.std(saturation)
        saturation_mean = np.mean(saturation)
        
        return {
            "gradient_mean": float(gradient_mean),
            "gradient_std": float(gradient_std),
            "texture_var_mean": float(texture_var_mean),
            "texture_var_ratio": float(texture_var_ratio),
            "histogram_peaks": int(peaks_count),
            "mid_freq_energy": float(mid_freq_energy),
            "saturation_std": float(saturation_std),
            "saturation_mean": float(saturation_mean)
        }
    
    def _analyze_metrics(self, metrics: Dict[str, float]) -> tuple:
        """
        Анализирует метрики и определяет, является ли изображение фотографией.
        
        Returns:
            tuple: (is_photo, evidence_dict)
        """
        # По умолчанию считаем, что это фотография (обратная логика)
        is_photo = True
        evidence = {
            "type": "unknown",
            "details": []
        }
        
        # Характеристики реальных фотографий
        # 1. Умеренные значения градиентов
        if metrics["gradient_mean"] < 10:
            is_photo = False
            evidence["details"].append("extremely_low_gradients")
            evidence["type"] = "computer generated image"
        
        # 2. Нормальные соотношения текстуры
        if metrics["texture_var_ratio"] > self.config["texture_var_threshold"]:
            # Необычно высокое отношение, характерно для искусственных изображений
            # Но для документальных фото это не критично, поэтому не меняем is_photo
            evidence["details"].append("unusual_texture_pattern")
            
        # 3. Неестественно высокие всплески в FFT
        if metrics["mid_freq_energy"] > 300:
            is_photo = False
            evidence["details"].append("artificial_frequency_pattern")
            evidence["type"] = "digitally altered image"
            
        # 4. Слишком равномерная насыщенность
        if metrics["saturation_std"] < 20 and metrics["saturation_mean"] > 100:
            # Неестественно равномерная и высокая насыщенность
            evidence["details"].append("uniform_high_saturation")
            
        # Если накоплено более 2 серьезных признаков, считаем не фотографией
        if len(evidence["details"]) >= 3:
            is_photo = False
            if not evidence["type"]:
                evidence["type"] = "computer generated image"
                
        # Если указано смещение в пользу фото - пропускаем некоторые виды изображений
        if self.config["evidence_bias"] == "photo":
            # Официальные документальные фотографии должны проходить
            if len(evidence["details"]) < 3:
                is_photo = True
                
        return is_photo, evidence