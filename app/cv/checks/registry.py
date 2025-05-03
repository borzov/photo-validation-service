"""
Реестр всех доступных проверок.
"""
from typing import Dict, Any, Type, List, Optional
import importlib
import pkgutil
import inspect
import os
from app.cv.checks.base import BaseCheck
from app.core.logging import get_logger

logger = get_logger(__name__)

class CheckRegistry:
    """
    Реестр всех доступных проверок. Выполняет автоматическое обнаружение и регистрацию проверок.
    """
    def __init__(self):
        """
        Инициализация реестра проверок.
        """
        self._checks: Dict[str, Type[BaseCheck]] = {}

    def register(self, check_class: Type[BaseCheck]) -> None:
        """
        Регистрирует класс проверки в реестре.
        :param check_class: Класс проверки, наследник BaseCheck
        """
        if not inspect.isclass(check_class) or not issubclass(check_class, BaseCheck):
            raise TypeError(f"Class {check_class} is not a subclass of BaseCheck")
        check_id = check_class.check_id
        if not check_id:
            raise ValueError(f"Check class {check_class.__name__} does not have a check_id")
        if check_id in self._checks:
            logger.warning(f"Check with id '{check_id}' already registered. Overwriting.")
        self._checks[check_id] = check_class
        logger.debug(f"Registered check: {check_id}")

    def get_check(self, check_id: str) -> Optional[Type[BaseCheck]]:
        """
        Получает класс проверки по идентификатору.
        :param check_id: Идентификатор проверки
        :return: Класс проверки или None, если проверка не найдена
        """
        return self._checks.get(check_id)

    def get_all_checks(self) -> List[Type[BaseCheck]]:
        """
        Возвращает список всех зарегистрированных классов проверок.
        :return: Список классов проверок
        """
        return list(self._checks.values())

    def get_all_check_ids(self) -> List[str]:
        """
        Возвращает список идентификаторов всех зарегистрированных проверок.
        :return: Список идентификаторов проверок
        """
        return list(self._checks.keys())

    def discover_checks(self, package_name: str = "app.cv.checks") -> None:
        """
        Автоматическое обнаружение и регистрация всех проверок в указанном пакете.
        :param package_name: Имя пакета для поиска проверок
        """
        package = importlib.import_module(package_name)
        package_path = os.path.dirname(package.__file__)
        package_prefix = package.__name__ + "."
        for _, module_name, is_pkg in pkgutil.iter_modules([package_path], package_prefix):
            if is_pkg and module_name != package_name:
                self.discover_checks(module_name)
            elif not is_pkg and module_name != package_prefix + "base" and module_name != package_prefix + "registry":
                module = importlib.import_module(module_name)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseCheck) and 
                        obj != BaseCheck and 
                        hasattr(obj, 'check_id') and 
                        obj.check_id):
                        self.register(obj)
        logger.info(f"Discovered {len(self._checks)} checks in {package_name}")

check_registry = CheckRegistry()
from app.cv.checks.base import BaseCheck