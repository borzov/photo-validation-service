# Архитектура автоматического обнаружения модулей

## Обзор

Система автоматического обнаружения модулей решает проблему человеческого фактора при добавлении новых модулей проверки. Теперь при создании нового модуля он автоматически обнаруживается и интегрируется в админ-панель.

## Ключевые компоненты

### 1. Базовый класс `BaseCheck`

Все модули проверки должны наследоваться от `BaseCheck`:

```python
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter

class MyNewCheck(BaseCheck):
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        return CheckMetadata(
            name="my_new_check",
            display_name="Моя новая проверка",
            description="Описание проверки",
            category="image_quality",
            version="1.0.0",
            author="Ваше имя",
            parameters=[
                CheckParameter(
                    name="threshold",
                    type="float",
                    default=0.5,
                    description="Порог срабатывания",
                    min_value=0.0,
                    max_value=1.0,
                    required=True
                )
            ]
        )
    
    def check(self, image, context):
        # Логика проверки
        return {
            "check": "my_new_check",
            "status": "PASSED",
            "details": {}
        }
```

### 2. Система метаданных

Каждый модуль описывает себя через метаданные:

- **name**: Уникальное имя модуля
- **display_name**: Отображаемое имя в админ-панели
- **description**: Описание функциональности
- **category**: Категория (face_detection, image_quality, etc.)
- **version**: Версия модуля
- **author**: Автор модуля
- **parameters**: Список настраиваемых параметров
- **dependencies**: Зависимости (библиотеки)
- **enabled_by_default**: Включен ли по умолчанию

### 3. Параметры модуля

Каждый параметр описывается через `CheckParameter`:

```python
CheckParameter(
    name="parameter_name",           # Имя параметра
    type="int",                      # Тип: int, float, bool, str
    default=10,                      # Значение по умолчанию
    description="Описание параметра", # Описание для админ-панели
    min_value=1,                     # Минимальное значение (опционально)
    max_value=100,                   # Максимальное значение (опционально)
    choices=[1, 2, 3],              # Список допустимых значений (опционально)
    required=True                    # Обязательный ли параметр
)
```

### 4. Автоматическое обнаружение

Система автоматически:

1. **Сканирует** все Python файлы в `app/cv/checks/`
2. **Импортирует** модули и ищет классы, наследующиеся от `BaseCheck`
3. **Регистрирует** найденные модули в реестре
4. **Валидирует** метаданные и параметры
5. **Интегрирует** в админ-панель

### 5. Админ-панель

Новая страница "Модули" (`/admin/checks-discovery`) показывает:

- **Статистику** обнаруженных модулей
- **Категории** модулей
- **Детали** каждого модуля
- **Параметры** с валидацией
- **Поиск и фильтрацию**

## Преимущества новой архитектуры

### ✅ Решенные проблемы

1. **Человеческий фактор**: Модули обнаруживаются автоматически
2. **Забытые настройки**: Параметры извлекаются из метаданных
3. **Документация**: Самодокументирующийся код
4. **Валидация**: Автоматическая проверка параметров
5. **Интеграция**: Автоматическое добавление в админ-панель

### 🚀 Новые возможности

1. **Динамическое обнаружение**: Модули добавляются без перезапуска
2. **Метаданные**: Богатое описание модулей
3. **Категоризация**: Автоматическая группировка
4. **Валидация**: Проверка типов и ограничений
5. **API**: RESTful API для работы с модулями

## Как добавить новый модуль

### Шаг 1: Создайте файл модуля

```bash
# Создайте файл в соответствующей категории
touch app/cv/checks/quality/my_new_check.py
```

### Шаг 2: Реализуйте модуль

```python
from app.cv.checks.registry import BaseCheck, CheckMetadata, CheckParameter

class MyNewCheck(BaseCheck):
    @classmethod
    def get_metadata(cls) -> CheckMetadata:
        return CheckMetadata(
            name="my_new_check",
            display_name="Моя новая проверка",
            description="Проверяет качество изображения",
            category="image_quality",
            version="1.0.0",
            author="Ваше имя",
            parameters=[
                CheckParameter(
                    name="quality_threshold",
                    type="float",
                    default=0.7,
                    description="Минимальный порог качества",
                    min_value=0.0,
                    max_value=1.0,
                    required=True
                ),
                CheckParameter(
                    name="strict_mode",
                    type="bool",
                    default=False,
                    description="Строгий режим проверки",
                    required=False
                )
            ],
            dependencies=["opencv-python"],
            enabled_by_default=True
        )
    
    def __init__(self, **parameters):
        self.parameters = parameters
        # Валидация параметров
        if not self.validate_parameters(parameters):
            raise ValueError("Invalid parameters")
    
    def check(self, image, context):
        # Ваша логика проверки
        quality_score = self._calculate_quality(image)
        threshold = self.parameters.get("quality_threshold", 0.7)
        
        if quality_score >= threshold:
            return {
                "check": "my_new_check",
                "status": "PASSED",
                "details": {
                    "quality_score": quality_score,
                    "threshold": threshold
                }
            }
        else:
            return {
                "check": "my_new_check",
                "status": "FAILED",
                "reason": f"Качество {quality_score:.2f} ниже порога {threshold}",
                "details": {
                    "quality_score": quality_score,
                    "threshold": threshold
                }
            }
    
    def _calculate_quality(self, image):
        # Ваш алгоритм расчета качества
        return 0.8
```

### Шаг 3: Проверьте обнаружение

1. Перезапустите сервис или обновите страницу модулей
2. Откройте `/admin/checks-discovery`
3. Найдите ваш модуль в списке
4. Проверьте параметры и метаданные

## API для работы с модулями

### Получить все модули
```bash
GET /admin/api/checks/discovery
```

### Получить модули по категориям
```bash
GET /admin/api/checks/categories
```

### Получить детали модуля
```bash
GET /admin/api/checks/{check_name}/details
```

### Валидировать конфигурацию
```bash
POST /admin/api/checks/{check_name}/validate
Content-Type: application/json

{
    "config": {
        "quality_threshold": 0.8,
        "strict_mode": true
    }
}
```

## Категории модулей

- **face_detection**: Детекция и анализ лиц
- **image_quality**: Оценка качества изображения
- **background**: Анализ фона
- **object_detection**: Обнаружение объектов
- **accessories**: Детекция аксессуаров
- **pose**: Анализ позы
- **lighting**: Анализ освещения

## Лучшие практики

### 1. Именование
- Используйте snake_case для имен модулей
- Добавляйте версию в имя при значительных изменениях
- Используйте понятные display_name

### 2. Параметры
- Всегда указывайте значения по умолчанию
- Добавляйте ограничения (min_value, max_value)
- Используйте choices для ограниченного набора значений
- Пишите понятные описания

### 3. Валидация
- Всегда валидируйте входные параметры
- Обрабатывайте ошибки gracefully
- Возвращайте информативные сообщения об ошибках

### 4. Производительность
- Кэшируйте тяжелые вычисления
- Используйте ленивую инициализацию
- Оптимизируйте алгоритмы

### 5. Тестирование
- Покрывайте тестами основную логику
- Тестируйте граничные случаи
- Проверяйте валидацию параметров

## Миграция существующих модулей

Для миграции существующих модулей:

1. Добавьте наследование от `BaseCheck`
2. Реализуйте метод `get_metadata()`
3. Добавьте валидацию параметров
4. Обновите конструктор для работы с параметрами
5. Протестируйте обнаружение

## Заключение

Новая архитектура обеспечивает:

- **Автоматизацию**: Нет необходимости вручную регистрировать модули
- **Масштабируемость**: Легко добавлять новые модули
- **Надежность**: Автоматическая валидация и проверки
- **Удобство**: Интуитивная админ-панель
- **Документированность**: Самодокументирующийся код

Система готова к продуктивному использованию и дальнейшему развитию! 