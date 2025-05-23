"""
Модуль для мониторинга производительности и сбора метрик.
"""
import time
import asyncio
import psutil
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from app.core.logging import get_logger

logger = get_logger(__name__)

@dataclass
class PerformanceMetrics:
    """Класс для хранения метрик производительности"""
    total_requests: int = 0
    completed_requests: int = 0
    failed_requests: int = 0
    average_processing_time: float = 0.0
    peak_memory_usage: float = 0.0
    active_tasks: int = 0
    queue_size: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    last_updated: datetime = field(default_factory=datetime.now)

class PerformanceMonitor:
    """
    Класс для мониторинга производительности системы.
    """
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.processing_times = []
        self.max_processing_times = 1000  # Храним последние 1000 времен обработки
        self._start_time = time.time()
        
    def record_request_start(self):
        """Записывает начало обработки запроса"""
        self.metrics.total_requests += 1
        
    def record_request_completion(self, processing_time: float, success: bool = True):
        """Записывает завершение обработки запроса"""
        if success:
            self.metrics.completed_requests += 1
        else:
            self.metrics.failed_requests += 1
            
        # Обновляем статистику времени обработки
        self.processing_times.append(processing_time)
        if len(self.processing_times) > self.max_processing_times:
            self.processing_times.pop(0)
            
        # Пересчитываем среднее время
        if self.processing_times:
            self.metrics.average_processing_time = sum(self.processing_times) / len(self.processing_times)
            
        self.metrics.last_updated = datetime.now()
        
    def record_cache_hit(self):
        """Записывает попадание в кэш"""
        self.metrics.cache_hits += 1
        
    def record_cache_miss(self):
        """Записывает промах кэша"""
        self.metrics.cache_misses += 1
        
    def update_system_metrics(self, active_tasks: int, queue_size: int):
        """Обновляет системные метрики"""
        self.metrics.active_tasks = active_tasks
        self.metrics.queue_size = queue_size
        
        # Обновляем пиковое использование памяти
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        if current_memory > self.metrics.peak_memory_usage:
            self.metrics.peak_memory_usage = current_memory
            
    def get_cache_stats(self) -> Dict[str, Any]:
        """Возвращает статистику кэша"""
        total_cache_requests = self.metrics.cache_hits + self.metrics.cache_misses
        hit_rate = 0.0
        if total_cache_requests > 0:
            hit_rate = self.metrics.cache_hits / total_cache_requests
            
        return {
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "total_requests": total_cache_requests,
            "hit_rate": hit_rate
        }
        
    def get_metrics(self) -> Dict[str, Any]:
        """Возвращает текущие метрики"""
        uptime = time.time() - self._start_time
        
        # Вычисляем дополнительные метрики
        success_rate = 0.0
        if self.metrics.total_requests > 0:
            success_rate = self.metrics.completed_requests / self.metrics.total_requests * 100
            
        cache_hit_rate = 0.0
        total_cache_requests = self.metrics.cache_hits + self.metrics.cache_misses
        if total_cache_requests > 0:
            cache_hit_rate = self.metrics.cache_hits / total_cache_requests * 100
            
        requests_per_minute = 0.0
        if uptime > 0:
            requests_per_minute = self.metrics.total_requests / (uptime / 60)
            
        return {
            "uptime_seconds": round(uptime, 2),
            "total_requests": self.metrics.total_requests,
            "completed_requests": self.metrics.completed_requests,
            "failed_requests": self.metrics.failed_requests,
            "success_rate_percent": round(success_rate, 2),
            "average_processing_time_seconds": round(self.metrics.average_processing_time, 3),
            "peak_memory_usage_mb": round(self.metrics.peak_memory_usage, 2),
            "current_memory_usage_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
            "cpu_usage_percent": psutil.cpu_percent(),
            "active_tasks": self.metrics.active_tasks,
            "queue_size": self.metrics.queue_size,
            "cache_hits": self.metrics.cache_hits,
            "cache_misses": self.metrics.cache_misses,
            "cache_hit_rate_percent": round(cache_hit_rate, 2),
            "requests_per_minute": round(requests_per_minute, 2),
            "last_updated": self.metrics.last_updated.isoformat()
        }
        
    def get_health_status(self) -> Dict[str, Any]:
        """Возвращает статус здоровья системы"""
        metrics = self.get_metrics()
        
        # Определяем статус здоровья
        health_issues = []
        
        # Проверяем высокое использование памяти
        if metrics["current_memory_usage_mb"] > 1000:  # 1GB
            health_issues.append("High memory usage")
            
        # Проверяем высокое использование CPU
        if metrics["cpu_usage_percent"] > 80:
            health_issues.append("High CPU usage")
            
        # Проверяем большую очередь
        if metrics["queue_size"] > 100:
            health_issues.append("Large processing queue")
            
        # Проверяем низкий успех
        if metrics["success_rate_percent"] < 90 and metrics["total_requests"] > 10:
            health_issues.append("Low success rate")
            
        # Проверяем медленную обработку
        if metrics["average_processing_time_seconds"] > 30:
            health_issues.append("Slow processing")
            
        status = "healthy" if not health_issues else "warning" if len(health_issues) <= 2 else "critical"
        
        return {
            "status": status,
            "issues": health_issues,
            "metrics": metrics
        }

# Глобальный экземпляр монитора
performance_monitor = PerformanceMonitor()

class PerformanceContext:
    """Контекстный менеджер для измерения производительности"""
    
    def __init__(self, operation_name: str = "operation"):
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        performance_monitor.record_request_start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            processing_time = time.time() - self.start_time
            success = exc_type is None
            performance_monitor.record_request_completion(processing_time, success)
            
            if success:
                logger.debug(f"{self.operation_name} completed in {processing_time:.3f}s")
            else:
                logger.error(f"{self.operation_name} failed after {processing_time:.3f}s: {exc_val}")

async def periodic_metrics_update():
    """Периодически обновляет системные метрики"""
    while True:
        try:
            # Здесь можно добавить обновление метрик из других источников
            # Например, количество активных задач из worker
            await asyncio.sleep(30)  # Обновляем каждые 30 секунд
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            await asyncio.sleep(60)  # При ошибке ждем дольше 