# Configuration Manager for centralized settings management

import json
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .schema import ConfigurationSchema
from .defaults import get_default_config


logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """File system event handler for configuration file changes"""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        
    def on_modified(self, event):
        if not event.is_directory and event.src_path == str(self.config_manager.config_file):
            logger.info(f"Configuration file changed: {event.src_path}")
            self.config_manager.reload_config()


class ConfigurationManager:
    """Centralized configuration manager with validation and hot-reload support"""
    
    def __init__(self, config_file: str = "app/config/unified_config.json"):
        self.config_file = Path(config_file)
        self.config_dir = self.config_file.parent
        self.backup_dir = self.config_dir / "backups"
        
        # Current configuration
        self._config: Optional[ConfigurationSchema] = None
        
        # File monitoring
        self._observer: Optional[Observer] = None
        self._file_handler: Optional[ConfigFileHandler] = None
        
        # Callbacks for configuration changes
        self._change_callbacks = []
        
        # Initialize
        self._ensure_directories()
        self.load_config()
        self._start_file_monitoring()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _start_file_monitoring(self):
        """Start monitoring configuration file for changes"""
        try:
            self._file_handler = ConfigFileHandler(self)
            self._observer = Observer()
            self._observer.schedule(
                self._file_handler, 
                str(self.config_dir), 
                recursive=False
            )
            self._observer.start()
            logger.info("Started configuration file monitoring")
        except Exception as e:
            logger.warning(f"Failed to start file monitoring: {e}")
    
    def _stop_file_monitoring(self):
        """Stop monitoring configuration file"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("Stopped configuration file monitoring")
    
    def add_change_callback(self, callback):
        """Add callback to be called when configuration changes"""
        self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback):
        """Remove change callback"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    def _notify_change_callbacks(self, old_config: ConfigurationSchema, new_config: ConfigurationSchema):
        """Notify all registered callbacks about configuration changes"""
        for callback in self._change_callbacks:
            try:
                callback(old_config, new_config)
            except Exception as e:
                logger.error(f"Error in configuration change callback: {e}")
    
    def load_config(self) -> ConfigurationSchema:
        """Load configuration from file or create default"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Validate and load configuration
                config = ConfigurationSchema(**config_data)
                logger.info(f"Loaded configuration from {self.config_file}")
            else:
                # Create default configuration
                config = get_default_config()
                self.save_config(config)
                logger.info(f"Created default configuration at {self.config_file}")
            
            old_config = self._config
            self._config = config
            
            # Notify callbacks if config changed
            if old_config and old_config != config:
                self._notify_change_callbacks(old_config, config)
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            if self._config is None:
                # If no config loaded yet, use default
                self._config = get_default_config()
            return self._config
    
    def save_config(self, config: ConfigurationSchema, backup: bool = True) -> bool:
        """Save configuration to file with optional backup"""
        try:
            # Update last modified timestamp
            config.last_modified = datetime.now()
            
            # Create backup if requested and file exists
            if backup and self.config_file.exists():
                self._create_backup()
            
            # Write configuration
            config_data = json.loads(config.json(indent=2))
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            old_config = self._config
            self._config = config
            
            # Notify callbacks
            if old_config and old_config != config:
                self._notify_change_callbacks(old_config, config)
            
            logger.info(f"Saved configuration to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _create_backup(self) -> str:
        """Create backup of current configuration file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"config_backup_{timestamp}.json"
        
        shutil.copy2(self.config_file, backup_file)
        logger.info(f"Created configuration backup: {backup_file}")
        
        # Clean old backups (keep last 10)
        self._cleanup_old_backups()
        
        return str(backup_file)
    
    def _cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backup files, keeping only the most recent ones"""
        try:
            backup_files = list(self.backup_dir.glob("config_backup_*.json"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for old_backup in backup_files[keep_count:]:
                old_backup.unlink()
                logger.debug(f"Removed old backup: {old_backup}")
                
        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")
    
    def reload_config(self) -> ConfigurationSchema:
        """Reload configuration from file"""
        logger.info("Reloading configuration...")
        return self.load_config()
    
    def get_config(self) -> ConfigurationSchema:
        """Get current configuration"""
        if self._config is None:
            self._config = self.load_config()
        return self._config
    
    def update_config(self, updates: Dict[str, Any], validate: bool = True) -> tuple[bool, Optional[str]]:
        """Update configuration with partial data"""
        try:
            current_config = self.get_config()
            current_data = json.loads(current_config.json())
            
            # Deep merge updates
            merged_data = self._deep_merge(current_data, updates)
            
            if validate:
                # Validate new configuration
                new_config = ConfigurationSchema(**merged_data)
            else:
                # Create without validation (risky)
                new_config = ConfigurationSchema.parse_obj(merged_data)
            
            # Save new configuration
            success = self.save_config(new_config)
            
            if success:
                return True, None
            else:
                return False, "Failed to save configuration"
                
        except Exception as e:
            error_msg = f"Failed to update configuration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def reset_to_defaults(self) -> bool:
        """Reset configuration to default values"""
        try:
            default_config = get_default_config()
            return self.save_config(default_config)
        except Exception as e:
            logger.error(f"Failed to reset configuration to defaults: {e}")
            return False
    
    def export_config(self, export_path: str) -> bool:
        """Export current configuration to file"""
        try:
            export_file = Path(export_path)
            config = self.get_config()
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(json.loads(config.json()), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported configuration to {export_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return False
    
    def import_config(self, import_path: str, validate: bool = True) -> tuple[bool, Optional[str]]:
        """Import configuration from file"""
        try:
            import_file = Path(import_path)
            
            if not import_file.exists():
                return False, f"Import file does not exist: {import_path}"
            
            with open(import_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if validate:
                # Validate imported configuration
                config = ConfigurationSchema(**config_data)
            else:
                config = ConfigurationSchema.parse_obj(config_data)
            
            success = self.save_config(config)
            
            if success:
                logger.info(f"Imported configuration from {import_file}")
                return True, None
            else:
                return False, "Failed to save imported configuration"
                
        except Exception as e:
            error_msg = f"Failed to import configuration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def validate_config(self, config_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate configuration data without saving"""
        try:
            ConfigurationSchema(**config_data)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_section(self, section_path: str) -> Any:
        """Get specific section of configuration using dot notation"""
        config = self.get_config()
        
        parts = section_path.split('.')
        current = config.dict()
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def update_section(self, section_path: str, value: Any) -> tuple[bool, Optional[str]]:
        """Update specific section of configuration using dot notation"""
        updates = {}
        parts = section_path.split('.')
        
        # Build nested dictionary for update
        current = updates
        for part in parts[:-1]:
            current[part] = {}
            current = current[part]
        current[parts[-1]] = value
        
        return self.update_config(updates)
    
    def shutdown(self):
        """Cleanup resources"""
        self._stop_file_monitoring()
        self._change_callbacks.clear()


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


def get_current_config() -> ConfigurationSchema:
    """Get current configuration from global manager"""
    return get_config_manager().get_config() 