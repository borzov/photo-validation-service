FROM python:3.9-slim

WORKDIR /app

# Установка системных зависимостей для OpenCV и PostgreSQL
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем файлы проекта
COPY app /app/app
COPY alembic /app/alembic
COPY alembic.ini /app/
COPY requirements.txt /app/
COPY models /app/models

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Создание директории для хранилища
RUN mkdir -p local_storage

# Запуск приложения
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
