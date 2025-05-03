"""
Процессор для запуска проверок изображений.
"""
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
import numpy as np
from app.cv.checks.registry import check_registry, BaseCheck
from app.core.check_config import check_config
from app.core.logging import get_logger

logger = get_logger(__name__)

class CheckRunner:
    """
    Класс для запуска проверок изображений в соответствии с конфигурацией.
    """
    
    def __init__(self, config=None):
        """
        Инициализирует процессор проверок.
        
        Args:
            config: Конфигурация проверок (если None, используется глобальная конфигурация)
        """
        self.config = config or check_config
        
        # Проверяем наличие всех проверок в конфигурации
        self.config.register_missing_checks()
        
        # Получаем системные настройки
        self.system_config = self.config.get_system_config()
        self.stop_on_failure = self.system_config.get("stop_on_failure", False)
        self.max_check_time = self.system_config.get("max_check_time", 5.0)
    
    async def run_checks(self, image: np.ndarray, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Запускает все проверки для изображения.
        
        Args:
            image: Изображение для проверки
            context: Начальный контекст (может содержать результаты предварительных проверок)
            
        Returns:
            Словарь с результатами всех проверок и общим результатом:
            {
                "overall_status": "APPROVED" | "REJECTED" | "MANUAL_REVIEW",
                "checks": [...],  # Результаты отдельных проверок
                "issues": [...]   # Список проблем
            }
        """
        # Инициализируем контекст, если его нет
        context = context or {}
        
        # Получаем список включенных проверок в порядке выполнения
        enabled_checks = self.config.get_enabled_checks()
        
        # Создаем список для результатов проверок
        check_results = []
        
        # Создаем список для проблем
        issues = []
        
        # Запускаем проверки по порядку
        for check_id in enabled_checks:
            # Получаем класс проверки
            check_class = check_registry.get_check(check_id)
            if not check_class:
                logger.warning(f"Check {check_id} not found in registry. Skipping.")
                continue
            
            # Получаем параметры проверки
            check_params = self.config.get_check_params(check_id)
            
            # Создаем экземпляр проверки
            check_instance = check_class(check_params)
            
            # Запускаем проверку с ограничением по времени
            try:
                logger.info(f"Running check: {check_id}")
                start_time = time.time()
                
                # Запускаем проверку
                check_result = await asyncio.wait_for(
                    self._run_check(check_instance, image, context),
                    timeout=self.max_check_time
                )
                
                end_time = time.time()
                check_time = end_time - start_time
                logger.info(f"Check {check_id} completed in {check_time:.3f}s with status: {check_result.get('status')}")
                
                # Добавляем ID проверки в результат
                check_result["check"] = check_id
                
                # Добавляем результат проверки в общий список
                check_results.append(check_result)
                
                # Добавляем результат в контекст для последующих проверок
                context[check_id] = check_result
                
                # Если проверка не пройдена, добавляем проблему
                if check_result.get("status") == "FAILED":
                    reason = check_result.get("reason")
                    if reason:
                        issues.append(reason)
                    
                    # Если настроена остановка при ошибке, прекращаем проверки
                    if self.stop_on_failure:
                        logger.info(f"Stopping checks due to failure in {check_id}")
                        break
                
            except asyncio.TimeoutError:
                logger.error(f"Check {check_id} timed out after {self.max_check_time}s")
                check_results.append({
                    "check": check_id,
                    "status": "FAILED",
                    "reason": f"Check timed out after {self.max_check_time}s",
                    "details": None
                })
                issues.append(f"Check {check_id} timed out")
                
                # Если настроена остановка при ошибке, прекращаем проверки
                if self.stop_on_failure:
                    break
            
            except Exception as e:
                logger.error(f"Error running check {check_id}: {e}", exc_info=True)
                check_results.append({
                    "check": check_id,
                    "status": "FAILED",
                    "reason": f"Check error: {str(e)}",
                    "details": None
                })
                issues.append(f"Check {check_id} error: {str(e)}")
                
                # Если настроена остановка при ошибке, прекращаем проверки
                if self.stop_on_failure:
                    break
        
        # Определяем общий статус проверки
        overall_status = self._determine_overall_status(check_results)
        
        # Формируем итоговый результат
        result = {
            "overall_status": overall_status,
            "checks": check_results,
            "issues": issues
        }
        
        return result
    
    async def _run_check(self, check: BaseCheck, image: np.ndarray, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запускает одну проверку.
        
        Args:
            check: Экземпляр проверки
            image: Изображение для проверки
            context: Контекст с результатами предыдущих проверок
            
        Returns:
            Результат проверки
        """
        # Если проверка синхронная, оборачиваем в корутину
        if asyncio.iscoroutinefunction(check.run):
            result = await check.run(image, context)
        else:
            # Запускаем синхронный метод в пуле исполнителей
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, check.run, image, context)
        
        return result
    
    def _determine_overall_status(self, check_results: List[Dict[str, Any]]) -> str:
        """
        Определяет общий статус проверки по результатам отдельных проверок.
        
        Args:
            check_results: Список результатов проверок
            
        Returns:
            Общий статус: "APPROVED", "REJECTED" или "MANUAL_REVIEW"
        """
        # Инициализируем флаги
        has_failed = False
        has_needs_review = False
        
        # Анализируем статусы всех проверок
        for result in check_results:
            status = result.get("status")
            check_id = result.get("check")
            
            # Игнорируем 'NEEDS_REVIEW' для accessories
            if status == "NEEDS_REVIEW" and check_id != "accessories":
                has_needs_review = True
            elif status == "FAILED":
                has_failed = True
        
        # Определяем общий статус
        if has_failed:
            return "REJECTED"
        elif has_needs_review:
            return "MANUAL_REVIEW"
        else:
            return "APPROVED"