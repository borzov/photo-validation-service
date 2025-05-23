"""
Сервис для интеграции системы автоматического обнаружения модулей с админ-панелью.
"""
from typing import Dict, List, Any, Optional
from app.cv.checks.registry import check_registry, CheckMetadata
from app.core.logging import get_logger

logger = get_logger(__name__)

class CheckDiscoveryService:
    """
    Сервис для работы с автоматически обнаруженными модулями проверки.
    Предоставляет API для админ-панели.
    """
    
    def __init__(self):
        self.registry = check_registry
        self._ensure_discovery()
    
    def _ensure_discovery(self):
        """Убеждается, что обнаружение модулей выполнено"""
        if not self.registry._discovered:
            self.registry.discover_checks()
    
    def get_all_checks_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Возвращает метаданные всех обнаруженных модулей проверки
        в формате, подходящем для админ-панели.
        """
        self._ensure_discovery()
        
        result = {}
        for name, metadata in self.registry.get_all_metadata().items():
            result[name] = self._format_metadata_for_admin(metadata)
        
        return result
    
    def get_checks_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Возвращает модули проверки, сгруппированные по категориям.
        """
        self._ensure_discovery()
        
        categories = {}
        for name, metadata in self.registry.get_all_metadata().items():
            category = metadata.category
            if category not in categories:
                categories[category] = []
            
            categories[category].append({
                "name": name,
                "display_name": metadata.display_name,
                "description": metadata.description,
                "version": metadata.version,
                "author": metadata.author,
                "enabled_by_default": metadata.enabled_by_default,
                "parameters_count": len(metadata.parameters)
            })
        
        return categories
    
    def get_check_details(self, check_name: str) -> Optional[Dict[str, Any]]:
        """
        Возвращает детальную информацию о конкретном модуле проверки.
        """
        metadata = self.registry.get_metadata(check_name)
        if not metadata:
            return None
        
        return self._format_metadata_for_admin(metadata)
    
    def _format_metadata_for_admin(self, metadata: CheckMetadata) -> Dict[str, Any]:
        """
        Форматирует метаданные модуля для использования в админ-панели.
        """
        return {
            "name": metadata.name,
            "display_name": metadata.display_name,
            "description": metadata.description,
            "category": metadata.category,
            "version": metadata.version,
            "author": metadata.author,
            "enabled_by_default": metadata.enabled_by_default,
            "dependencies": metadata.dependencies,
            "parameters": [
                {
                    "name": param.name,
                    "type": param.type,
                    "default": param.default,
                    "description": param.description,
                    "min_value": param.min_value,
                    "max_value": param.max_value,
                    "choices": param.choices,
                    "required": param.required
                }
                for param in metadata.parameters
            ]
        }
    
    def generate_admin_form_config(self) -> Dict[str, Any]:
        """
        Генерирует конфигурацию для автоматического создания форм в админ-панели.
        """
        self._ensure_discovery()
        
        categories = self.get_checks_by_category()
        form_config = {
            "categories": {},
            "form_sections": []
        }
        
        # Создаем секции формы для каждой категории
        for category_name, checks in categories.items():
            category_config = {
                "name": category_name,
                "display_name": self._get_category_display_name(category_name),
                "description": self._get_category_description(category_name),
                "checks": []
            }
            
            for check in checks:
                check_details = self.get_check_details(check["name"])
                if check_details:
                    category_config["checks"].append({
                        "name": check_details["name"],
                        "display_name": check_details["display_name"],
                        "description": check_details["description"],
                        "enabled_by_default": check_details["enabled_by_default"],
                        "form_fields": self._generate_form_fields(check_details["parameters"])
                    })
            
            form_config["categories"][category_name] = category_config
            form_config["form_sections"].append(category_config)
        
        return form_config
    
    def _generate_form_fields(self, parameters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Генерирует поля формы на основе параметров модуля проверки.
        """
        form_fields = []
        
        for param in parameters:
            field = {
                "name": param["name"],
                "label": param["description"],
                "type": self._map_param_type_to_form_type(param["type"]),
                "default": param["default"],
                "required": param["required"],
                "help_text": f"Тип: {param['type']}"
            }
            
            # Добавляем ограничения
            if param["min_value"] is not None:
                field["min"] = param["min_value"]
                field["help_text"] += f", мин: {param['min_value']}"
            
            if param["max_value"] is not None:
                field["max"] = param["max_value"]
                field["help_text"] += f", макс: {param['max_value']}"
            
            if param["choices"]:
                field["type"] = "select"
                field["choices"] = [
                    {"value": choice, "label": str(choice)}
                    for choice in param["choices"]
                ]
                field["help_text"] += f", варианты: {', '.join(map(str, param['choices']))}"
            
            form_fields.append(field)
        
        return form_fields
    
    def _map_param_type_to_form_type(self, param_type: str) -> str:
        """
        Преобразует тип параметра в тип поля формы.
        """
        mapping = {
            "int": "number",
            "float": "number",
            "bool": "checkbox",
            "str": "text"
        }
        return mapping.get(param_type, "text")
    
    def _get_category_display_name(self, category: str) -> str:
        """
        Возвращает отображаемое имя категории.
        """
        display_names = {
            "face_detection": "Детекция лиц",
            "image_quality": "Качество изображения",
            "background": "Анализ фона",
            "object_detection": "Детекция объектов",
            "accessories": "Детекция аксессуаров",
            "pose": "Анализ позы",
            "lighting": "Анализ освещения"
        }
        return display_names.get(category, category.replace("_", " ").title())
    
    def _get_category_description(self, category: str) -> str:
        """
        Возвращает описание категории.
        """
        descriptions = {
            "face_detection": "Модули для обнаружения и анализа лиц на изображении",
            "image_quality": "Модули для оценки качества изображения",
            "background": "Модули для анализа фона изображения",
            "object_detection": "Модули для обнаружения посторонних объектов",
            "accessories": "Модули для обнаружения аксессуаров и украшений",
            "pose": "Модули для анализа позы и ориентации",
            "lighting": "Модули для анализа освещения и экспозиции"
        }
        return descriptions.get(category, f"Модули категории {category}")
    
    def validate_check_configuration(self, check_name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Валидирует конфигурацию модуля проверки.
        """
        try:
            is_valid = self.registry.validate_check_parameters(check_name, config)
            
            if is_valid:
                return {
                    "valid": True,
                    "message": "Конфигурация валидна"
                }
            else:
                return {
                    "valid": False,
                    "message": "Конфигурация содержит ошибки"
                }
        except Exception as e:
            logger.error(f"Error validating configuration for {check_name}: {e}")
            return {
                "valid": False,
                "message": f"Ошибка валидации: {str(e)}"
            }
    
    def get_discovery_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику обнаруженных модулей.
        """
        self._ensure_discovery()
        
        categories = self.get_checks_by_category()
        total_checks = sum(len(checks) for checks in categories.values())
        
        return {
            "total_checks": total_checks,
            "categories_count": len(categories),
            "categories": {
                name: len(checks) 
                for name, checks in categories.items()
            },
            "discovery_completed": self.registry._discovered
        }

# Глобальный экземпляр сервиса
check_discovery_service = CheckDiscoveryService() 