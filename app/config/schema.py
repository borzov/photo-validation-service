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
    face_confidence_threshold: float = Field(
        default=0.4,
        ge=0.1,
        le=0.9,
        description="Confidence threshold for face detection"
    )
    
    @model_validator(mode='after')
    def validate_face_counts(self):
        """Validate face count constraints"""
        if self.max_count < self.min_count:
            raise ValueError('max_count must be >= min_count')
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


class FacePositionConfig(BaseModel):
    """Face position and size settings"""
    enabled: bool = Field(default=True, description="Enable face position check")
    face_min_area_ratio: float = Field(
        default=0.05,
        ge=0.01,
        le=0.5,
        description="Minimum face area ratio relative to image"
    )
    face_max_area_ratio: float = Field(
        default=0.8,
        ge=0.5,
        le=1.0,
        description="Maximum face area ratio relative to image"
    )
    face_center_tolerance: float = Field(
        default=0.4,
        ge=0.1,
        le=0.8,
        description="Tolerance for face center position"
    )
    min_width_ratio: float = Field(
        default=0.15,
        ge=0.05,
        le=0.5,
        description="Minimum face width ratio relative to image"
    )
    min_height_ratio: float = Field(
        default=0.2,
        ge=0.05,
        le=0.5,
        description="Minimum face height ratio relative to image"
    )
    min_margin_ratio: float = Field(
        default=0.03,
        ge=0.01,
        le=0.2,
        description="Minimum margin around face"
    )
    boundary_tolerance: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Tolerance for face boundary detection in pixels"
    )
    
    @model_validator(mode='after')
    def validate_face_areas(self):
        """Validate face area ratio constraints"""
        if self.face_max_area_ratio <= self.face_min_area_ratio:
            raise ValueError('face_max_area_ratio must be > face_min_area_ratio')
        return self


class AccessoriesConfig(BaseModel):
    """Accessories detection settings"""
    enabled: bool = Field(default=True, description="Enable accessories detection")
    glasses_detection_enabled: bool = Field(default=False, description="Enable glasses detection")
    headwear_detection_enabled: bool = Field(default=True, description="Enable headwear detection")
    hand_detection_enabled: bool = Field(default=True, description="Enable hands near face detection")
    glasses_confidence_threshold: float = Field(
        default=0.5,
        ge=0.1,
        le=0.9,
        description="Confidence threshold for glasses detection"
    )
    skin_detection_threshold: float = Field(
        default=0.3,
        ge=0.1,
        le=0.8,
        description="Skin detection threshold for hand analysis"
    )
    
    # Aliases for template compatibility
    @property
    def glasses_detection(self):
        return self.glasses_detection_enabled
    
    @property  
    def headwear_detection(self):
        return self.headwear_detection_enabled
    
    @property
    def hand_detection(self):
        return self.hand_detection_enabled


class BlurrinessConfig(BaseModel):
    """Image blurriness detection settings"""
    enabled: bool = Field(default=True, description="Enable blurriness check")
    laplacian_threshold: int = Field(
        default=40,
        ge=10,
        le=200,
        description="Minimum Laplacian variance value to consider image sharp"
    )


class ColorModeConfig(BaseModel):
    """Color mode detection settings"""
    enabled: bool = Field(default=True, description="Enable color mode check")
    grayscale_saturation_threshold: int = Field(
        default=15,
        ge=5,
        le=50,
        description="Saturation threshold for determining grayscale image"
    )
    require_color: bool = Field(
        default=True,
        description="Whether to require color image (if False, any is accepted)"
    )


class LightingConfig(BaseModel):
    """Lighting quality settings"""
    enabled: bool = Field(default=True, description="Enable lighting quality check")
    underexposure_threshold: int = Field(
        default=25,
        ge=5,
        le=100,
        description="Threshold for underexposure (mean brightness)"
    )
    overexposure_threshold: int = Field(
        default=240,
        ge=200,
        le=255,
        description="Threshold for overexposure (mean brightness)"
    )
    low_contrast_threshold: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Threshold for low contrast (standard deviation)"
    )
    shadow_ratio_threshold: float = Field(
        default=0.4,
        ge=0.1,
        le=0.8,
        description="Maximum ratio of dark pixels"
    )
    highlight_ratio_threshold: float = Field(
        default=0.3,
        ge=0.1,
        le=0.8,
        description="Maximum ratio of bright pixels"
    )
    
    @model_validator(mode='after')
    def validate_thresholds(self):
        """Validate that overexposure threshold is greater than underexposure"""
        if self.overexposure_threshold <= self.underexposure_threshold:
            raise ValueError('overexposure_threshold must be > underexposure_threshold')
        return self


class ImageQualityConfig(BaseModel):
    """Combined image quality settings for admin interface compatibility"""
    enabled: bool = Field(default=True, description="Enable image quality checks")
    blurriness_threshold: int = Field(
        default=40,
        ge=10,
        le=200,
        description="Minimum Laplacian variance value to consider image sharp"
    )
    grayscale_saturation: int = Field(
        default=15,
        ge=5,
        le=50,
        description="Saturation threshold for determining grayscale image"
    )
    # Include lighting settings for unified access
    underexposure_threshold: int = Field(
        default=25,
        ge=5,
        le=100,
        description="Threshold for underexposure (mean brightness)"
    )
    overexposure_threshold: int = Field(
        default=240,
        ge=200,
        le=255,
        description="Threshold for overexposure (mean brightness)"
    )
    low_contrast_threshold: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Threshold for low contrast (standard deviation)"
    )


