import asyncio
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Семафор для ограничения одновременных обработок
processing_semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PROCESSING)

async def acquire_processing_slot():
    """
    Получает слот для обработки изображения.
    Блокирует выполнение, если достигнуто максимальное количество одновременных обработок.
    """
    logger.debug(f"Waiting for processing slot. Available: {processing_semaphore._value}")
    await processing_semaphore.acquire()
    logger.debug(f"Processing slot acquired. Remaining: {processing_semaphore._value}")
    return True

def release_processing_slot():
    """
    Освобождает слот обработки изображения
    """
    processing_semaphore.release()
    logger.debug(f"Processing slot released. Available: {processing_semaphore._value}")
