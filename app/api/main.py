from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
from app.api.endpoints import validation
from app.db.models import init_db
from app.core.config import settings
from app.core.exceptions import PhotoValidationError
from app.core.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url="/openapi.json"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на список разрешенных доменов
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = init_db()

# Middleware для логирования запросов
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
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=True)
