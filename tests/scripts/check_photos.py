#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse

# Настройки
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PHOTO_DIR = "_photo"
DEFAULT_REPORT_DIR = "reports"
DEFAULT_MAX_ATTEMPTS = 60  # Увеличено количество попыток
DEFAULT_DELAY_SECONDS = 5  # Увеличена задержка между попытками

def check_service_availability(api_url: str) -> bool:
    """
    Проверяет доступность сервиса валидации фотографий
    """
    try:
        response = requests.get(f"{api_url}/health", timeout=10)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except Exception as e:
        print(f"Ошибка при проверке доступности сервиса: {str(e)}")
        return False

def submit_photo(api_url: str, photo_path: str) -> Optional[str]:
    """
    Отправляет фотографию на валидацию и возвращает ID запроса
    """
    try:
        with open(photo_path, "rb") as f:
            files = {"file": (os.path.basename(photo_path), f, "image/jpeg")}
            response = requests.post(
                f"{api_url}/api/v1/validate", 
                files=files,
                timeout=60  # Увеличен таймаут
            )
            
        if response.status_code != 202:
            print(f"Ошибка при отправке фото {photo_path}: {response.text}")
            return None
            
        request_id = response.json().get("requestId")
        print(f"Фото {os.path.basename(photo_path)} отправлено на проверку. ID запроса: {request_id}")
        return request_id
    except Exception as e:
        print(f"Ошибка при отправке фото {photo_path}: {str(e)}")
        return None

def get_validation_result(api_url: str, request_id: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS, delay: int = DEFAULT_DELAY_SECONDS) -> Optional[Dict[str, Any]]:
    """
    Получает результат валидации по ID запроса с повторными попытками
    """
    for attempt in range(max_attempts):
        try:
            response = requests.get(
                f"{api_url}/api/v1/results/{request_id}",
                timeout=20  # Увеличен таймаут
            )
            
            if response.status_code != 200:
                print(f"Ошибка при получении результатов для ID {request_id}: {response.text}")
                time.sleep(delay)
                continue
                
            result = response.json()
            
            # Если обработка завершена, возвращаем результат
            if result.get("status") in ["COMPLETED", "FAILED"]:
                return result
                
            # Иначе ждем и пробуем снова
            print(f"Ожидание результатов для ID {request_id}... (попытка {attempt+1}/{max_attempts}, статус: {result.get('status')})")
            time.sleep(delay)
            
        except Exception as e:
            print(f"Ошибка при получении результатов для ID {request_id}: {str(e)}")
            time.sleep(delay)
    
    print(f"Превышено максимальное количество попыток для ID {request_id}")
    return None

def format_validation_result(result: Dict[str, Any], photo_name: str, processing_time: float) -> str:
    """
    Форматирует результат валидации для вывода в консоль и файл
    """
    status = result.get("status", "UNKNOWN")
    
    if status == "FAILED":
        return f"Фото: {photo_name}\nСтатус: ОШИБКА\nПричина: {result.get('errorMessage', 'Неизвестная ошибка')}\nВремя обработки: {processing_time:.2f} сек.\n"
    
    if status != "COMPLETED":
        return f"Фото: {photo_name}\nСтатус: {status}\nВремя обработки: {processing_time:.2f} сек.\n"
    
    overall_status = result.get("overallStatus", "UNKNOWN")
    
    output = [
        f"Фото: {photo_name}",
        f"Статус обработки: {status}",
        f"Итоговый статус: {overall_status}",
        f"Время обработки: {processing_time:.2f} сек."
    ]
    
    # Преобразуем статусы в понятные сообщения
    status_map = {
        "APPROVED": "ОДОБРЕНО",
        "REJECTED": "ОТКЛОНЕНО",
        "MANUAL_REVIEW": "ТРЕБУЕТСЯ РУЧНАЯ ПРОВЕРКА",
        "PASSED": "ПРОЙДЕНО",
        "FAILED": "НЕ ПРОЙДЕНО",
        "NEEDS_REVIEW": "ТРЕБУЕТСЯ ПРОВЕРКА"
    }
    
    # Добавляем результаты проверок
    if "checks" in result and result["checks"]:
        output.append("\nРезультаты проверок:")
        for check in result["checks"]:
            check_name = check.get("check", "Неизвестная проверка")
            check_status = status_map.get(check.get("status"), check.get("status", "UNKNOWN"))
            
            check_line = f"- {check_name}: {check_status}"
            
            if check.get("status") != "PASSED" and "reason" in check:
                check_line += f" - {check.get('reason')}"
                
            if "details" in check:
                check_line += f" ({check.get('details')})"
                
            output.append(check_line)
    
    # Добавляем список проблем
    if "issues" in result and result["issues"]:
        output.append("\nОбнаруженные проблемы:")
        for issue in result["issues"]:
            output.append(f"- {issue}")
    
    return "\n".join(output) + "\n"

