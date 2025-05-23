"""
Automatic discovery and registration system for check modules.
Solves human factor problem when adding new modules.
"""
import os
import importlib
import inspect
from typing import Dict, List, Any, Type, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from app.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class CheckParameter:
    """Check parameter description."""
    name: str
    type: str
    default: Any
    description: str
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    choices: Optional[List[Any]] = None
    required: bool = True

@dataclass
class CheckMetadata:
    """Check module metadata."""
    name: str
    display_name: str
    description: str
    category: str
    version: str
    author: str
    parameters: List[CheckParameter] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    enabled_by_default: bool = True

class BaseCheck(ABC):
    """
    Base class for all check modules.
    All new modules should inherit from this class.
    """
    
    @classmethod
    @abstractmethod
    def get_metadata(cls) -> CheckMetadata:
        """Return check module metadata."""
        pass
    
    @abstractmethod
    def check(self, image, context) -> Dict[str, Any]:
        """Execute image check."""
        pass
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """Validate module parameters."""
        metadata = self.get_metadata()
        
        for param in metadata.parameters:
            if param.required and param.name not in parameters:
                logger.error(f"Required parameter '{param.name}' missing for {metadata.name}")
                return False
                
            if param.name in parameters:
                value = parameters[param.name]
                
                # Type checking
                if param.type == "int" and not isinstance(value, int):
                    logger.error(f"Parameter '{param.name}' must be int, got {type(value)}")
                    return False
                elif param.type == "float" and not isinstance(value, (int, float)):
                    logger.error(f"Parameter '{param.name}' must be float, got {type(value)}")
                    return False
                elif param.type == "bool" and not isinstance(value, bool):
                    logger.error(f"Parameter '{param.name}' must be bool, got {type(value)}")
                    return False
                elif param.type == "str" and not isinstance(value, str):
                    logger.error(f"Parameter '{param.name}' must be str, got {type(value)}")
                    return False
                
                # Range checking
                if param.min_value is not None and value < param.min_value:
                    logger.error(f"Parameter '{param.name}' must be >= {param.min_value}")
                    return False
                if param.max_value is not None and value > param.max_value:
                    logger.error(f"Parameter '{param.name}' must be <= {param.max_value}")
                    return False
                
                # Choice checking
                if param.choices and value not in param.choices:
                    logger.error(f"Parameter '{param.name}' must be one of {param.choices}")
                    return False
        
        return True

class CheckRegistry:
    """
    Check modules registry with automatic discovery.
    """
    
    def __init__(self):
        self.checks: Dict[str, Type[BaseCheck]] = {}
        self.metadata: Dict[str, CheckMetadata] = {}
        self._discovered = False
    
    def discover_checks(self, base_path: str = None) -> None:
        """
        Automatically discover all check modules in specified directory.
        """
        if base_path is None:
            base_path = os.path.dirname(__file__)
        
        logger.info(f"Discovering checks in {base_path}")
        
        # Recursively walk through all Python files
        for root, dirs, files in os.walk(base_path):
            # Skip __pycache__ and other service directories
            dirs[:] = [d for d in dirs if not d.startswith('__')]
            
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    file_path = os.path.join(root, file)
                    self._discover_checks_in_file(file_path, base_path)
        
        self._discovered = True
        logger.info(f"Discovered {len(self.checks)} check modules")
    
    def _discover_checks_in_file(self, file_path: str, base_path: str) -> None:
        """Discover check modules in specific file."""
        try:
            # Convert file path to module name
            rel_path = os.path.relpath(file_path, base_path)
            module_name = rel_path.replace(os.sep, '.').replace('.py', '')
            
            # Add package prefix
            full_module_name = f"app.cv.checks.{module_name}"
            
            # Import module
            module = importlib.import_module(full_module_name)
            
            # Look for classes inheriting from BaseCheck
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseCheck) and 
                    obj != BaseCheck and 
                    hasattr(obj, 'get_metadata')):
                    
                    try:
                        metadata = obj.get_metadata()
                        self.register_check(obj, metadata)
                        logger.debug(f"Registered check: {metadata.name} from {full_module_name}")
                    except Exception as e:
                        logger.error(f"Failed to get metadata for {name}: {e}")
                        
        except Exception as e:
            logger.debug(f"Could not import {file_path}: {e}")
    
    def register_check(self, check_class: Type[BaseCheck], metadata: CheckMetadata) -> None:
        """Register check module."""
        self.checks[metadata.name] = check_class
        self.metadata[metadata.name] = metadata
    
    def get_check(self, name: str) -> Optional[Type[BaseCheck]]:
        """Return check module class by name."""
        return self.checks.get(name)
    
    def get_metadata(self, name: str) -> Optional[CheckMetadata]:
        """Return check module metadata."""
        return self.metadata.get(name)
    
    def get_all_checks(self) -> Dict[str, Type[BaseCheck]]:
        """Return all registered check modules."""
        if not self._discovered:
            self.discover_checks()
        return self.checks.copy()
    
    def get_all_metadata(self) -> Dict[str, CheckMetadata]:
        """Return metadata for all check modules."""
        if not self._discovered:
            self.discover_checks()
        return self.metadata.copy()
    
    def get_checks_by_category(self, category: str) -> Dict[str, Type[BaseCheck]]:
        """Return check modules by category."""
        if not self._discovered:
            self.discover_checks()
        
        result = {}
        for name, metadata in self.metadata.items():
            if metadata.category == category:
                result[name] = self.checks[name]
        return result
    
    def validate_check_parameters(self, check_name: str, parameters: Dict[str, Any]) -> bool:
        """Validate parameters for specific check module."""
        check_class = self.get_check(check_name)
        if not check_class:
            logger.error(f"Check '{check_name}' not found")
            return False
        
        # Create temporary instance for validation
        try:
            instance = check_class()
            return instance.validate_parameters(parameters)
        except Exception as e:
            logger.error(f"Failed to validate parameters for {check_name}: {e}")
            return False
    
    def generate_config_schema(self) -> Dict[str, Any]:
        """
        Generate configuration schema based on discovered modules.
        This allows automatic admin panel creation.
        """
        if not self._discovered:
            self.discover_checks()
        
        schema = {
            "categories": {},
            "checks": {}
        }
        
        # Group by categories
        categories = {}
        for name, metadata in self.metadata.items():
            if metadata.category not in categories:
                categories[metadata.category] = []
            categories[metadata.category].append(name)
        
        schema["categories"] = categories
        
        # Add details for each module
        for name, metadata in self.metadata.items():
            schema["checks"][name] = {
                "display_name": metadata.display_name,
                "description": metadata.description,
                "category": metadata.category,
                "version": metadata.version,
                "author": metadata.author,
                "enabled_by_default": metadata.enabled_by_default,
                "parameters": []
            }
            
            for param in metadata.parameters:
                param_schema = {
                    "name": param.name,
                    "type": param.type,
                    "default": param.default,
                    "description": param.description,
                    "required": param.required
                }
                
                if param.min_value is not None:
                    param_schema["min_value"] = param.min_value
                if param.max_value is not None:
                    param_schema["max_value"] = param.max_value
                if param.choices:
                    param_schema["choices"] = param.choices
                
                schema["checks"][name]["parameters"].append(param_schema)
        
        return schema

# Global registry
check_registry = CheckRegistry()