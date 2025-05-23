# Configuration schemas with validation using Pydantic

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ImageFormat(str, Enum):
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"


class ProcessingConfig(BaseModel):
    """Processing and performance settings"""
    max_concurrent: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of concurrent image processing tasks"
    )
    max_check_time: float = Field(
        default=5.0,
        ge=1.0,
        le=30.0,
        description="Maximum time allowed for a single check (seconds)"
    )
    stop_on_failure: bool = Field(
        default=False,
        description="Stop processing on first check failure"
    )
    parallel_checks: bool = Field(
        default=True,
        description="Run checks in parallel when possible"
    )


class StorageConfig(BaseModel):
    """File storage and upload settings"""
    max_file_size_mb: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Maximum upload file size in megabytes"
    )
    allowed_formats: List[ImageFormat] = Field(
        default=[ImageFormat.JPG, ImageFormat.JPEG, ImageFormat.PNG, 
                ImageFormat.WEBP, ImageFormat.BMP, ImageFormat.TIFF],
        description="Allowed image file formats"
    )
    storage_path: str = Field(
        default="./local_storage",
        description="Path for temporary file storage"
    )
    max_pixels: int = Field(
        default=50_000_000,
        ge=1_000_000,
        le=100_000_000,
        description="Maximum number of pixels in image"
    )


class ImageRequirementsConfig(BaseModel):
    """Basic image dimension requirements"""
    min_width: int = Field(
        default=400,
        ge=100,
        le=5000,
        description="Minimum image width in pixels"
    )
    min_height: int = Field(
        default=500,
        ge=100,
        le=5000,
        description="Minimum image height in pixels"
    )
    
    @model_validator(mode='after')
    def validate_dimensions(self):
        """Validate that height is reasonable relative to width"""
        if self.min_height < self.min_width * 0.5:
            raise ValueError('Height should not be less than 50% of width')
        return self


class FaceDetectionConfig(BaseModel):
    """Face detection and counting settings"""
    enabled: bool = Field(default=True, description="Enable face detection check")
    min_count: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Minimum number of faces required"
    )
    max_count: int = Field(
        default=1,
        ge=1,
        le=10,
        description="Maximum number of faces allowed"
    )
    confidence_threshold: float = Field(
        default=0.4,
        ge=0.1,
        le=0.9,
        description="Minimum confidence score for face detection"
    )
    min_area_ratio: float = Field(
        default=0.05,
        ge=0.01,
        le=0.5,
        description="Minimum face area ratio relative to image"
    )
    max_area_ratio: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="Maximum face area ratio relative to image"
    )
    
    @model_validator(mode='after')
    def validate_face_counts_and_areas(self):
        """Validate face count and area ratio constraints"""
        if self.max_count < self.min_count:
            raise ValueError('max_count must be >= min_count')
        
        if self.max_area_ratio <= self.min_area_ratio:
            raise ValueError('max_area_ratio must be > min_area_ratio')
        
        return self


class FacePoseConfig(BaseModel):
    """Face pose and orientation settings"""
    enabled: bool = Field(default=True, description="Enable face pose check")
    max_yaw: float = Field(
        default=25.0,
        ge=5.0,
        le=90.0,
        description="Maximum allowed yaw angle (degrees)"
    )
    max_pitch: float = Field(
        default=25.0,
        ge=5.0,
        le=90.0,
        description="Maximum allowed pitch angle (degrees)"
    )
    max_roll: float = Field(
        default=25.0,
        ge=5.0,
        le=90.0,
        description="Maximum allowed roll angle (degrees)"
    )


class LightingConfig(BaseModel):
    """Lighting quality settings"""
    underexposure_threshold: int = Field(
        default=25,
        ge=5,
        le=100,
        description="Threshold for detecting underexposed areas"
    )
    overexposure_threshold: int = Field(
        default=240,
        ge=200,
        le=255,
        description="Threshold for detecting overexposed areas"
    )
    low_contrast_threshold: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Threshold for detecting low contrast"
    )
    
    @model_validator(mode='after')
    def validate_thresholds(self):
        """Validate that overexposure threshold is greater than underexposure"""
        if self.overexposure_threshold <= self.underexposure_threshold:
            raise ValueError('overexposure_threshold must be > underexposure_threshold')
        return self