def process_photos(api_url: str, photo_dir: str, report_dir: str, max_attempts: int, delay: int) -> None:
    """
    Обрабатывает все фотографии в указанной директории
    """
    # Проверяем доступность сервиса
    if not check_service_availability(api_url):
        print(f"Сервис валидации фотографий недоступен по адресу {api_url}")
        sys.exit(1)
    
    print(f"Сервис валидации фотографий доступен по адресу {api_url}")
    
    # Создаем директорию для отчетов, если она не существует
    os.makedirs(report_dir, exist_ok=True)
    
    # Проверяем наличие директории с фотографиями
    if not os.path.exists(photo_dir) or not os.path.isdir(photo_dir):
        print(f"Директория с фотографиями '{photo_dir}' не найдена")
        sys.exit(1)
    
    # Получаем список файлов JPEG в директории
    photos = [
        os.path.join(photo_dir, f) for f in os.listdir(photo_dir)
        if f.lower().endswith(('.jpg', '.jpeg')) and os.path.isfile(os.path.join(photo_dir, f))
    ]
    
    if not photos:
        print(f"В директории '{photo_dir}' не найдено JPEG-файлов")
        sys.exit(1)
    
    print(f"Найдено {len(photos)} фотографий для проверки")
    
    # Создаем файл отчета
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(report_dir, f"validation_report_{timestamp}.txt")
    
    # Статистика
    total_time = 0
    successful_validations = 0
    failed_validations = 0
    
    with open(report_path, "w", encoding="utf-8") as report_file:
        # Записываем заголовок отчета
        header = f"Отчет о валидации фотографий от {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
        header += f"Всего фотографий: {len(photos)}\n"
        header += f"Настройки: макс. попыток={max_attempts}, задержка={delay} сек.\n\n"
        
        report_file.write(header)
        print(header)
        
        # Обрабатываем каждую фотографию
        for i, photo_path in enumerate(photos, 1):
            photo_name = os.path.basename(photo_path)
            print(f"\nОбработка фото {i}/{len(photos)}: {photo_name}")
            
            start_time = time.time()
            
            # Отправляем фото на валидацию
            request_id = submit_photo(api_url, photo_path)
            if not request_id:
                end_time = time.time()
                processing_time = end_time - start_time
                total_time += processing_time
                failed_validations += 1
                
                error_msg = f"Фото: {photo_name}\nСтатус: ОШИБКА\nПричина: Не удалось отправить фото на валидацию\nВремя обработки: {processing_time:.2f} сек.\n\n"
                report_file.write(error_msg)
                print(error_msg)
                continue
            
            # Получаем результат валидации
            result = get_validation_result(api_url, request_id, max_attempts, delay)
            
            end_time = time.time()
            processing_time = end_time - start_time
            total_time += processing_time
            
            if not result:
                failed_validations += 1
                error_msg = f"Фото: {photo_name}\nСтатус: ОШИБКА\nПричина: Не удалось получить результат валидации\nВремя обработки: {processing_time:.2f} сек.\n\n"
                report_file.write(error_msg)
                print(error_msg)
                continue
            
            # Форматируем и записываем результат
            successful_validations += 1
            formatted_result = format_validation_result(result, photo_name, processing_time)
            report_file.write(formatted_result + "\n")
            print(formatted_result)
        
        # Записываем итоговую статистику
        summary = f"\nИтоговая статистика:\n"
        summary += f"Всего фотографий: {len(photos)}\n"
        summary += f"Успешно обработано: {successful_validations}\n"
        summary += f"Ошибок обработки: {failed_validations}\n"
        summary += f"Общее время обработки: {total_time:.2f} сек.\n"
        summary += f"Среднее время на фото: {total_time/len(photos):.2f} сек.\n"
        
        report_file.write(summary)
        print(summary)
    
    print(f"\nПроверка завершена. Отчет сохранен в файл: {report_path}")

def main():
    """
    Основная функция скрипта
    """
    parser = argparse.ArgumentParser(description="Скрипт для автоматической проверки фотографий")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"URL API сервиса валидации (по умолчанию: {DEFAULT_API_URL})")
    parser.add_argument("--photo-dir", default=DEFAULT_PHOTO_DIR, help=f"Директория с фотографиями (по умолчанию: {DEFAULT_PHOTO_DIR})")
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR, help=f"Директория для отчетов (по умолчанию: {DEFAULT_REPORT_DIR})")
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS, help=f"Максимальное количество попыток получения результата (по умолчанию: {DEFAULT_MAX_ATTEMPTS})")
    parser.add_argument("--delay", type=int, default=DEFAULT_DELAY_SECONDS, help=f"Задержка между попытками в секундах (по умолчанию: {DEFAULT_DELAY_SECONDS})")
    
    args = parser.parse_args()
    
    process_photos(args.api_url, args.photo_dir, args.report_dir, args.max_attempts, args.delay)

if __name__ == "__main__":
    main()
