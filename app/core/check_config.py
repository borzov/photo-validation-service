"""
Система конфигурации для модулей проверки.
"""
import os
import yaml
from typing import Dict, Any, List, Optional, Set
from app.core.logging import get_logger
from app.cv.checks.registry import check_registry

logger = get_logger(__name__)

class CheckConfig:
    """
    Класс для работы с конфигурацией проверок.
    """
    
    def __init__(self, config_file: str = None):
        """
        Инициализирует конфигурацию проверок.
        
        Args:
            config_file: Путь к файлу конфигурации
        """
        self.config_file = config_file or os.environ.get(
            "CHECKS_CONFIG_FILE", 
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "checks_config.yaml")
        )
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Загружает конфигурацию из файла.
        
        Returns:
            Словарь с конфигурацией
        """
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded check configuration from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load check configuration from {self.config_file}: {e}")
            # Возвращаем пустую конфигурацию по умолчанию
            return {
                "system": {"stop_on_failure": False, "max_check_time": 5.0},
                "check_order": [],
                "checks": {}
            }
    
    def save_config(self, config_file: str = None) -> None:
        """
        Сохраняет конфигурацию в файл.
        
        Args:
            config_file: Путь к файлу конфигурации (если None, использует self.config_file)
        """
        file_to_save = config_file or self.config_file
        try:
            with open(file_to_save, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            logger.info(f"Saved check configuration to {file_to_save}")
        except Exception as e:
            logger.error(f"Failed to save check configuration to {file_to_save}: {e}")
    
    def get_enabled_checks(self) -> List[str]:
        """
        Возвращает список ID включенных проверок в порядке выполнения.
        
        Returns:
            Список ID включенных проверок
        """
        # Получаем порядок проверок из конфигурации
        check_order = self.config.get("check_order", [])
        
        # Находим включенные проверки
        enabled_checks = []
        for check_id in check_order:
            check_config = self.config.get("checks", {}).get(check_id, {})
            if check_config.get("enabled", True):
                enabled_checks.append(check_id)
        
        return enabled_checks
    
    def get_check_params(self, check_id: str) -> Dict[str, Any]:
        """
        Возвращает параметры для указанной проверки.
        
        Args:
            check_id: Идентификатор проверки
            
        Returns:
            Словарь с параметрами
        """
        check_config = self.config.get("checks", {}).get(check_id, {})
        return check_config.get("params", {})
    
    def is_check_enabled(self, check_id: str) -> bool:
        """
        Проверяет, включена ли указанная проверка.
        
        Args:
            check_id: Идентификатор проверки
            
        Returns:
            True, если проверка включена, иначе False
        """
        check_config = self.config.get("checks", {}).get(check_id, {})
        return check_config.get("enabled", True)
    
    def get_system_config(self) -> Dict[str, Any]:
        """
        Возвращает общие настройки системы проверок.
        
        Returns:
            Словарь с общими настройками
        """
        return self.config.get("system", {})
    
    def register_missing_checks(self) -> None:
        """
        Регистрирует в конфигурации проверки, которые есть в реестре, но отсутствуют в конфигурации.
        """
        # Получаем все проверки из реестра
        all_check_ids = set(check_registry.get_all_check_ids())
        
        # Получаем проверки из конфигурации
        configured_checks = set(self.config.get("checks", {}).keys())
        
        # Находим отсутствующие проверки
        missing_checks = all_check_ids - configured_checks
        
        # Добавляем отсутствующие проверки в конфигурацию
        if missing_checks:
            logger.info(f"Adding missing checks to configuration: {missing_checks}")
            
            # Если нет раздела checks, создаем его
            if "checks" not in self.config:
                self.config["checks"] = {}
            
            # Добавляем каждую отсутствующую проверку
            for check_id in missing_checks:
                check_class = check_registry.get_check(check_id)
                if check_class:
                    self.config["checks"][check_id] = {
                        "enabled": True,
                        "params": check_class.default_config
                    }
            
            # Если нет порядка проверок, создаем его
            if "check_order" not in self.config:
                self.config["check_order"] = []
            
            # Добавляем отсутствующие проверки в порядок выполнения
            configured_order = set(self.config["check_order"])
            for check_id in missing_checks:
                if check_id not in configured_order:
                    self.config["check_order"].append(check_id)
            
            # Сохраняем обновленную конфигурацию
            self.save_config()

# Глобальный экземпляр конфигурации
check_config = CheckConfig()