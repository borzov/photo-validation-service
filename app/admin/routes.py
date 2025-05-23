"""
Маршруты для админ панели.
"""
import json
import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import Request, Form, HTTPException, Depends, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session
from app.admin.app import admin_app
from app.core.config import settings
from app.config.schema import ConfigurationSchema
from app.config.manager import ConfigurationManager
from app.db.session import get_db
from app.api.models.validation import ValidationResult as ValidationResultModel
from app.db.models import ValidationRequest
from app.core.monitoring import performance_monitor
from app.core.logging import get_logger
from app.admin.services.check_discovery import check_discovery_service

logger = get_logger(__name__)

# Templates
templates = Jinja2Templates(directory="app/admin/templates")

config_manager = ConfigurationManager()

@admin_app.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Главная страница админ панели"""
    try:
        # Получаем базовую статистику
        config = config_manager.get_config()
        
        context = {
            "request": request,
            "title": "Дашборд",
            "config": config,
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage('/').percent
            }
        }
        
        return templates.TemplateResponse("dashboard.html", context)
        
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "error": "Ошибка загрузки дашборда"
        })

@admin_app.get("/system", response_class=HTMLResponse)
async def system_config(request: Request):
    """Страница системных настроек"""
    try:
        config = config_manager.get_config()
        
        context = {
            "request": request,
            "title": "Системные настройки",
            "config": config
        }
        
        return templates.TemplateResponse("system_config.html", context)
        
    except Exception as e:
        logger.error(f"Error loading system config: {e}")
        return templates.TemplateResponse("system_config.html", {
            "request": request,
            "error": "Ошибка загрузки системных настроек"
        })

@admin_app.get("/validation", response_class=HTMLResponse)
async def validation_config(request: Request):
    """Страница настроек валидации"""
    try:
        config = config_manager.get_config()
        
        context = {
            "request": request,
            "title": "Настройки валидации",
            "config": config
        }
        
        return templates.TemplateResponse("validation_config.html", context)
        
    except Exception as e:
        logger.error(f"Error loading validation config: {e}")
        return templates.TemplateResponse("validation_config.html", {
            "request": request,
            "error": "Ошибка загрузки настроек валидации"
        })

@admin_app.get("/operations", response_class=HTMLResponse)
async def operations_monitoring(request: Request, db: Session = Depends(get_db)):
    """Страница мониторинга операций"""
    try:
        # Получаем базовую статистику
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        
        # Статистика за последние 24 часа
        successful_today = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "APPROVED"
            )
        ).count()
        
        rejected_today = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "REJECTED"
            )
        ).count()
        
        # Среднее время обработки
        avg_time_result = db.query(func.avg(ValidationRequest.processing_time)).filter(
            ValidationRequest.created_at >= day_ago
        ).scalar()
        
        avg_processing_time = float(avg_time_result) if avg_time_result else 0.0
        
        # Системные метрики
        cpu_usage = psutil.cpu_percent(interval=1)
        memory_usage = psutil.virtual_memory().percent
        
        # Метрики кэша из performance_monitor
        cache_stats = performance_monitor.get_cache_stats()
        cache_hit_rate = cache_stats.get('hit_rate', 0.0) * 100
        
        context = {
            "request": request,
            "title": "Мониторинг операций",
            "active_operations": 0,  # Will be updated via API
            "successful_today": successful_today,
            "rejected_today": rejected_today,
            "avg_processing_time": avg_processing_time,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "cache_hit_rate": cache_hit_rate
        }
        
        return templates.TemplateResponse("operations.html", context)
        
    except Exception as e:
        logger.error(f"Error loading operations page: {e}")
        return templates.TemplateResponse("operations.html", {
            "request": request,
            "error": "Ошибка загрузки страницы операций"
        })

@admin_app.post("/validation")
async def update_validation_config(
    request: Request,
    # Global settings
    stop_on_failure: bool = Form(False),
    max_check_time: float = Form(5.0),
    max_concurrent: int = Form(5),
    
    # Image requirements
    min_width: int = Form(400),
    min_height: int = Form(400),
    max_file_size: float = Form(5.0),
    allowed_formats: List[str] = Form(["jpg", "jpeg"]),
    
    # Face detection
    face_detection_enabled: bool = Form(False),
    face_min_count: int = Form(1),
    face_max_count: int = Form(1),
    face_confidence_threshold: float = Form(0.4),
    face_min_area_ratio: float = Form(0.05),
    face_max_area_ratio: float = Form(0.8),
    
    # Face pose
    face_pose_enabled: bool = Form(False),
    pose_max_yaw: float = Form(25.0),
    pose_max_pitch: float = Form(25.0),
    pose_max_roll: float = Form(25.0),
    
    # Image quality
    image_quality_enabled: bool = Form(False),
    blurriness_threshold: int = Form(40),
    grayscale_saturation: int = Form(15),
    underexposure_threshold: int = Form(25),
    overexposure_threshold: int = Form(240),
    low_contrast_threshold: int = Form(20),
    
    # Background
    background_enabled: bool = Form(False),
    background_std_dev_threshold: float = Form(100.0),
    dark_threshold: int = Form(100),
    
    # Object detection
    object_detection_enabled: bool = Form(False),
    min_contour_area_ratio: float = Form(0.03),
    person_scale_factor: float = Form(1.1),
    
    # Accessories
    accessories_enabled: bool = Form(False),
    glasses_detection: bool = Form(False),
    headwear_detection: bool = Form(True),
    hand_detection: bool = Form(True)
):
    """Обновление настроек валидации"""
    try:
        # Получаем текущую конфигурацию
        current_config = config_manager.get_config()
        
        # Обновляем настройки
        updated_config = current_config.model_copy()
        
        # Системные настройки
        updated_config.system.stop_on_failure = stop_on_failure
        updated_config.system.max_check_time = max_check_time
        updated_config.system.processing.max_concurrent = max_concurrent
        
        # Требования к изображению
        updated_config.validation.image_requirements.min_width = min_width
        updated_config.validation.image_requirements.min_height = min_height
        updated_config.validation.image_requirements.max_file_size = int(max_file_size * 1024 * 1024)
        updated_config.validation.image_requirements.allowed_formats = allowed_formats
        
        # Детекция лиц
        updated_config.validation.checks.face_detection.enabled = face_detection_enabled
        updated_config.validation.checks.face_detection.min_count = face_min_count
        updated_config.validation.checks.face_detection.max_count = face_max_count
        updated_config.validation.checks.face_detection.confidence_threshold = face_confidence_threshold
        updated_config.validation.checks.face_detection.min_area_ratio = face_min_area_ratio
        updated_config.validation.checks.face_detection.max_area_ratio = face_max_area_ratio
        
        # Поза лица
        updated_config.validation.checks.face_pose.enabled = face_pose_enabled
        updated_config.validation.checks.face_pose.max_yaw = pose_max_yaw
        updated_config.validation.checks.face_pose.max_pitch = pose_max_pitch
        updated_config.validation.checks.face_pose.max_roll = pose_max_roll
        
        # Качество изображения
        updated_config.validation.checks.image_quality.enabled = image_quality_enabled
        updated_config.validation.checks.image_quality.blurriness_threshold = blurriness_threshold
        updated_config.validation.checks.image_quality.grayscale_saturation = grayscale_saturation
        updated_config.validation.checks.image_quality.lighting.underexposure_threshold = underexposure_threshold
        updated_config.validation.checks.image_quality.lighting.overexposure_threshold = overexposure_threshold
        updated_config.validation.checks.image_quality.lighting.low_contrast_threshold = low_contrast_threshold
        
        # Фон
        updated_config.validation.checks.background.enabled = background_enabled
        updated_config.validation.checks.background.std_dev_threshold = background_std_dev_threshold
        updated_config.validation.checks.background.dark_threshold = dark_threshold
        
        # Детекция объектов
        updated_config.validation.checks.object_detection.enabled = object_detection_enabled
        updated_config.validation.checks.object_detection.min_contour_area_ratio = min_contour_area_ratio
        updated_config.validation.checks.object_detection.person_scale_factor = person_scale_factor
        
        # Аксессуары
        updated_config.validation.checks.accessories.enabled = accessories_enabled
        updated_config.validation.checks.accessories.glasses_detection = glasses_detection
        updated_config.validation.checks.accessories.headwear_detection = headwear_detection
        updated_config.validation.checks.accessories.hand_detection = hand_detection
        
        # Сохраняем конфигурацию
        config_manager.save_config(updated_config)
        
        logger.info("Validation configuration updated successfully")
        
        # Перенаправляем с параметром успеха
        return RedirectResponse(url="/admin/validation?success=1", status_code=303)
        
    except Exception as e:
        logger.error(f"Error updating validation config: {e}")
        return RedirectResponse(url="/admin/validation?error=1", status_code=303)


# =============================================================================
# API ENDPOINTS FOR OPERATIONS MONITORING
# =============================================================================

@admin_app.get("/api/operations/current")
async def get_current_operations():
    """Получить текущие активные операции"""
    try:
        # В реальной реализации здесь будет получение активных задач
        # Пока возвращаем пустой список
        operations = []
        
        # TODO: Интеграция с системой очередей задач
        # operations = await get_active_validation_tasks()
        
        return JSONResponse({
            "operations": operations,
            "count": len(operations)
        })
        
    except Exception as e:
        logger.error(f"Error getting current operations: {e}")
        return JSONResponse({"operations": [], "count": 0})

@admin_app.get("/api/metrics")
async def get_system_metrics(db: Session = Depends(get_db)):
    """Получить системные метрики"""
    try:
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        
        # Статистика валидации
        successful_today = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "APPROVED"
            )
        ).count()
        
        rejected_today = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "REJECTED"
            )
        ).count()
        
        # Среднее время обработки
        avg_time_result = db.query(func.avg(ValidationRequest.processing_time)).filter(
            ValidationRequest.created_at >= day_ago
        ).scalar()
        
        avg_processing_time = float(avg_time_result) if avg_time_result else 0.0
        
        # Системные метрики
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent
        
        # Метрики кэша
        cache_stats = performance_monitor.get_cache_stats()
        cache_hit_rate = cache_stats.get('hit_rate', 0.0) * 100
        
        return JSONResponse({
            "active_operations": 0,  # TODO: Получить из системы очередей
            "successful_today": successful_today,
            "rejected_today": rejected_today,
            "avg_processing_time": avg_processing_time,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "cache_hit_rate": cache_hit_rate,
            "timestamp": now.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        return JSONResponse({
            "active_operations": 0,
            "successful_today": 0,
            "rejected_today": 0,
            "avg_processing_time": 0.0,
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "cache_hit_rate": 0.0,
            "error": str(e)
        })

@admin_app.get("/api/validation/history")
async def get_validation_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    filter: str = Query("all"),
    time_range: str = Query("24h"),
    db: Session = Depends(get_db)
):
    """Получить историю валидации"""
    try:
        # Определяем временной диапазон
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)
        
        # Базовый запрос
        query = db.query(ValidationRequest).filter(
            ValidationRequest.created_at >= start_time
        )
        
        # Фильтрация по статусу
        if filter != "all":
            query = query.filter(ValidationRequest.overall_status == filter)
        
        # Общее количество
        total = query.count()
        
        # Пагинация
        offset = (page - 1) * limit
        items = query.order_by(desc(ValidationRequest.created_at)).offset(offset).limit(limit).all()
        
        # Формируем ответ
        validation_items = []
        for item in items:
            checks_data = item.checks if item.checks else []
            
            validation_items.append({
                "id": item.request_id,
                "filename": getattr(item, 'filename', 'unknown'),
                "status": item.overall_status,
                "created_at": item.created_at.isoformat(),
                "processing_time": item.processing_time,
                "checks_passed": len([c for c in checks_data if c.get('status') == 'PASSED']),
                "total_checks": len(checks_data),
                "image_path": getattr(item, 'image_path', None)
            })
        
        return JSONResponse({
            "items": validation_items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        })
        
    except Exception as e:
        logger.error(f"Error getting validation history: {e}")
        return JSONResponse({
            "items": [],
            "total": 0,
            "page": page,
            "limit": limit,
            "pages": 0,
            "error": str(e)
        })

@admin_app.get("/api/validation/{validation_id}/details")
async def get_validation_details(validation_id: str, db: Session = Depends(get_db)):
    """Получить детали конкретной валидации"""
    try:
        validation = db.query(ValidationRequest).filter(ValidationRequest.request_id == validation_id).first()
        
        if not validation:
            raise HTTPException(status_code=404, detail="Validation not found")
        
        # Парсим результаты проверок
        check_results = validation.checks if validation.checks else []
        
        return JSONResponse({
            "id": validation.request_id,
            "filename": getattr(validation, 'filename', 'unknown'),
            "file_size": getattr(validation, 'file_size', 0),
            "status": validation.overall_status,
            "created_at": validation.created_at.isoformat(),
            "processing_time": validation.processing_time,
            "checks_passed": len([c for c in check_results if c.get('status') == 'PASSED']),
            "total_checks": len(check_results),
            "check_results": check_results,
            "image_path": getattr(validation, 'image_path', None)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting validation details: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@admin_app.get("/api/metrics/processing-time")
async def get_processing_time_metrics(db: Session = Depends(get_db)):
    """Получить метрики времени обработки"""
    try:
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        
        # Получаем данные по часам за последние 24 часа
        results = db.query(
            func.date_trunc('hour', ValidationRequest.created_at).label('hour'),
            func.avg(ValidationRequest.processing_time).label('avg_time')
        ).filter(
            ValidationRequest.created_at >= day_ago
        ).group_by('hour').order_by('hour').all()
        
        labels = []
        values = []
        
        for result in results:
            labels.append(result.hour.strftime('%H:00'))
            values.append(float(result.avg_time) if result.avg_time else 0.0)
        
        return JSONResponse({
            "labels": labels,
            "values": values
        })
        
    except Exception as e:
        logger.error(f"Error getting processing time metrics: {e}")
        return JSONResponse({"labels": [], "values": []})

@admin_app.get("/api/metrics/success-rate")
async def get_success_rate_metrics(db: Session = Depends(get_db)):
    """Получить метрики успешности"""
    try:
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        
        # Подсчитываем по статусам
        approved = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "APPROVED"
            )
        ).count()
        
        rejected = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "REJECTED"
            )
        ).count()
        
        manual_review = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "MANUAL_REVIEW"
            )
        ).count()
        
        return JSONResponse({
            "approved": approved,
            "rejected": rejected,
            "manual_review": manual_review
        })
        
    except Exception as e:
        logger.error(f"Error getting success rate metrics: {e}")
        return JSONResponse({
            "approved": 0,
            "rejected": 0,
            "manual_review": 0
        })

@admin_app.get("/api/reports/export")
async def export_reports(
    filter: str = Query("all"),
    time_range: str = Query("24h"),
    db: Session = Depends(get_db)
):
    """Экспорт отчетов"""
    try:
        # Определяем временной диапазон
        now = datetime.utcnow()
        if time_range == "1h":
            start_time = now - timedelta(hours=1)
        elif time_range == "24h":
            start_time = now - timedelta(days=1)
        elif time_range == "7d":
            start_time = now - timedelta(days=7)
        elif time_range == "30d":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(days=1)
        
        # TODO: Реализовать экспорт в CSV/Excel
        return JSONResponse({
            "message": "Экспорт отчетов будет реализован в следующей версии",
            "filter": filter,
            "time_range": time_range,
            "start_time": start_time.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error exporting reports: {e}")
        raise HTTPException(status_code=500, detail="Error exporting reports")

@admin_app.get("/api/checks/discovery")
async def get_discovered_checks():
    """Получить все автоматически обнаруженные модули проверки"""
    try:
        checks = check_discovery_service.get_all_checks_metadata()
        return JSONResponse({
            "success": True,
            "checks": checks,
            "stats": check_discovery_service.get_discovery_stats()
        })
    except Exception as e:
        logger.error(f"Error getting discovered checks: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/checks/categories")
async def get_checks_by_categories():
    """Получить модули проверки, сгруппированные по категориям"""
    try:
        categories = check_discovery_service.get_checks_by_category()
        return JSONResponse({
            "success": True,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Error getting checks by categories: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/checks/{check_name}/details")
async def get_check_details(check_name: str):
    """Получить детальную информацию о модуле проверки"""
    try:
        details = check_discovery_service.get_check_details(check_name)
        if not details:
            return JSONResponse({
                "success": False,
                "error": "Check not found"
            }, status_code=404)
        
        return JSONResponse({
            "success": True,
            "check": details
        })
    except Exception as e:
        logger.error(f"Error getting check details for {check_name}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/checks/form-config")
async def get_admin_form_config():
    """Получить конфигурацию для автоматического создания форм"""
    try:
        form_config = check_discovery_service.generate_admin_form_config()
        return JSONResponse({
            "success": True,
            "form_config": form_config
        })
    except Exception as e:
        logger.error(f"Error generating form config: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@admin_app.post("/api/checks/{check_name}/validate")
async def validate_check_config(check_name: str, request: Request):
    """Валидировать конфигурацию модуля проверки"""
    try:
        data = await request.json()
        config = data.get("config", {})
        
        validation_result = check_discovery_service.validate_check_configuration(check_name, config)
        
        return JSONResponse({
            "success": True,
            "validation": validation_result
        })
    except Exception as e:
        logger.error(f"Error validating config for {check_name}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@admin_app.get("/checks-discovery", response_class=HTMLResponse)
async def checks_discovery_page(request: Request):
    """Страница управления автоматически обнаруженными модулями"""
    try:
        context = {
            "request": request,
            "title": "Обнаружение модулей",
            "stats": check_discovery_service.get_discovery_stats()
        }
        
        return templates.TemplateResponse("checks_discovery.html", context)
        
    except Exception as e:
        logger.error(f"Error loading checks discovery page: {e}")
        return templates.TemplateResponse("checks_discovery.html", {
            "request": request,
            "title": "Обнаружение модулей",
            "error": str(e)
        }) 