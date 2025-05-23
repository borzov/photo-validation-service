# Python Code Standards

Вы эксперт Python разработчик. Строго следуйте этим стандартам:

## Стандарты кодирования
- Следуйте PEP 8 для стиля кода
- Используйте PEP 257 для docstrings
- Применяйте type hints согласно PEP 484/526
- Следуйте PEP 20 (The Zen of Python)

## Форматирование кода
- Используйте 4 пробела для отступов
- Максимальная длина строки: 88 символов (Black formatter)
- Используйте trailing commas в многострочных структурах
- Импорты группируйте согласно PEP 8: stdlib, third-party, local

## Именование
- Классы: PascalCase (ImageProcessor, ApiHandler)
- Функции и переменные: snake_case (process_image, user_data)
- Константы: UPPER_SNAKE_CASE (MAX_IMAGE_SIZE, DEFAULT_FORMAT)
- Приватные атрибуты: _leading_underscore
- Модули: lowercase с подчеркиваниями при необходимости

## Type Hints
- Всегда используйте type hints для функций и методов
- Используйте Union, Optional из typing
- Для Python 3.9+ предпочитайте встроенные типы (list[str] вместо List[str])
- Используйте TypedDict для структурированных данных

## Обработка ошибок
- Используйте специфичные исключения
- Создавайте кастомные исключения для доменной логики
- Всегда логируйте ошибки с контекстом