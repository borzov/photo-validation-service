#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import requests
import base64
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse
import random
from io import BytesIO
from pathlib import Path
import shutil # Не используется, но был импортирован ранее
import html
from concurrent.futures import ThreadPoolExecutor, as_completed

# Настройки
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_PHOTO_DIR = "../photos"
DEFAULT_REPORT_DIR = "../reports"
DEFAULT_MAX_ATTEMPTS = 20
DEFAULT_DELAY_SECONDS = 3
MIN_REQUEST_DELAY = 0.1  # Минимальная задержка между запросами в секундах
MAX_REQUEST_DELAY = 0.8  # Максимальная задержка между запросами в секундах

# HTML шаблоны
HTML_HEADER = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Отчет о валидации фотографий</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            color: #333;
        }
        h1, h2, h3 {
            color: #2c3e50;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .summary {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .summary-title {
            margin-top: 0;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        .summary-stats {
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
        }
        .stat-item {
            flex: 1;
            min-width: 150px;
        }
        .photo-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .photo-table th, .photo-table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
            vertical-align: top;
        }
        .photo-table th {
            background-color: #f2f2f2;
            position: sticky;
            top: 0;
        }
        .photo-preview {
            max-width: 200px;
            max-height: 250px;
            display: block;
            margin: 0 auto;
        }
        .status-APPROVED {
            color: #28a745;
            font-weight: bold;
        }
        .status-REJECTED {
            color: #dc3545;
            font-weight: bold;
        }
        .status-MANUAL_REVIEW {
            color: #fd7e14;
            font-weight: bold;
        }
        .status-FAILED, .status-ERROR {
            color: #dc3545;
            font-weight: bold;
        }
        .check-PASSED {
            color: #28a745;
        }
        .check-FAILED {
            color: #dc3545;
        }
        .check-NEEDS_REVIEW {
            color: #fd7e14;
        }
        .check-SKIPPED {
            color: #6c757d;
            font-style: italic;
        }
        .accordion {
            background-color: #f8f9fa;
            color: #444;
            cursor: pointer;
            padding: 10px;
            width: 100%;
            text-align: left;
            border: none;
            outline: none;
            transition: 0.4s;
            border-radius: 3px;
            margin-bottom: 5px;
        }
        .accordion:hover {
            background-color: #e9ecef;
        }
        .panel {
            padding: 0 10px;
            background-color: white;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.2s ease-out;
            border: 1px solid #eee;
            border-top: none;
            margin-bottom: 5px;
        }
        .check-list {
            list-style-type: none;
            padding: 0;
            margin: 0;
        }
        .check-list li {
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }
        .check-list li:last-child {
            border-bottom: none;
        }
        .check-details {
            margin: 10px 0;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 4px solid #dc3545;
        }
        .check-details p {
            margin: 5px 0;
        }
        .check-details pre {
            margin: 5px 0;
            padding: 8px;
            background-color: #fff;
            border: 1px solid #ddd;
            border-radius: 3px;
            overflow-x: auto;
        }
        .check-details ul {
            margin: 5px 0;
            padding-left: 20px;
        }
        .check-details li {
            margin: 3px 0;
        }
        @media print {
            .accordion {
                background-color: #f8f9fa !important;
                color: #444 !important;
            }
            .panel {
                max-height: none !important;
                display: block !important;
            }
            .photo-preview {
                max-width: 100px;
                max-height: 125px;
            }
            .check-details {
                break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Отчет о валидации фотографий</h1>
"""

HTML_FOOTER = """
        </div>
        <script>
            // Функции для работы с аккордеоном
            function expandAll() {
                document.querySelectorAll('.panel').forEach(panel => {
                    panel.style.maxHeight = panel.scrollHeight + "px";
                });
            }

            function collapseAll() {
                document.querySelectorAll('.panel').forEach(panel => {
                    panel.style.maxHeight = "0px";
                });
            }

            // Обработчики для аккордеона
            document.querySelectorAll('.accordion').forEach(button => {
                button.addEventListener('click', function() {
                    this.classList.toggle('active');
                    var panel = this.nextElementSibling;
                    if (panel.style.maxHeight) {
                        panel.style.maxHeight = null;
                    } else {
                        panel.style.maxHeight = panel.scrollHeight + "px";
                    }
                });
            });

            // Автоматически раскрываем все панели при загрузке
            document.addEventListener('DOMContentLoaded', expandAll);
        </script>
    </body>
</html>
"""

def check_service_availability(api_url: str) -> bool:
    """
    Проверяет доступность сервиса валидации фотографий
    """
    try:
        health_url = f"{api_url}/health"
        print(f"Checking service availability at {health_url}...")
        response = requests.get(health_url, timeout=10)
        if response.status_code == 200:
            try:
                data = response.json()
                # Принимаем как старый формат "ok", так и новый "healthy", и "warning"
                status = data.get("status")
                if status in ["ok", "healthy", "warning"]:
                    if status == "warning":
                        print(f"Service is available with warnings: {data.get('issues', [])}")
                    else:
                        print("Service is available.")
                    return True
                else:
                    print(f"Service health check returned unexpected status: {data}")
                    return False
            except json.JSONDecodeError:
                 print(f"Service health check returned non-JSON response: {response.text}")
                 return False
        else:
            print(f"Service health check failed with status code {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error checking service availability: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error during service check: {str(e)}")
        return False

def submit_photo(api_url: str, photo_path: str) -> Optional[str]:
    """
    Отправляет фотографию на валидацию и возвращает ID запроса
    """
    submit_url = f"{api_url}/api/v1/validate"
    photo_name = os.path.basename(photo_path)
    try:
        with open(photo_path, "rb") as f:
            files = {"file": (photo_name, f, "image/jpeg")} # Предполагаем jpeg
            print(f"Submitting {photo_name} to {submit_url}...")
            response = requests.post(
                submit_url,
                files=files,
                timeout=60  # Увеличен таймаут
            )

        if response.status_code == 202:
            try:
                request_id = response.json().get("requestId")
                if request_id:
                    print(f"Photo {photo_name} submitted successfully. Request ID: {request_id}")
                    return request_id
                else:
                    print(f"Error submitting photo {photo_name}: Response JSON does not contain 'requestId'. Response: {response.text}")
                    return None
            except json.JSONDecodeError:
                 print(f"Error submitting photo {photo_name}: Could not decode JSON response. Status: {response.status_code}, Response: {response.text}")
                 return None
        elif response.status_code == 400:
            # Return error details for 400 responses for better error handling
            try:
                error_detail = response.json().get("detail", "Unknown validation error")
                print(f"Photo {photo_name} rejected during validation: {error_detail}")
                return f"VALIDATION_ERROR:{error_detail}"
            except json.JSONDecodeError:
                print(f"Error submitting photo {photo_name}: Validation failed but could not parse error. Response: {response.text}")
                return "VALIDATION_ERROR:Unknown validation error"
        else:
            print(f"Error submitting photo {photo_name}: Received status code {response.status_code}. Response: {response.text}")
            return None

    except FileNotFoundError:
        print(f"Error submitting photo: File not found at {photo_path}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error submitting photo {photo_name}: Request failed: {str(e)}")
        return None
    except Exception as e:
        print(f"Unexpected error submitting photo {photo_name}: {str(e)}")
        return None

def get_validation_result(api_url: str, request_id: str, max_attempts: int = 30, delay: float = 0.2) -> Optional[Dict[str, Any]]:
    result_url = f"{api_url}/api/v1/results/{request_id}"
    import time
    start_time = time.time()
    last_result = None
    for attempt in range(max_attempts):
        try:
            response = requests.get(result_url, timeout=10)  # Increased timeout
            if response.status_code == 200:
                try:
                    result = response.json()
                    status = result.get("status")
                    last_result = result
                    if status in ["COMPLETED", "FAILED"]:
                        return result
                except json.JSONDecodeError:
                    pass
            elif response.status_code == 404:
                return None
        except Exception:
            pass
        # Increased overall timeout from 6 to 30 seconds
        if time.time() - start_time > 30:
            break
        if attempt < max_attempts - 1:
            time.sleep(delay)
    return last_result

def get_image_info(image_path: str) -> Dict[str, Any]:
    """
    Получает базовую информацию об изображении и создает превью.
    """
    file_name = os.path.basename(image_path)
    image_info = {
        "file_name": file_name,
        "file_path": image_path, # Сохраняем путь для чтения
        "file_size": None,
        "file_size_kb": None,
        "preview_base64": None,
        "error": None
    }
    try:
        # Получаем размер файла
        image_info["file_size"] = os.path.getsize(image_path)
        image_info["file_size_kb"] = round(image_info["file_size"] / 1024, 2)

        # Создаем превью изображения в формате base64
        # Читаем файл здесь, чтобы не хранить путь вне этой функции
        with open(image_path, "rb") as img_file:
            img_data = img_file.read()
            # Можно добавить сюда ресайз для превью, если файлы большие
            # from PIL import Image
            # try:
            #     pil_img = Image.open(BytesIO(img_data))
            #     pil_img.thumbnail((200, 250)) # Макс. размер превью
            #     buffer = BytesIO()
            #     pil_img.save(buffer, format="JPEG")
            #     img_data_resized = buffer.getvalue()
            #     image_info["preview_base64"] = base64.b64encode(img_data_resized).decode('utf-8')
            # except Exception as pil_e:
            #     print(f"Warning: Could not resize preview for {file_name}: {pil_e}. Using original.")
            #     image_info["preview_base64"] = base64.b64encode(img_data).decode('utf-8')
            # Пока используем оригинал для простоты
            image_info["preview_base64"] = base64.b64encode(img_data).decode('utf-8')

    except FileNotFoundError:
        print(f"Error getting image info: File not found at {image_path}")
        image_info["error"] = "File not found"
    except Exception as e:
        print(f"Error getting image info for {file_name}: {str(e)}")
        image_info["error"] = str(e)

    return image_info


def generate_html_report(results: List[Dict[str, Any]], report_dir: str, timestamp: str) -> str:
    """
    Генерирует HTML-отчет по результатам валидации
    """
    # Создаем директорию для ресурсов отчета
    report_resources_dir = os.path.join(report_dir, f"report_resources_{timestamp}")
    try:
        os.makedirs(report_resources_dir, exist_ok=True)
    except OSError as e:
        print(f"Ошибка при создании директории для ресурсов отчета: {e}")
        raise

    # Создаем HTML файл
    report_path = os.path.join(report_dir, f"validation_report_{timestamp}.html")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            # Записываем заголовок
            f.write(HTML_HEADER)
            
            # Начинаем таблицу с результатами
            f.write("""
                <table class="photo-table">
                    <tr>
                        <th>Фото</th>
                        <th>Информация</th>
                        <th>Результат валидации</th>
                    </tr>
            """)

            # Обрабатываем каждый результат
            for result in results:
                try:
                    image_info = result.get("image_info", {})
                    validation_result = result.get("validation_result", {})
                    
                    # Получаем информацию о файле
                    file_name = image_info.get("file_name", "Неизвестно")
                    file_size = image_info.get("file_size", 0)
                    file_size_kb = file_size / 1024 if file_size else 0
                    file_name_str = html.escape(str(file_name))
                    file_size_kb_str = f"{file_size_kb:.1f}"

                    # Копируем изображение в ресурсы отчета
                    preview_rel_path = ""
                    try:
                        if image_info.get("file_path"):
                            preview_name = f"preview_{os.path.basename(file_name)}"
                            preview_path = os.path.join(report_resources_dir, preview_name)
                            preview_rel_path = f"report_resources_{timestamp}/{preview_name}"
                            shutil.copy2(image_info["file_path"], preview_path)
                    except (OSError, IOError) as e:
                        print(f"Ошибка при копировании превью для {file_name}: {e}")
                        preview_rel_path = ""

                    # Формируем HTML для строки таблицы
                    preview_cell = f"<img src='{preview_rel_path}' class='photo-preview' alt='{file_name_str}'>" if preview_rel_path else "Превью недоступно"
                    
                    # Формируем информацию о файле
                    file_info_html = f"""
                        <p><strong>Имя файла:</strong> {file_name_str}</p>
                        <p><strong>Размер:</strong> {file_size_kb_str} КБ</p>
                    """
                    
                    # Добавляем ошибку, если есть
                    if image_info.get("error"):
                        file_info_html += f"<p class='status-FAILED'>Ошибка: {html.escape(str(image_info['error']))}</p>"

                    # Формируем HTML для результатов валидации
                    validation_html = ""
                    if not validation_result:
                        validation_html = "<p class='status-FAILED'>Ошибка: Не удалось получить результат валидации</p>"
                    else:
                        # Use overallStatus for display if available, otherwise fall back to status
                        display_status = validation_result.get('overallStatus', validation_result.get('status', 'UNKNOWN'))
                        status_class = f"status-{display_status}"
                        validation_html = f"<p class='{status_class}'><strong>Статус:</strong> {display_status}</p>"
                        
                        if validation_result.get("processingTime") is not None:
                            validation_html += f"<p><strong>Время обработки:</strong> {validation_result['processingTime']:.2f} сек</p>"

                        # Показываем основные проблемы, если они есть
                        if validation_result.get("issues"):
                            validation_html += f"""
                                <div class="check-details">
                                    <p><strong>Основные проблемы:</strong></p>
                                    <ul>
                            """
                            for issue in validation_result["issues"]:
                                validation_html += f"<li>{html.escape(str(issue))}</li>"
                            validation_html += """
                                    </ul>
                                </div>
                            """

                        # Добавляем детали проверок
                        if validation_result.get("checks", []):
                            validation_html += f"""
                                <button class="accordion">Результаты проверок ({len(validation_result['checks'])})</button>
                                <div class="panel">
                                    <ul class="check-list">
                            """
                            
                            for check in validation_result['checks']:
                                if not isinstance(check, dict):
                                    continue
                                    
                                check_name = check.get("check", "unknown")
                                check_status = check.get("status", "UNKNOWN")
                                check_reason = check.get("reason", "")
                                check_details = check.get("details", "")
                                check_params = check.get("parameters", {})
                                check_results = check.get("results", {})
                                
                                status_class = f"check-{check_status}"
                                
                                validation_html += f"""
                                    <li>
                                        <strong>{html.escape(str(check_name))}</strong>: 
                                        <span class="{status_class}">{check_status}</span>
                                """
                                
                                # Показываем причину для всех проверок, если она есть
                                if check_reason:
                                    validation_html += f"""
                                        <div class="check-details">
                                            <p><strong>Причина:</strong> {html.escape(str(check_reason))}</p>
                                        </div>
                                    """
                                
                                # Для FAILED проверок всегда показываем расширенную информацию
                                if check_status == "FAILED":
                                    # Показываем параметры проверки из конфига
                                    if check_params:
                                        validation_html += f"""
                                            <div class="check-details">
                                                <p><strong>Параметры проверки:</strong></p>
                                                <pre>{html.escape(str(check_params))}</pre>
                                            </div>
                                        """
                                    
                                    # Показываем результаты анализа
                                    if check_results:
                                        validation_html += f"""
                                            <div class="check-details">
                                                <p><strong>Результаты анализа:</strong></p>
                                                <pre>{html.escape(str(check_results))}</pre>
                                            </div>
                                        """
                                    
                                    # Показываем детали проверки
                                    if check_details:
                                        validation_html += f"""
                                            <div class="check-details">
                                                <p><strong>Детали проверки:</strong></p>
                                                <pre>{html.escape(str(check_details))}</pre>
                                            </div>
                                        """
                                    
                                    # Для facePose добавляем пояснение о значениях
                                    if check_name == "facePose" and isinstance(check_details, dict):
                                        yaw = check_details.get('yaw', 0)
                                        roll = check_details.get('roll', 0)
                                        pitch = check_details.get('pitch', 0)
                                        thresholds = check_details.get('thresholds', {})
                                        validation_html += f"""
                                            <div class="check-details">
                                                <p><strong>Интерпретация значений:</strong></p>
                                                <ul>
                                                    <li>Yaw (поворот влево/вправо): {yaw:.2f}° (макс. {thresholds.get('max_yaw', 0)}°)</li>
                                                    <li>Roll (наклон головы): {roll:.2f}° (макс. {thresholds.get('max_roll', 0)}°)</li>
                                                    <li>Pitch (наклон вперед/назад): {pitch:.2f}° (макс. {thresholds.get('max_pitch', 0)}°)</li>
                                                </ul>
                                            </div>
                                        """
                                    
                                    # Для redEye добавляем детали проверки
                                    if check_name == "redEye" and isinstance(check_details, dict):
                                        affected_eyes = check_details.get('affected_eyes', [])
                                        validation_html += f"""
                                            <div class="check-details">
                                                <p><strong>Детали проверки красных глаз:</strong></p>
                                                <ul>
                                                    <li>Затронутые глаза: {', '.join(affected_eyes)}</li>
                                                </ul>
                                            </div>
                                        """
                                    
                                    # Для background добавляем детали проверки
                                    if check_name == "background" and isinstance(check_details, dict):
                                        threshold = check_details.get('threshold', 0)
                                        std_dev = check_details.get('background_mean_std_dev', 0)
                                        mean_bgr = check_details.get('background_mean_bgr', [0, 0, 0])
                                        validation_html += f"""
                                            <div class="check-details">
                                                <p><strong>Детали проверки фона:</strong></p>
                                                <ul>
                                                    <li>Стандартное отклонение: {std_dev:.2f} (порог: {threshold})</li>
                                                    <li>Средний цвет (BGR): [{', '.join(f'{x:.1f}' for x in mean_bgr)}]</li>
                                                </ul>
                                            </div>
                                        """
                                
                                validation_html += "</li>"
                            
                            validation_html += """
                                    </ul>
                                </div>
                            """

                    # Добавляем строку в таблицу
                    f.write(f"""
                        <tr>
                            <td>{preview_cell}</td>
                            <td>{file_info_html}</td>
                            <td>{validation_html}</td>
                        </tr>
                    """)
                except Exception as e:
                    print(f"Ошибка при обработке результата: {e}")
                    continue

            # Закрываем таблицу
            f.write("</table>")
            
            # Закрываем HTML
            f.write(HTML_FOOTER)

        print(f"HTML отчет сгенерирован: {report_path}")
        return report_path
    except Exception as e:
        print(f"Ошибка при генерации отчета: {e}")
        raise

def process_single_photo(photo_path, api_url, max_attempts, delay):
    image_info = get_image_info(photo_path)
    result = {"image_info": image_info, "validation_result": None, "error": image_info.get("error")}
    
    # If there's an error getting image info, return early
    if result["error"]:
        return result
    
    # Try to submit photo
    request_id = submit_photo(api_url, photo_path)
    if not request_id:
        result["error"] = "Failed to submit photo to API"
        return result
    
    # Check if submission returned a validation error
    if isinstance(request_id, str) and request_id.startswith("VALIDATION_ERROR:"):
        error_detail = request_id[len("VALIDATION_ERROR:"):]
        # Create a fake validation result for display purposes
        result["validation_result"] = {
            "status": "FAILED", 
            "overallStatus": "REJECTED",
            "processingTime": 0.0,
            "checks": [],
            "issues": [error_detail]  # Clean text instead of JSON object
        }
        return result
    
    # If submission succeeded, try to get validation result
    validation_result = get_validation_result(api_url, request_id, max_attempts, delay)
    if not validation_result:
        result["error"] = f"Failed to retrieve validation result (Request ID: {request_id})"
    else:
        result["validation_result"] = validation_result
    
    return result

def process_photos_parallel(api_url: str, photo_dir: str, report_dir: str, max_attempts: int, delay: float, max_workers: int = 8) -> None:
    if not check_service_availability(api_url):
        print(f"Service at {api_url} is not available. Exiting.")
        sys.exit(1)
    try:
        os.makedirs(report_dir, exist_ok=True)
    except OSError as e:
        print(f"Error creating report directory '{report_dir}': {e}")
        sys.exit(1)
    photo_path_obj = Path(photo_dir)
    if not photo_path_obj.is_dir():
        print(f"Photo directory '{photo_dir}' not found or is not a directory.")
        sys.exit(1)
    photos = sorted([
        str(p) for p in photo_path_obj.iterdir()
        if p.is_file() and p.suffix.lower() in ['.jpg', '.jpeg']
    ])
    if not photos:
        print(f"No JPEG files found in directory '{photo_dir}'.")
        sys.exit(0)
    print(f"Found {len(photos)} photos to process in '{photo_dir}'.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    start_run_time = time.time()
    report_data = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(process_single_photo, photo_path, api_url, max_attempts, delay)
            for photo_path in photos
        ]
        for future in as_completed(futures, timeout=max(2, len(photos))):
            try:
                report_data.append(future.result(timeout=1))
            except Exception as e:
                report_data.append({"error": str(e)})
    end_run_time = time.time()
    total_run_time = end_run_time - start_run_time
    try:
        report_path = generate_html_report(report_data, report_dir, timestamp)
    except Exception as report_e:
        print(f"\nFATAL ERROR: Failed to generate HTML report: {report_e}")
        print("Raw results data:")
        print(json.dumps(report_data, indent=2, ensure_ascii=False))
        sys.exit(1)
    print(f"\n--- Run Summary ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(f"Total photos found: {len(photos)}")
    print(f"Total script execution time: {total_run_time:.2f} sec.")
    print(f"Check completed. Report saved to: {report_path}")
    try:
        import webbrowser
        report_abs_path = os.path.abspath(report_path)
        webbrowser.open(f"file://{report_abs_path}")
        print(f"Attempting to open report in default browser...")
    except Exception as e:
        print(f"Could not automatically open the report: {str(e)}")
        print(f"Please open the file manually: {os.path.abspath(report_path)}")

def main():
    parser = argparse.ArgumentParser(description="Script for automatic photo validation via API")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"Validation service API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--photo-dir", default=DEFAULT_PHOTO_DIR, help=f"Directory with photos (default: {DEFAULT_PHOTO_DIR})")
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR, help=f"Directory for reports (default: {DEFAULT_REPORT_DIR})")
    parser.add_argument("--max-attempts", type=int, default=30, help=f"Max attempts to get result (default: 30)")
    parser.add_argument("--delay", type=float, default=1, help=f"Delay between attempts in seconds (default: 1)")
    parser.add_argument("--threads", type=int, default=8, help=f"Number of parallel threads (default: 8)")
    args = parser.parse_args()
    print("Starting photo validation process...")
    print(f"API URL: {args.api_url}")
    print(f"Photo Directory: {args.photo_dir}")
    print(f"Report Directory: {args.report_dir}")
    print(f"Max Attempts: {args.max_attempts}, Delay: {args.delay}s, Threads: {args.threads}")
    process_photos_parallel(args.api_url, args.photo_dir, args.report_dir, args.max_attempts, args.delay, args.threads)

if __name__ == "__main__":
    main()