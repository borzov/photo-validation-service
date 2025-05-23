"""
Module for counting faces in image.
"""
import cv2
import numpy as np
from typing import Dict, Any, List
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter
from app.cv.checks.face.detector import detect_faces
from app.core.logging import get_logger

logger = get_logger(__name__)

class FaceCountCheck(BaseCheck):
    """
    Check number of faces in image.
    """
    
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        """Return metadata for this check module."""
        return CheckMetadata(
            name="face_count",
            display_name="Face Count",
            description="Checks that the image contains the required number of faces",
            category="face_detection",
            version="1.0.0",
            author="Photo Validation Team",
            parameters=[
                CheckParameter(
                    name="min_count",
                    type="int",
                    default=1,
                    description="Minimum number of faces",
                    min_value=0,
                    max_value=10,
                    required=True
                ),
                CheckParameter(
                    name="max_count",
                    type="int",
                    default=1,
                    description="Maximum number of faces",
                    min_value=1,
                    max_value=10,
                    required=True
                ),
                CheckParameter(
                    name="face_confidence_threshold",
                    type="float",
                    default=0.4,
                    description="Confidence threshold for face detection",
                    min_value=0.1,
                    max_value=0.9,
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
        Perform face count check on the image.
        
        Args:
            image: Image to check
            context: Context with previous check results
            
        Returns:
            Check results
        """
        try:
            # Use face detector
            faces = detect_faces(image, confidence_threshold=self.parameters["face_confidence_threshold"])
            face_count = len(faces)
            
            min_count = self.parameters["min_count"]
            max_count = self.parameters["max_count"]
            
            # Form details
            face_details = []
            for i, face in enumerate(faces):
                bbox = face.get("bbox", [0, 0, 0, 0])
                confidence = face.get("confidence", 0.0)
                face_details.append({
                    "id": i + 1,
                    "bbox": bbox,
                    "confidence": float(confidence),
                    "area": bbox[2] * bbox[3] if len(bbox) >= 4 else 0
                })
            
            details = {
                "face_count": face_count,
                "min_count_required": min_count,
                "max_count_allowed": max_count,
                "faces": face_details,
                "confidence_threshold": self.parameters["face_confidence_threshold"],
                "parameters_used": self.parameters
            }
            
            # Determine result
            if face_count < min_count:
                return {
                    "check": "face_count",
                    "status": "FAILED",
                    "reason": f"Not enough faces: found {face_count}, required minimum {min_count}",
                    "details": details
                }
            elif face_count > max_count:
                return {
                    "check": "face_count",
                    "status": "FAILED",
                    "reason": f"Too many faces: found {face_count}, maximum {max_count}",
                    "details": details
                }
            else:
                return {
                    "check": "face_count",
                    "status": "PASSED",
                    "details": details
                }
                
        except Exception as e:
            logger.error(f"Error in face count check: {e}")
            return {
                "check": "face_count",
                "status": "NEEDS_REVIEW",
                "reason": f"Error during face count check: {str(e)}",
                "details": {"error": str(e), "parameters_used": self.parameters}
            }