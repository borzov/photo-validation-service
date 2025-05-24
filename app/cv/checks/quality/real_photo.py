"""
Проверка на реальную фотографию (не рисунок).
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.mixins import StandardCheckMixin
from app.core.logging import get_logger

logger = get_logger(__name__)

class RealPhotoCheck(StandardCheckMixin, BaseCheck):
    """
    Проверка, является ли изображение реальной фотографией,
    а не рисунком, скетчем или компьютерной графикой.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Return metadata for this check module."""
        return CheckMetadata(
            name="real_photo",
            display_name="Проверка реальности фото",
            description="Проверяет, является ли изображение реальной фотографией, а не рисунком, скетчем или компьютерной графикой",
            category="image_quality",
            version="1.0.0",
            author="Maxim Borzov",
            parameters=[
                CheckParameter(
                    name="gradient_mean_threshold",
                    type="int",
                    default=20,
                    description="Порог для анализа градиентов",
                    min_value=5,
                    max_value=100,
                    required=True
                ),
                CheckParameter(
                    name="texture_var_threshold",
                    type="float",
                    default=1.5,
                    description="Порог для анализа вариации текстуры",
                    min_value=0.5,
                    max_value=5.0,
                    required=True
                ),
                CheckParameter(
                    name="color_distribution_threshold",
                    type="int",
                    default=50,
                    description="Порог для анализа распределения цветов",
                    min_value=10,
                    max_value=200,
                    required=True
                ),
                CheckParameter(
                    name="mid_freq_energy_threshold",
                    type="int",
                    default=250,
                    description="Порог для энергии средних частот в FFT анализе",
                    min_value=100,
                    max_value=1000,
                    required=True
                ),
                CheckParameter(
                    name="evidence_bias",
                    type="str",
                    default="photo",
                    description="Смещение для определения реальной фотографии против рисунка",
                    choices=["photo", "drawing", "neutral"],
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Выполняет проверку на реальность фотографии.
        
        Args:
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результаты проверки
        """
        try:
            # Convert to grayscale for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # 1. Gradient analysis - real photos have more complex gradients
            grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            gradient_mean = np.mean(gradient_magnitude)
            
            # 2. Texture analysis - real photos have more texture variation
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            texture_variance = np.var(laplacian)
            
            # 3. Color distribution analysis
            color_std = np.std(image, axis=(0, 1))
            color_distribution_score = np.mean(color_std)
            
            # 4. FFT analysis for frequency content
            fft = np.fft.fft2(gray)
            fft_shifted = np.fft.fftshift(fft)
            magnitude_spectrum = np.abs(fft_shifted)
            
            # Focus on mid-frequency content (real photos have more)
            h, w = magnitude_spectrum.shape
            center_y, center_x = h // 2, w // 2
            mid_freq_region = magnitude_spectrum[center_y-h//4:center_y+h//4, 
                                               center_x-w//4:center_x+w//4]
            mid_freq_energy = np.mean(mid_freq_region)
            
            # Get thresholds from parameters
            gradient_threshold = self.parameters["gradient_mean_threshold"]
            texture_threshold = self.parameters["texture_var_threshold"]
            color_threshold = self.parameters["color_distribution_threshold"]
            freq_threshold = self.parameters["mid_freq_energy_threshold"]
            evidence_bias = self.parameters["evidence_bias"]
            
            details = {
                "gradient_mean": float(gradient_mean),
                "texture_variance": float(texture_variance),
                "color_distribution_score": float(color_distribution_score),
                "mid_freq_energy": float(mid_freq_energy),
                "thresholds": {
                    "gradient": gradient_threshold,
                    "texture": texture_threshold,
                    "color": color_threshold,
                    "frequency": freq_threshold
                },
                "parameters_used": self.parameters
            }
            
            # Evidence scoring
            photo_evidence = 0
            drawing_evidence = 0
            
            if gradient_mean > gradient_threshold:
                photo_evidence += 1
            else:
                drawing_evidence += 1
                
            if texture_variance > texture_threshold:
                photo_evidence += 1
            else:
                drawing_evidence += 1
                
            if color_distribution_score > color_threshold:
                photo_evidence += 1
            else:
                drawing_evidence += 1
                
            if mid_freq_energy > freq_threshold:
                photo_evidence += 1
            else:
                drawing_evidence += 1
            
            # Apply bias if set
            if evidence_bias == "photo":
                photo_evidence += 0.5
            elif evidence_bias == "drawing":
                drawing_evidence += 0.5
            
            details.update({
                "photo_evidence": photo_evidence,
                "drawing_evidence": drawing_evidence,
                "is_real_photo": photo_evidence > drawing_evidence
            })
            
            # Determine result
            if photo_evidence > drawing_evidence:
                return {
                    "check": "real_photo",
                    "status": "PASSED",
                    "details": details
                }
            else:
                reasons = []
                if gradient_mean <= gradient_threshold:
                    reasons.append(f"Низкая сложность градиентов ({gradient_mean:.1f} <= {gradient_threshold})")
                if texture_variance <= texture_threshold:
                    reasons.append(f"Низкая вариация текстуры ({texture_variance:.1f} <= {texture_threshold})")
                if color_distribution_score <= color_threshold:
                    reasons.append(f"Ограниченное распределение цветов ({color_distribution_score:.1f} <= {color_threshold})")
                if mid_freq_energy <= freq_threshold:
                    reasons.append(f"Низкое содержание частот ({mid_freq_energy:.1f} <= {freq_threshold})")
                
                return {
                    "check": "real_photo",
                    "status": "FAILED",
                    "reason": f"Изображение похоже на рисунок/графику: {'; '.join(reasons)}",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Ошибка при проверке реальности фото: {e}")
            return {
                "check": "real_photo",
                "status": "NEEDS_REVIEW",
                "reason": f"Ошибка при проверке реальности фото: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }