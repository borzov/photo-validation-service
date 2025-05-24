"""
Миксины для устранения дублирования кода в модулях проверки.
"""
from typing import Dict, Any
from app.core.logging import get_logger

logger = get_logger(__name__)

class StandardCheckMixin:
    """
    Миксин с общими методами для всех модулей проверки.
    Устраняет дублирование кода инициализации и run() методов.
    """
    
    def __init__(self, **parameters):
        """Стандартная инициализация с параметрами."""
        self.parameters = parameters
        metadata = self.get_metadata()
        
        # Устанавливаем значения по умолчанию
        for param in metadata.parameters:
            if param.name not in self.parameters:
                self.parameters[param.name] = param.default
        
        # Проверяем параметры
        if not self.validate_parameters(self.parameters):
            raise ValueError("Переданы недопустимые параметры")

    def run(self, image, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Метод для совместимости со старым runner."""
        return self.check(image, context)

    def _create_error_result(self, check_name: str, error: Exception) -> Dict[str, Any]:
        """Создает стандартный результат для ошибки."""
        error_msg = f"Ошибка при проверке {check_name}: {str(error)}"
        logger.error(error_msg)
        return {
            "check": check_name,
            "status": "NEEDS_REVIEW",
            "reason": error_msg,
            "details": {"error": str(error), "parameters_used": self.parameters}
        }

    def _create_skipped_result(self, check_name: str, reason: str) -> Dict[str, Any]:
        """Создает стандартный результат для пропущенной проверки."""
        return {
            "check": check_name,
            "status": "SKIPPED",
            "reason": reason,
            "details": None
        }

    def _validate_face_context(self, context: Dict[str, Any], check_name: str) -> Dict[str, Any]:
        """Проверяет наличие контекста лица. Возвращает результат ошибки если контекст неверный."""
        if not context or "face" not in context:
            return self._create_skipped_result(check_name, "Лицо не обнаружено")
        return None

    def _validate_face_bbox_context(self, context: Dict[str, Any], check_name: str) -> Dict[str, Any]:
        """Проверяет наличие bbox лица в контексте."""
        face_error = self._validate_face_context(context, check_name)
        if face_error:
            return face_error
            
        if "bbox" not in context["face"]:
            return self._create_skipped_result(check_name, "Лицо не обнаружено")
        return None 