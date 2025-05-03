"""
Пакет с модулями проверки лиц на изображении.
"""
from app.cv.checks.registry import check_registry

# Автоматическая регистрация проверок будет выполнена через check_registry.discover_checks()