class RedEyeConfig(BaseModel):
    """Red eye detection settings"""
    enabled: bool = Field(default=True, description="Enable red eye detection")
    red_threshold: int = Field(
        default=180,
        ge=100,
        le=255,
        description="Minimum red channel brightness for red eye detection"
    )
    red_ratio_threshold: float = Field(
        default=1.8,
        ge=1.2,
        le=3.0,
        description="Minimum ratio of red channel to other channels"
    )
    min_red_pixel_ratio: float = Field(
        default=0.15,
        ge=0.05,
        le=0.5,
        description="Minimum ratio of bright red pixels in pupil area"
    )
    pupil_relative_size: float = Field(
        default=0.3,
        ge=0.1,
        le=0.8,
        description="Relative size of pupil to eye area"
    )
    adaptive_threshold: bool = Field(
        default=True,
        description="Use adaptive threshold for pupil segmentation"
    )
    hsv_detection: bool = Field(
        default=True,
        description="Use HSV color space for enhanced red detection"
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable detailed logging for debugging"
    )
    save_debug_images: bool = Field(
        default=False,
        description="Save debug images for analysis"
    )


class RealPhotoConfig(BaseModel):
    """Real photo detection settings"""
    enabled: bool = Field(default=True, description="Enable real photo detection")
    gradient_mean_threshold: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Threshold for gradient analysis"
    )
    texture_var_threshold: float = Field(
        default=1.5,
        ge=0.5,
        le=5.0,
        description="Threshold for texture variation analysis"
    )
    color_distribution_threshold: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Threshold for color distribution analysis"
    )
    mid_freq_energy_threshold: int = Field(
        default=250,
        ge=100,
        le=1000,
        description="Threshold for mid-frequency energy in FFT analysis"
    )
    evidence_bias: str = Field(
        default="photo",
        description="Bias for determining real photo vs drawing",
        pattern="^(photo|drawing|neutral)$"
    )


class BackgroundConfig(BaseModel):
    """Background analysis settings"""
    enabled: bool = Field(default=True, description="Enable background check")
    background_std_dev_threshold: float = Field(
        default=110.0,
        ge=50.0,
        le=200.0,
        description="Standard deviation threshold for background uniformity"
    )
    is_dark_threshold: int = Field(
        default=80,
        ge=30,
        le=150,
        description="Brightness threshold for determining dark background"
    )
    edge_density_threshold: float = Field(
        default=0.08,
        ge=0.01,
        le=0.5,
        description="Edge density threshold for texture detection"
    )
    grad_mean_threshold: int = Field(
        default=45,
        ge=10,
        le=100,
        description="Mean gradient threshold for smooth background"
    )


class ObjectDetectionConfig(BaseModel):
    """Extraneous objects detection settings"""
    enabled: bool = Field(default=True, description="Enable object detection check")
    min_object_contour_area_ratio: float = Field(
        default=0.03,
        ge=0.001,
        le=0.5,
        description="Minimum object contour area ratio relative to image"
    )
    person_scale_factor: float = Field(
        default=1.1,
        ge=1.02,
        le=1.5,
        description="Scale factor for HOG person detector"
    )
    person_min_neighbors: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Minimum neighbors for HOG person detector"
    )
    canny_threshold1: int = Field(
        default=50,
        ge=10,
        le=200,
        description="Lower threshold for Canny edge detector"
    )
    canny_threshold2: int = Field(
        default=150,
        ge=50,
        le=300,
        description="Upper threshold for Canny edge detector"
    )
    
    @model_validator(mode='after')
    def validate_canny_thresholds(self):
        """Validate that canny_threshold2 is greater than canny_threshold1"""
        if self.canny_threshold2 <= self.canny_threshold1:
            raise ValueError('canny_threshold2 must be > canny_threshold1')
        return self


class ValidationChecksConfig(BaseModel):
    """Complete validation checks configuration"""
    face_detection: FaceDetectionConfig = Field(default_factory=FaceDetectionConfig)
    face_pose: FacePoseConfig = Field(default_factory=FacePoseConfig)
    face_position: FacePositionConfig = Field(default_factory=FacePositionConfig)
    accessories: AccessoriesConfig = Field(default_factory=AccessoriesConfig)
    blurriness: BlurrinessConfig = Field(default_factory=BlurrinessConfig)
    color_mode: ColorModeConfig = Field(default_factory=ColorModeConfig)
    lighting: LightingConfig = Field(default_factory=LightingConfig)
    red_eye: RedEyeConfig = Field(default_factory=RedEyeConfig)
    real_photo: RealPhotoConfig = Field(default_factory=RealPhotoConfig)
    background: BackgroundConfig = Field(default_factory=BackgroundConfig)
    object_detection: ObjectDetectionConfig = Field(default_factory=ObjectDetectionConfig)
    # Add unified image_quality for admin interface compatibility
    image_quality: ImageQualityConfig = Field(default_factory=ImageQualityConfig)


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
        "validate_assignment": True
    }
    
    @model_validator(mode='after')
    def validate_configuration_consistency(self):
        """Validate overall configuration consistency"""
        # Check that storage path is not empty
        if not self.system.storage.storage_path.strip():
            raise ValueError('Storage path cannot be empty')
        
        # Check that at least one format is allowed
        if not self.system.storage.allowed_formats:
            raise ValueError('At least one image format must be allowed')
        
        # Check that image requirements are reasonable
        min_w = self.validation.image_requirements.min_width
        min_h = self.validation.image_requirements.min_height
        max_pixels = self.system.storage.max_pixels
        
        if min_w * min_h > max_pixels:
            raise ValueError('Minimum image dimensions exceed maximum allowed pixels')
        
        return self


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
        """Validate face count range"""
        if self.face_count_max < self.face_count_min:
            raise ValueError('face_count_max must be >= face_count_min')
        return self


# Export configuration schema instance
config_schema = ConfigurationSchema() 