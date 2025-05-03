"""
Базовый класс для всех модулей проверки.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import numpy as np
from app.core.logging import get_logger

logger = get_logger(__name__)

class BaseCheck(ABC):
    """
    Абстрактный базовый класс для всех проверок изображений.
    Каждая проверка должна наследоваться от этого класса.
    """
    check_id: str = None
    name: str = None
    description: str = None
    default_config: Dict[str, Any] = {}

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализирует проверку с заданной конфигурацией.
        :param config: Словарь с параметрами конфигурации, переопределяющими значения по умолчанию
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
        Выполняет проверку изображения.
        :param image: Изображение в формате NumPy array (BGR)
        :param context: Словарь с контекстной информацией (например, результаты предыдущих проверок)
        :return: Dict с результатами проверки. Должен содержать как минимум:
            {
                "status": "PASSED" | "FAILED" | "NEEDS_REVIEW" | "SKIPPED",
                "reason": Optional[str],
                "details": Any
            }
        """
        pass

    def __str__(self) -> str:
        """
        Строковое представление проверки.
        """
        return f"{self.name} ({self.check_id})"