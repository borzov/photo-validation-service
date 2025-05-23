"""
Процессор для запуска проверок изображений.
"""
import time
import asyncio
from typing import Dict, Any, List, Optional, Callable
import numpy as np
import hashlib
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
        
        # Кэш для результатов детекции лиц
        self._face_detection_cache = {}
    
    def _get_image_hash(self, image: np.ndarray) -> str:
        """Вычисляет хэш изображения для кэширования"""
        # Используем небольшую выборку пикселей для быстрого хэширования
        sample = image[::50, ::50].flatten()
        return hashlib.md5(sample.tobytes()).hexdigest()
    
    def _cache_face_detection(self, image: np.ndarray, faces: List[Dict[str, Any]]) -> None:
        """Кэширует результаты детекции лиц"""
        image_hash = self._get_image_hash(image)
        self._face_detection_cache[image_hash] = faces
        
        # Ограничиваем размер кэша
        if len(self._face_detection_cache) > 100:
            # Удаляем самые старые записи
            oldest_key = next(iter(self._face_detection_cache))
            del self._face_detection_cache[oldest_key]
    
    def _get_cached_face_detection(self, image: np.ndarray) -> Optional[List[Dict[str, Any]]]:
        """Получает кэшированные результаты детекции лиц"""
        image_hash = self._get_image_hash(image)
        return self._face_detection_cache.get(image_hash)
    
    def _can_run_parallel(self, check_id: str) -> bool:
        """Определяет, можно ли запустить проверку параллельно"""
        # Проверки, которые можно выполнять параллельно (не зависят от результатов других)
        parallel_checks = {
            'fileFormat', 'fileSize', 'dimensions', 'colorMode', 
            'blurriness', 'redEye', 'lighting', 'realPhoto'
        }
        return check_id in parallel_checks
    
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
        
        # Разделяем проверки на параллельные и последовательные
        parallel_checks = []
        sequential_checks = []
        
        for check_id in enabled_checks:
            if self._can_run_parallel(check_id):
                parallel_checks.append(check_id)
            else:
                sequential_checks.append(check_id)
        
        # Сначала запускаем параллельные проверки
        if parallel_checks:
            parallel_tasks = []
            for check_id in parallel_checks:
                check_class = check_registry.get_check(check_id)
                if check_class:
                    check_params = self.config.get_check_params(check_id)
                    check_instance = check_class(check_params)
                    task = self._run_check_with_timeout(check_instance, check_id, image, context.copy())
                    parallel_tasks.append(task)
            
            # Ждем завершения всех параллельных проверок
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            
            for result in parallel_results:
                if isinstance(result, Exception):
                    logger.error(f"Parallel check failed: {result}")
                    continue
                
                check_results.append(result)
                context[result["check"]] = result
                
                if result.get("status") == "FAILED":
                    reason = result.get("reason")
                    if reason:
                        issues.append(reason)
                    
                    if self.stop_on_failure:
                        logger.info(f"Stopping checks due to failure in {result['check']}")
                        break
        
        # Если не остановились на ошибке, запускаем последовательные проверки
        if not (self.stop_on_failure and issues):
            for check_id in sequential_checks:
                check_class = check_registry.get_check(check_id)
                if not check_class:
                    logger.warning(f"Check {check_id} not found in registry. Skipping.")
                    continue
                
                check_params = self.config.get_check_params(check_id)
                check_instance = check_class(check_params)
                
                try:
                    result = await self._run_check_with_timeout(check_instance, check_id, image, context)
                    check_results.append(result)
                    context[check_id] = result
                    
                    if result.get("status") == "FAILED":
                        reason = result.get("reason")
                        if reason:
                            issues.append(reason)
                        
                        if self.stop_on_failure:
                            logger.info(f"Stopping checks due to failure in {check_id}")
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
    
    async def _run_check_with_timeout(self, check: BaseCheck, check_id: str, image: np.ndarray, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запускает одну проверку с ограничением по времени.
        """
        logger.info(f"Running check: {check_id}")
        start_time = time.time()
        
        try:
            # Оптимизация для проверок лиц - используем кэш
            if check_id in ['faceCount', 'facePosition', 'facePose', 'accessories']:
                cached_faces = self._get_cached_face_detection(image)
                if cached_faces is not None:
                    context['cached_faces'] = cached_faces
            
            check_result = await asyncio.wait_for(
                self._run_check(check, image, context),
                timeout=self.max_check_time
            )
            
            # Кэшируем результаты детекции лиц
            if check_id == 'faceCount' and check_result.get("status") == "PASSED":
                faces = context.get('faces', [])
                if faces:
                    self._cache_face_detection(image, faces)
            
            end_time = time.time()
            check_time = end_time - start_time
            logger.info(f"Check {check_id} completed in {check_time:.3f}s with status: {check_result.get('status')}")
            
            # Добавляем ID проверки в результат
            check_result["check"] = check_id
            
            return check_result
            
        except asyncio.TimeoutError:
            logger.error(f"Check {check_id} timed out after {self.max_check_time}s")
            return {
                "check": check_id,
                "status": "FAILED",
                "reason": f"Check timed out after {self.max_check_time}s",
                "details": None
            }
    
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