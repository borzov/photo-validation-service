"""
Base class for all check modules.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np
from app.core.logging import get_logger

logger = get_logger(__name__)

class BaseCheck(ABC):
    """
    Abstract base class for all image checks.
    Each check should inherit from this class.
    """
    check_id: str = None
    name: str = None
    description: str = None
    default_config: Dict[str, Any] = {}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize check with given configuration.
        
        Args:
            config: Dictionary with configuration parameters overriding defaults
        """
        if not self.check_id:
            raise ValueError(f"Check {self.__class__.__name__} must have a check_id defined")
        self.config = dict(self.default_config)
        if config:
            self.config.update(config)
        logger.debug(f"Initialized check {self.check_id} with config: {self.config}")

    @abstractmethod
    def run(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute image check.
        
        Args:
            image: Image in NumPy array format (BGR)
            context: Dictionary with contextual information (e.g. previous check results)
            
        Returns:
            Dict with check results. Must contain at least:
            {
                "status": "PASSED" | "FAILED" | "NEEDS_REVIEW" | "SKIPPED",
                "reason": Optional[str],
                "details": Any
            }
        """
        pass

    def __str__(self) -> str:
        """String representation of check."""
        return f"{self.name} ({self.check_id})"