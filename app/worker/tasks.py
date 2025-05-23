# ФАЙЛ: app/worker/tasks.py

import asyncio
import time
from datetime import datetime
import cv2
import numpy as np
import os
from typing import Dict, Any, List, Tuple, Union, Optional, Set
import traceback
import json
import math
import weakref

from app.core.logging import get_logger
from app.core.concurrency import acquire_processing_slot, release_processing_slot
from app.db.repositories import ValidationRequestRepository
from app.storage.client import storage_client
from app.core.config import settings
# Импортируем новую систему проверок
from app.cv.checks.runner import CheckRunner
from app.cv.checks.registry import check_registry
from app.core.check_config import check_config

logger = get_logger(__name__)

# Очередь задач для обработки изображений
processing_queue = asyncio.Queue()

# Множество для отслеживания активных задач
active_tasks: Set[asyncio.Task] = set()

def cleanup_completed_tasks():
    """Очищает завершенные задачи из множества активных задач"""
    completed_tasks = {task for task in active_tasks if task.done()}
    for task in completed_tasks:
        active_tasks.discard(task)
        # Логируем исключения из завершенных задач
        if task.exception():
            logger.error(f"Task completed with exception: {task.exception()}")

# --- Вспомогательная функция для конвертации типов NumPy ---
def convert_numpy_types(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Рекурсивно обходит структуру данных (словари, списки)
    и конвертирует типы NumPy в нативные типы Python.
    Возвращает None для NaN и Inf. Исправлено для NumPy 2.0.
    """
    if isinstance(data, dict):
        # Создаем новый словарь, чтобы не модифицировать исходный во время итерации
        new_dict = {}
        for key, value in data.items():
            new_dict[key] = convert_numpy_types(value)
        return new_dict
    elif isinstance(data, list):
        # Рекурсивно конвертируем элементы списка
        return [convert_numpy_types(item) for item in data]
    # --- Целые числа NumPy ---
    elif isinstance(data, (np.int_, np.intc, np.intp, np.int8,
                          np.int16, np.int32, np.int64, np.uint8,
                          np.uint16, np.uint32, np.uint64)):
        # Конвертируем в стандартный Python int
        return int(data)
    # --- Числа с плавающей точкой NumPy ---
    # Убрали np.float_ (удален в NumPy 2.0)
    elif isinstance(data, (np.float16, np.float32, np.float64)):
        # Проверяем на NaN/Infinity перед конвертацией в Python float
        # Используем стандартные math.isnan и math.isinf
        if data is None or math.isnan(data) or math.isinf(data):
            # Возвращаем None для невалидных float, т.к. JSON их не поддерживает
            return None
        # Конвертируем в стандартный Python float
        return float(data)
    # --- Комплексные числа NumPy ---
    elif isinstance(data, (np.complex64, np.complex128)):
        # Проверяем real/imag части на NaN/Infinity
        real_part = float(data.real) if data.real is not None and not math.isnan(data.real) and not math.isinf(data.real) else None
        imag_part = float(data.imag) if data.imag is not None and not math.isnan(data.imag) and not math.isinf(data.imag) else None
        # Если обе части None, можно вернуть None или оставить словарь
        if real_part is None and imag_part is None:
             return None
        # Возвращаем как словарь с Python float/None
        return {'real': real_part, 'imag': imag_part}
    # --- Массивы NumPy ---
    elif isinstance(data, (np.ndarray,)):
        # Конвертируем массив в список и рекурсивно обрабатываем его элементы
        return convert_numpy_types(data.tolist())
    # --- Булевы значения NumPy ---
    elif isinstance(data, (np.bool_)):
        # Конвертируем в стандартный Python bool
        return bool(data)
    # --- Void NumPy (редко) ---
    elif isinstance(data, (np.void)):
        # Представляем как None
        return None
    # --- Дата и время NumPy ---
    elif isinstance(data, np.datetime64):
        try:
            # Проверяем на NaT (Not a Time)
            if data == np.datetime64('NaT'): return None
            # Пробуем преобразовать в стандартный datetime Python
            py_dt_or_int = data.astype(object)
            if isinstance(py_dt_or_int, datetime):
                 # Возвращаем в ISO формате для совместимости с JSON
                 return py_dt_or_int.isoformat()
            else:
                 # Если не получилось (например, дата вне диапазона), возвращаем строку
                 return str(data)
        except Exception:
             # В случае любой ошибки при конвертации вернем строку
             return str(data)
    # --- Временные дельты NumPy ---
    elif isinstance(data, np.timedelta64):
        try:
            # Проверяем на NaT
            if data == np.timedelta64('NaT'): return None
            # Конвертируем в секунды (Python float)
            return float(data / np.timedelta64(1, 's'))
        except Exception:
             # В случае ошибки вернем строку
             return str(data)

    # Если тип уже совместим с JSON или не является специфичным типом NumPy,
    # возвращаем как есть (int, float, str, list, dict, bool, None)
    return data

# --- Основная функция обработки изображения ---
async def process_image_task(request_id: str, file_path: str) -> None:
    """
    Асинхронная задача для обработки и валидации изображения.
    Использует новую модульную систему проверок.
    """
    await acquire_processing_slot() # Получаем слот для обработки
    logger.info(f"Starting image processing for request: {request_id} from file: {file_path}")
    start_time = time.time()

    # Инициализируем переменные, доступные во всех блоках (try/except/finally)
    checks: List[Dict[str, Any]] = []
    overall_status: str = "FAILED" # Статус по умолчанию при ошибке
    issues: List[str] = []
    final_processing_time: float = 0.0
    error_message_short: Optional[str] = None # Краткое сообщение об ошибке для БД

    try:
        # Шаг 1: Обновляем статус на PROCESSING
        ValidationRequestRepository.update_status(request_id, "PROCESSING")

        # Шаг 2: Получаем и декодируем изображение
        logger.debug(f"[{request_id}] Getting image from storage...")
        image_bytes = storage_client.get_file(file_path)
        logger.debug(f"[{request_id}] Decoding image...")
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        if image is None:
            raise ValueError("Failed to decode image (cv2.imdecode returned None)")
        logger.debug(f"[{request_id}] Image decoded successfully, shape: {image.shape}")
        
        # Шаг 3: Подготовка контекста для проверок
        context = {
            "request_id": request_id,
            "file_path": file_path,
            "image_shape": image.shape,
        }
        
        # Шаг 4: Запуск проверок с использованием CheckRunner
        logger.debug(f"[{request_id}] Running checks...")
        check_runner = CheckRunner()
        validation_result = await check_runner.run_checks(image, context)
        
        # Шаг 5: Обработка результатов проверок
        overall_status = validation_result["overall_status"]
        checks = validation_result["checks"]
        issues = validation_result["issues"]

        required_checks = set(check_config.get_enabled_checks())
        found_checks = {c.get("check"): c for c in checks}
        logger.warning(f"[{request_id}] check_order: {list(required_checks)}")
        logger.warning(f"[{request_id}] checks: {[ (c.get('check'), c.get('status')) for c in checks ]}")
        all_checks_completed = True
        for check_id in required_checks:
            c = found_checks.get(check_id)
            if not c or c.get("status") is None:
                all_checks_completed = False
                logger.warning(f"[{request_id}] Check '{check_id}' not completed (status: {c.get('status') if c else 'MISSING'}), not marking as COMPLETED.")
                break

        # Шаг 6: Конвертируем типы NumPy для сохранения в БД
        logger.debug(f"[{request_id}] Converting check results...")
        checks_final = convert_numpy_types(checks)
        issues_final = convert_numpy_types(issues)

        # Шаг 7: Сохранение успешного результата в БД
        final_processing_time = time.time() - start_time
        logger.debug(f"[{request_id}] Updating result in database...")
        if all_checks_completed:
            ValidationRequestRepository.update_result(
                request_id=request_id,
                status="COMPLETED",
                overall_status=overall_status,
                checks=checks_final,
                issues=issues_final,
                processed_at=datetime.utcnow(),
                processing_time=final_processing_time
            )
            logger.info(f"Completed processing for request: {request_id}, overall status: {overall_status}, time: {final_processing_time:.3f}s")
        else:
            ValidationRequestRepository.update_status(request_id, "PROCESSING")
            logger.info(f"[{request_id}] Not all checks completed, status left as PROCESSING.")

    except Exception as e:
        final_processing_time = time.time() - start_time
        tb_str = traceback.format_exc()
        error_message_short = f"Processing error: {type(e).__name__}: {str(e)}"
        error_message_full = f"{error_message_short}\nTraceback:\n{tb_str}"
        logger.error(f"Error processing image for request: {request_id}. Error: {error_message_full}", extra={"request_id": request_id})

        try:
            checks_final_on_error = convert_numpy_types(checks)
            issues_on_error = convert_numpy_types(issues)
            ValidationRequestRepository.update_error(
                request_id=request_id,
                error_message=error_message_short,
                processing_time=final_processing_time,
                status="FAILED",
                checks=checks_final_on_error,
                issues=issues_on_error,
                overall_status=overall_status
            )
            logger.info(f"Recorded FAILED status for request {request_id} due to processing error.")
        except Exception as db_e:
            logger.error(f"Failed to update error status in DB for request {request_id}: {db_e}")
            try:
                ValidationRequestRepository.update_error(
                    request_id=request_id,
                    error_message=f"Processing error: {type(e).__name__} | DB update failed: {type(db_e).__name__}",
                    processing_time=final_processing_time,
                    status="FAILED"
                )
            except Exception as final_db_e:
                logger.critical(f"Failed to update minimal error status for request {request_id}: {final_db_e}")

    finally:
        try:
            logger.debug(f"[{request_id}] Deleting file from storage: {file_path}")
            storage_client.delete_file(file_path)
            logger.debug(f"[{request_id}] File deleted from storage: {file_path}")
        except Exception as del_e:
            logger.error(f"Failed to delete file {file_path} from storage: {type(del_e).__name__}: {str(del_e)}")

        logger.debug(f"[{request_id}] Releasing processing slot...")
        release_processing_slot()
        logger.debug(f"[{request_id}] Processing slot released for request {request_id}.")


# --- Функции start_worker и add_processing_task ---
async def start_worker():
    """
    Запускает обработчик очереди задач asyncio.
    """
    logger.info("Starting image processing worker...")
    while True:
        try:
            # Ожидаем и получаем задачу из очереди
            task_data = await processing_queue.get()
            request_id = task_data.get("request_id")
            file_path = task_data.get("file_path")

            # Проверяем, что получили валидные данные
            if request_id and file_path:
                logger.info(f"Dequeued task for request: {request_id} (file: {file_path})")
                # Запускаем обработку задачи в фоне (не блокируем цикл воркера)
                task = asyncio.create_task(process_image_task(request_id, file_path))
                active_tasks.add(task)
            else:
                logger.warning(f"Invalid task data received from queue: {task_data}")

            # Отмечаем задачу как выполненную в очереди asyncio
            processing_queue.task_done()

            # Очищаем завершенные задачи
            cleanup_completed_tasks()

        except asyncio.CancelledError:
             # Если воркер отменяют, логируем и выходим из цикла
             logger.info("Worker task cancelled.")
             break
        except Exception as e:
             # Логируем любую другую критическую ошибку в главном цикле воркера
             tb_str = traceback.format_exc()
             logger.exception(f"Critical exception in worker main loop: {type(e).__name__}: {str(e)}\nTraceback:\n{tb_str}")
             # Небольшая пауза перед следующей попыткой взять задачу,
             # чтобы не перегружать CPU в случае постоянной ошибки
             await asyncio.sleep(1)


async def add_processing_task(request_id: str, file_path: str):
    """
    Добавляет задачу обработки изображения в очередь asyncio.
    """
    # Кладем словарь с данными задачи в очередь
    await processing_queue.put({"request_id": request_id, "file_path": file_path})
    # Логируем добавление и текущий размер очереди для мониторинга
    logger.info(f"Added processing task for request: {request_id}, queue size now: {processing_queue.qsize()}")