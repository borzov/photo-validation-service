"""
Module for checking image color mode.
"""
import cv2
import numpy as np
from typing import Dict, Any
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.core.logging import get_logger

logger = get_logger(__name__)

class ColorModeCheck(BaseCheck):
    """
    Check whether image is color or grayscale.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Return metadata for this check module."""
        return CheckMetadata(
            name="color_mode",
            display_name="Color Mode Check",
            description="Checks whether image is color or grayscale",
            category="image_quality",
            version="1.0.0",
            author="Photo Validation Team",
            parameters=[
                CheckParameter(
                    name="grayscale_saturation_threshold",
                    type="int",
                    default=15,
                    description="Saturation threshold for determining grayscale image",
                    min_value=5,
                    max_value=50,
                    required=True
                ),
                CheckParameter(
                    name="require_color",
                    type="bool",
                    default=True,
                    description="Whether to require color image (if False, any is accepted)",
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def __init__(self, **parameters):
        """Initialize with parameters."""
        self.parameters = parameters
        metadata = self.get_metadata()
        
        # Set default values
        for param in metadata.parameters:
            if param.name not in self.parameters:
                self.parameters[param.name] = param.default
        
        # Validate parameters
        if not self.validate_parameters(self.parameters):
            raise ValueError("Invalid parameters provided")
    
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Method for compatibility with old runner."""
        return self.check(image, context)
    
    def check(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Perform color mode check on the image.
        
        Args:
            image: Image to check
            context: Context with previous check results
            
        Returns:
            Check results
        """
        try:
            # Convert to HSV for saturation analysis
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Extract saturation channel (S)
            saturation = hsv[:, :, 1]
            
            # Calculate mean saturation
            mean_saturation = np.mean(saturation)
            
            threshold = self.parameters["grayscale_saturation_threshold"]
            require_color = self.parameters["require_color"]
            
            # Determine if image is color
            is_color = mean_saturation > threshold
            
            details = {
                "mean_saturation": float(mean_saturation),
                "threshold": threshold,
                "is_color": is_color,
                "parameters_used": self.parameters
            }
            
            # Check requirements compliance
            if require_color and not is_color:
                return {
                    "check": "color_mode",
                    "status": "FAILED",
                    "reason": f"Image is grayscale (saturation: {mean_saturation:.1f} <= {threshold})",
                    "details": details
                }
            elif not require_color or is_color:
                return {
                    "check": "color_mode", 
                    "status": "PASSED",
                    "details": details
                }
            else:
                return {
                    "check": "color_mode",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error checking color mode: {e}")
            return {
                "check": "color_mode",
                "status": "NEEDS_REVIEW",
                "reason": f"Error during color mode check: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }