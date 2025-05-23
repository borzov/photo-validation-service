# Многоэтапная сборка для оптимизации размера образа
FROM python:3.9-slim as builder

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-dev \
    libglib2.0-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Финальный образ
FROM python:3.9-slim

WORKDIR /app

# Установка только runtime зависимостей
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    postgresql-client \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Копирование виртуального окружения из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Создание пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копирование файлов проекта
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/
COPY models /app/models

# Создание директорий и установка прав
RUN mkdir -p /app/local_storage && \
    chown -R appuser:appuser /app

# Переключение на непривилегированного пользователя
USER appuser

# Проверка здоровья контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск приложения
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
