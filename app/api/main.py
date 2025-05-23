from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
from app.api.endpoints import validation
from app.db.models import init_db
from app.core.config import settings
from app.core.exceptions import PhotoValidationError
from app.core.logging import get_logger
from app.core.monitoring import performance_monitor, periodic_metrics_update
import asyncio
from app.worker.tasks import start_worker

logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json"
)

# Настройка CORS с улучшенной безопасностью
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Использование списка разрешенных доменов
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],  # Ограничение методов
    allow_headers=["Content-Type", "X-Request-ID"],  # Ограничение заголовков
)

engine = init_db()

# Middleware для логирования запросов и мониторинга
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Генерируем ID запроса для логирования
    request_id = request.headers.get("X-Request-ID", "")
    
    logger.info(
        f"Request started: {request.method} {request.url.path}"
    )
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"Request completed: {request.method} {request.url.path} "
        f"(status: {response.status_code}, time: {process_time:.3f}s)"
    )
    
    return response


# Обработчик исключений
@app.exception_handler(PhotoValidationError)
async def validation_exception_handler(request: Request, exc: PhotoValidationError):
    logger.error(f"PhotoValidationError: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "code": exc.code}
    )


# Подключение роутеров
app.include_router(validation.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """
    Эндпоинт для проверки работоспособности сервиса
    """
    health_status = performance_monitor.get_health_status()
    
    # Возвращаем соответствующий HTTP статус
    if health_status["status"] == "healthy":
        status_code = 200
    elif health_status["status"] == "warning":
        status_code = 200  # Предупреждения не критичны
    else:  # critical
        status_code = 503  # Service Unavailable
        
    return JSONResponse(
        status_code=status_code,
        content={
            "status": health_status["status"],
            "service": "photo-validation-service",
            "issues": health_status["issues"]
        }
    )

@app.get("/metrics")
async def get_metrics():
    """
    Эндпоинт для получения метрик производительности
    """
    return performance_monitor.get_metrics()

@app.get("/metrics/detailed")
async def get_detailed_metrics():
    """
    Эндпоинт для получения детальных метрик и статуса здоровья
    """
    return performance_monitor.get_health_status()

# Запуск обработчика задач при старте приложения
@app.on_event("startup")
async def startup_event():
    # Запуск обработчика задач в фоновом режиме
    asyncio.create_task(start_worker())
    logger.info("Started image processing worker")
    
    # Запуск периодического обновления метрик
    asyncio.create_task(periodic_metrics_update())
    logger.info("Started performance monitoring")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)