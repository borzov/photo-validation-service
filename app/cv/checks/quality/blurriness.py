"""
Image blurriness detection check.
"""
import cv2
import numpy as np
from typing import Dict, Any
import math
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.core.logging import get_logger

logger = get_logger(__name__)

class BlurrinessCheck(BaseCheck):
    """
    Check for image blurriness in face region using Laplacian variance.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Return metadata for this check module."""
        return CheckMetadata(
            name="blurriness",
            display_name="Blurriness Check",
            description="Checks image blurriness in face region using Laplacian variance",
            category="image_quality",
            version="1.0.0",
            author="Photo Validation Team",
            parameters=[
                CheckParameter(
                    name="laplacian_threshold",
                    type="int",
                    default=40,
                    description="Minimum Laplacian variance value to consider image sharp",
                    min_value=10,
                    max_value=200,
                    required=True
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
        Perform blurriness check on the image.
        
        Args:
            image: Image to check
            context: Context with previous check results, should contain face["bbox"]
            
        Returns:
            Check results
        """
        if not context or "face" not in context or "bbox" not in context["face"]:
            logger.warning("Face region not found in context for blurriness check")
            return {
                "check": "blurriness",
                "status": "SKIPPED",
                "reason": "No face region available",
                "details": {"laplacian_variance": None}
            }

        # Get face region from context
        x, y, width, height = context["face"]["bbox"]
        face_region = image[y:y+height, x:x+width]

        if face_region.size == 0:
            logger.warning("Face region is empty, skipping blurriness check")
            return {
                "check": "blurriness",
                "status": "NEEDS_REVIEW",
                "reason": "Empty face region",
                "details": {"laplacian_variance": None}
            }
            
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian and its variance
            laplacian_var_np = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Check for NaN or Inf
            if laplacian_var_np is None or math.isnan(laplacian_var_np):
                laplacian_var = 0.0
                logger.warning("Laplacian variance resulted in NaN, treating as 0.0 for blur check")
            else:
                laplacian_var = float(laplacian_var_np)
                
            # Get threshold from configuration
            threshold = self.parameters["laplacian_threshold"]
            details = {
                "laplacian_variance": round(laplacian_var, 2),
                "threshold": threshold,
                "parameters_used": self.parameters
            }
            
            # Check blurriness
            if laplacian_var < threshold:
                logger.info(f"Face seems blurry: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
                return {
                    "check": "blurriness",
                    "status": "FAILED",
                    "reason": f"Image is blurry (Laplacian value: {laplacian_var:.2f} < {threshold})",
                    "details": details
                }
            else:
                logger.info(f"Face seems sharp: laplacian_var={laplacian_var:.2f}, threshold={threshold}")
                return {
                    "check": "blurriness",
                    "status": "PASSED",
                    "details": details
                }
        except Exception as e:
            logger.error(f"Error checking blurriness: {e}")
            return {
                "check": "blurriness",
                "status": "NEEDS_REVIEW",
                "reason": f"Error during blurriness check: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }