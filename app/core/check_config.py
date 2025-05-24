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
    Автоматически генерирует конфигурацию из метаданных модулей,
    но сохраняет изменения администратора.
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
        
        # Обеспечиваем обнаружение всех модулей
        check_registry.discover_checks()
        
        # Загружаем или генерируем конфигурацию
        self.config = self._load_or_generate_config()
        
    def _load_or_generate_config(self) -> Dict[str, Any]:
        """
        Загружает конфигурацию из файла или генерирует из метаданных модулей.
        
        Returns:
            Словарь с конфигурацией
        """
        # Если файл существует, загружаем его
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    existing_config = yaml.safe_load(f)
                
                # Проверяем, нужно ли обновить конфигурацию новыми модулями
                updated_config = self._merge_with_discovered_checks(existing_config)
                
                # Если конфигурация обновилась, сохраняем её
                if updated_config != existing_config:
                    self._save_config(updated_config)
                    logger.info(f"Конфигурация обновлена новыми модулями проверки: {self.config_file}")
                
                logger.info(f"Загружена конфигурация проверок из {self.config_file}")
                return updated_config
                
            except Exception as e:
                logger.error(f"Не удалось загрузить конфигурацию из {self.config_file}: {e}")
                logger.info("Генерирую новую конфигурацию из метаданных модулей")
                return self._generate_config_from_metadata()
        
        # Если файла нет, генерируем конфигурацию из метаданных
        logger.info("Файл конфигурации не найден. Генерирую из метаданных модулей.")
        config = self._generate_config_from_metadata()
        self._save_config(config)
        return config
    
    def _generate_config_from_metadata(self) -> Dict[str, Any]:
        """
        Генерирует конфигурацию на основе метаданных всех обнаруженных модулей.
        
        Returns:
            Сгенерированная конфигурация
        """
        all_metadata = check_registry.get_all_metadata()
        
        # Группируем модули по категориям для определения порядка
        categories_order = [
            "face_detection",     # Детекция лиц (должна быть первой для установки контекста)
            "image_validation",   # Базовая валидация изображения
            "image_quality",      # Качество изображения
            "background",         # Анализ фона
            "object_detection"    # Детекция объектов
        ]
        
        # Формируем порядок проверок
        check_order = []
        categorized_checks = {cat: [] for cat in categories_order}
        other_checks = []
        
        for check_name, metadata in all_metadata.items():
            if metadata.category in categorized_checks:
                categorized_checks[metadata.category].append(check_name)
            else:
                other_checks.append(check_name)
        
        # Добавляем в порядке категорий
        for category in categories_order:
            category_checks = categorized_checks[category]
            if category == "face_detection":
                # face_count должен быть первым для установки контекста лица
                if "face_count" in category_checks:
                    check_order.append("face_count")
                    category_checks = [c for c in category_checks if c != "face_count"]
                check_order.extend(sorted(category_checks))
            else:
                check_order.extend(sorted(category_checks))
        check_order.extend(sorted(other_checks))
        
        # Формируем конфигурацию
        config = {
            "# Автоматически сгенерированная конфигурация": "из метаданных модулей проверки",
            "system": {
                "stop_on_failure": False,
                "max_check_time": 5.0
            },
            "check_order": check_order,
            "checks": {}
        }
        
        # Добавляем параметры для каждого модуля
        for check_name, metadata in all_metadata.items():
            default_params = {}
            for param in metadata.parameters:
                default_params[param.name] = param.default
            
            config["checks"][check_name] = {
                "enabled": metadata.enabled_by_default,
                "params": default_params
            }
        
        logger.info(f"Сгенерирована конфигурация для {len(all_metadata)} модулей проверки")
        return config
    
    def _merge_with_discovered_checks(self, existing_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Объединяет существующую конфигурацию с новыми обнаруженными модулями.
        
        Args:
            existing_config: Существующая конфигурация
            
        Returns:
            Обновленная конфигурация
        """
        all_metadata = check_registry.get_all_metadata()
        all_check_names = set(all_metadata.keys())
        
        # Получаем уже настроенные проверки
        configured_checks = set(existing_config.get("checks", {}).keys())
        
        # Находим новые модули
        new_checks = all_check_names - configured_checks
        
        if not new_checks:
            return existing_config  # Нет изменений
        
        logger.info(f"Найдены новые модули проверки: {new_checks}")
        
        # Создаем копию конфигурации
        updated_config = existing_config.copy()
        
        # Обеспечиваем наличие нужных секций
        if "checks" not in updated_config:
            updated_config["checks"] = {}
        if "check_order" not in updated_config:
            updated_config["check_order"] = []
        
        # Добавляем новые модули
        for check_name in new_checks:
            metadata = all_metadata[check_name]
            default_params = {}
            for param in metadata.parameters:
                default_params[param.name] = param.default
            
            updated_config["checks"][check_name] = {
                "enabled": metadata.enabled_by_default,
                "params": default_params
            }
            
            # Добавляем в порядок выполнения, если его там нет
            if check_name not in updated_config["check_order"]:
                updated_config["check_order"].append(check_name)
        
        return updated_config
    
    def _save_config(self, config: Dict[str, Any]) -> None:
        """
        Сохраняет конфигурацию в файл.
        
        Args:
            config: Конфигурация для сохранения
        """
        try:
            # Обеспечиваем существование директории
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # Сохраняем с красивым форматированием
            with open(self.config_file, 'w', encoding='utf-8') as f:
                # Добавляем заголовок
                f.write("# Конфигурация проверок фотографий\n")
                f.write("# Автоматически сгенерирована из метаданных модулей\n")
                f.write("# Изменения администратора сохраняются при перезапуске\n\n")
                
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            logger.info(f"Конфигурация сохранена в {self.config_file}")
            
        except Exception as e:
            logger.error(f"Не удалось сохранить конфигурацию в {self.config_file}: {e}")
    
    def save_config(self, config_file: str = None) -> None:
        """
        Сохраняет текущую конфигурацию в файл.
        Метод для обратной совместимости.
        
        Args:
            config_file: Путь к файлу конфигурации (если None, использует self.config_file)
        """
        if config_file:
            original_config_file = self.config_file
            self.config_file = config_file
            self._save_config(self.config)
            self.config_file = original_config_file
        else:
            self._save_config(self.config)
    
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
    


# Глобальный экземпляр конфигурации
check_config = CheckConfig()