"""
Пакет проверок валидации фотографий.
"""
from app.cv.checks.registry import check_registry

# Явный импорт всех модулей проверок
from app.cv.checks.quality import blurriness, color_mode, lighting, real_photo, red_eyes
from app.cv.checks.face import accessories, detector, face_count, face_pose, face_position
from app.cv.checks.background import background_analysis, extraneous_objects

# Запуск обнаружения всех проверок
check_registry.discover_checks()