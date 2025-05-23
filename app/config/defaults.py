# Default configuration values

from .schema import ConfigurationSchema


def get_default_config() -> ConfigurationSchema:
    """Get default configuration matching current system settings"""
    
    return ConfigurationSchema(
        version="2.1",
        system={
            "processing": {
                "max_concurrent": 5,
                "max_check_time": 5.0,
                "stop_on_failure": False
            },
            "storage": {
                "max_file_size_mb": 1.0,
                "allowed_formats": ["jpg", "jpeg", "png", "webp", "bmp", "tiff"],
                "storage_path": "./local_storage",
                "max_pixels": 25000000
            },
            "log_level": "INFO"
        },
        validation={
            "image_requirements": {
                "min_width": 400,
                "min_height": 500
            },
            "checks": {
                "face_detection": {
                    "enabled": True,
                    "min_count": 1,
                    "max_count": 1,
                    "confidence_threshold": 0.4,
                    "min_area_ratio": 0.05,
                    "max_area_ratio": 0.8
                },
                "face_pose": {
                    "enabled": True,
                    "max_yaw": 25.0,
                    "max_pitch": 25.0,
                    "max_roll": 25.0
                },
                "image_quality": {
                    "enabled": True,
                    "blurriness_threshold": 40,
                    "grayscale_saturation": 15,
                    "lighting": {
                        "underexposure_threshold": 25,
                        "overexposure_threshold": 240,
                        "low_contrast_threshold": 20
                    }
                },
                "background": {
                    "enabled": True,
                    "std_dev_threshold": 100.0,
                    "dark_threshold": 100
                },
                "object_detection": {
                    "enabled": True,
                    "min_contour_area_ratio": 0.03,
                    "person_scale_factor": 1.1
                },
                "accessories": {
                    "enabled": True,
                    "glasses_detection": True,
                    "headwear_detection": True,
                    "hand_detection": True
                }
            }
        }
    ) 