class ImageQualityConfig(BaseModel):
    """Image quality assessment settings"""
    enabled: bool = Field(default=True, description="Enable image quality checks")
    blurriness_threshold: int = Field(
        default=40,
        ge=10,
        le=200,
        description="Threshold for detecting image blurriness"
    )
    grayscale_saturation: int = Field(
        default=15,
        ge=5,
        le=50,
        description="Threshold for detecting grayscale images"
    )
    lighting: LightingConfig = Field(default_factory=LightingConfig)


class BackgroundConfig(BaseModel):
    """Background analysis settings"""
    enabled: bool = Field(default=True, description="Enable background check")
    std_dev_threshold: float = Field(
        default=100.0,
        ge=10.0,
        le=500.0,
        description="Standard deviation threshold for background uniformity"
    )
    dark_threshold: int = Field(
        default=100,
        ge=50,
        le=200,
        description="Threshold for detecting dark backgrounds"
    )


class ObjectDetectionConfig(BaseModel):
    """Extraneous objects detection settings"""
    enabled: bool = Field(default=True, description="Enable object detection check")
    min_contour_area_ratio: float = Field(
        default=0.03,
        ge=0.001,
        le=0.5,
        description="Minimum contour area ratio for object detection"
    )
    person_scale_factor: float = Field(
        default=1.1,
        ge=1.01,
        le=2.0,
        description="Scale factor for person detection"
    )


class AccessoriesConfig(BaseModel):
    """Accessories detection settings"""
    enabled: bool = Field(default=True, description="Enable accessories detection")
    glasses_detection: bool = Field(default=True, description="Detect glasses")
    headwear_detection: bool = Field(default=True, description="Detect headwear")
    hand_detection: bool = Field(default=True, description="Detect hands near face")


class ValidationChecksConfig(BaseModel):
    """Complete validation checks configuration"""
    face_detection: FaceDetectionConfig = Field(default_factory=FaceDetectionConfig)
    face_pose: FacePoseConfig = Field(default_factory=FacePoseConfig)
    image_quality: ImageQualityConfig = Field(default_factory=ImageQualityConfig)
    background: BackgroundConfig = Field(default_factory=BackgroundConfig)
    object_detection: ObjectDetectionConfig = Field(default_factory=ObjectDetectionConfig)
    accessories: AccessoriesConfig = Field(default_factory=AccessoriesConfig)


class ValidationConfig(BaseModel):
    """Complete validation configuration"""
    image_requirements: ImageRequirementsConfig = Field(default_factory=ImageRequirementsConfig)
    checks: ValidationChecksConfig = Field(default_factory=ValidationChecksConfig)


class SystemConfig(BaseModel):
    """System-level configuration"""
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Application log level")


class ConfigurationSchema(BaseModel):
    """Complete application configuration schema"""
    version: str = Field(default="2.1", description="Configuration version")
    last_modified: datetime = Field(default_factory=datetime.now, description="Last modification time")
    system: SystemConfig = Field(default_factory=SystemConfig)
    validation: ValidationConfig = Field(default_factory=ValidationConfig)
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat()
        }
    }
        
    @model_validator(mode='after')
    def validate_configuration_consistency(self):
        """Validate cross-field consistency"""
        # Validate face detection settings
        face_config = self.validation.checks.face_detection
        if face_config.min_count > face_config.max_count:
            raise ValueError("Face detection min_count cannot be greater than max_count")
        
        # Validate image requirements
        img_req = self.validation.image_requirements
        if img_req.min_height < img_req.min_width * 0.5:
            raise ValueError("Image height should not be less than 50% of width")
        
        return self 


# Request models for API endpoints
class ValidationRequestModel(BaseModel):
    """Model for validation request parameters"""
    face_count_min: int = Field(default=1, ge=0, le=10)
    face_count_max: int = Field(default=1, ge=1, le=10)
    min_face_size: Optional[int] = Field(default=None, ge=20, le=500)
    blur_threshold: Optional[float] = Field(default=None, ge=0.1, le=100.0)
    brightness_min: Optional[int] = Field(default=None, ge=0, le=255)
    brightness_max: Optional[int] = Field(default=None, ge=0, le=255)
    
    @model_validator(mode='after')
    def validate_face_count_range(self):
        """Validate that face count max >= min"""
        if self.face_count_max < self.face_count_min:
            raise ValueError("face_count_max must be >= face_count_min")
        return self 