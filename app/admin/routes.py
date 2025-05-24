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
        try:
            config = config_manager.get_config()
        except Exception as config_error:
            logger.warning(f"Config error: {config_error}")
            # Создаем полную заглушку конфигурации
            from datetime import datetime
            
            class MockConfig:
                def __init__(self):
                    self.last_modified = datetime.now()
                    self.version = "2.1"
                    
                    # System configuration
                    class MockSystem:
                        def __init__(self):
                            class MockProcessing:
                                max_concurrent = 5
                            self.processing = MockProcessing()
                            self.max_check_time = 5.0
                            self.stop_on_failure = False
                    
                    # Validation configuration  
                    class MockValidation:
                        def __init__(self):
                            # Image requirements
                            class MockImageReq:
                                max_file_size = 5 * 1024 * 1024
                                allowed_formats = ["jpg", "jpeg", "png"]
                            self.image_requirements = MockImageReq()
                            
                            # Checks configuration
                            class MockChecks:
                                def __init__(self):
                                    # Face detection
                                    class MockFaceDetection:
                                        enabled = True
                                        min_count = 1
                                        max_count = 1
                                        face_confidence_threshold = 0.4
                                        confidence_threshold = 0.4
                                    self.face_detection = MockFaceDetection()
                                    
                                    # Face pose
                                    class MockFacePose:
                                        enabled = True
                                        max_yaw = 25.0
                                    self.face_pose = MockFacePose()
                                    
                                    # Image quality (unified)
                                    class MockImageQuality:
                                        enabled = True
                                        blurriness_threshold = 40
                                    self.image_quality = MockImageQuality()
                                    
                                    # Background
                                    class MockBackground:
                                        enabled = True
                                    self.background = MockBackground()
                                    
                                    # Object detection
                                    class MockObjectDetection:
                                        enabled = True
                                    self.object_detection = MockObjectDetection()
                                    
                                    # Accessories
                                    class MockAccessories:
                                        enabled = True
                                        glasses_detection_enabled = False
                                        headwear_detection_enabled = True
                                        hand_detection_enabled = True
                                        glasses_detection = False
                                        headwear_detection = True
                                        hand_detection = True
                                    self.accessories = MockAccessories()
                            
                            self.checks = MockChecks()
                    
                    self.system = MockSystem()
                    self.validation = MockValidation()
            
            config = MockConfig()
        
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
        # Создаем fallback конфигурацию для ошибки
        from datetime import datetime
        
        class MockConfig:
            def __init__(self):
                self.last_modified = datetime.now()
                self.version = "2.1"
                
                class MockSystem:
                    def __init__(self):
                        class MockProcessing:
                            max_concurrent = 5
                        self.processing = MockProcessing()
                        self.max_check_time = 5.0
                        self.stop_on_failure = False
                
                class MockValidation:
                    def __init__(self):
                        class MockImageReq:
                            max_file_size = 5 * 1024 * 1024
                            allowed_formats = ["jpg", "jpeg"]
                        self.image_requirements = MockImageReq()
                        
                        class MockChecks:
                            def __init__(self):
                                class MockCheck:
                                    enabled = False
                                    min_count = 1
                                    max_count = 1
                                    max_yaw = 25.0
                                    blurriness_threshold = 40
                                    glasses_detection = False
                                    headwear_detection = False
                                    hand_detection = False
                                
                                self.face_detection = MockCheck()
                                self.face_pose = MockCheck()
                                self.image_quality = MockCheck()
                                self.background = MockCheck()
                                self.object_detection = MockCheck()
                                self.accessories = MockCheck()
                        
                        self.checks = MockChecks()
                
                self.system = MockSystem()
                self.validation = MockValidation()
        
        fallback_config = MockConfig()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "title": "Дашборд",
            "config": fallback_config,
            "error": "Ошибка загрузки дашборда",
            "system_info": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "disk_usage": psutil.disk_usage('/').percent
            }
        })

@admin_app.get("/system", response_class=HTMLResponse)
async def system_config(request: Request):
    """Страница системных настроек"""
    try:
        try:
            config = config_manager.get_config()
        except Exception as config_error:
            logger.warning(f"Config error in system page: {config_error}")
            # Создаем заглушку для системных настроек
            from datetime import datetime
            
            class MockConfig:
                def __init__(self):
                    self.last_modified = datetime.now()
                    self.version = "2.1"
                    
                    class MockSystem:
                        def __init__(self):
                            class MockProcessing:
                                max_concurrent = 5
                            self.processing = MockProcessing()
                            self.max_check_time = 5.0
                            self.stop_on_failure = False
                            
                            class MockStorage:
                                max_file_size_mb = 5.0
                                allowed_formats = ["jpg", "jpeg", "png"]
                                storage_path = "./local_storage"
                                max_pixels = 50000000
                            self.storage = MockStorage()
                            
                            self.log_level = "INFO"
                    
                    class MockValidation:
                        def __init__(self):
                            class MockImageReq:
                                max_file_size = 5 * 1024 * 1024
                                allowed_formats = ["jpg", "jpeg", "png"]
                                min_width = 400
                                min_height = 500
                            self.image_requirements = MockImageReq()
                    
                    self.system = MockSystem()
                    self.validation = MockValidation()
            
            config = MockConfig()
        
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
            "title": "Системные настройки",
            "error": "Ошибка загрузки системных настроек"
        })

@admin_app.get("/validation", response_class=HTMLResponse)
async def validation_config(request: Request):
    """Страница настроек валидации"""
    try:
        try:
            config = config_manager.get_config()
        except Exception as config_error:
            logger.warning(f"Config error in validation page: {config_error}")
            # Создаем заглушку для настроек валидации
            from datetime import datetime
            
            class MockConfig:
                def __init__(self):
                    self.last_modified = datetime.now()
                    self.version = "2.1"
                    
                    class MockSystem:
                        def __init__(self):
                            class MockProcessing:
                                max_concurrent = 5
                            self.processing = MockProcessing()
                            self.max_check_time = 5.0
                            self.stop_on_failure = False
                    
                    class MockValidation:
                        def __init__(self):
                            class MockImageReq:
                                max_file_size = 5 * 1024 * 1024
                                allowed_formats = ["jpg", "jpeg", "png"]
                                min_width = 400
                                min_height = 500
                            self.image_requirements = MockImageReq()
                            
                            class MockChecks:
                                def __init__(self):
                                    # Создаем все необходимые check классы
                                    class MockFaceDetection:
                                        enabled = True
                                        min_count = 1
                                        max_count = 1
                                        confidence_threshold = 0.4
                                        min_area_ratio = 0.05
                                        max_area_ratio = 0.8
                                    self.face_detection = MockFaceDetection()
                                    
                                    class MockFacePose:
                                        enabled = True
                                        max_yaw = 25.0
                                        max_pitch = 25.0
                                        max_roll = 25.0
                                    self.face_pose = MockFacePose()
                                    
                                    class MockFacePosition:
                                        enabled = True
                                        face_min_area_ratio = 0.05
                                        face_max_area_ratio = 0.8
                                        face_center_tolerance = 0.4
                                        min_width_ratio = 0.15
                                        min_height_ratio = 0.2
                                        min_margin_ratio = 0.03
                                        boundary_tolerance = 5
                                    self.face_position = MockFacePosition()
                                    
                                    class MockImageQuality:
                                        enabled = True
                                        blurriness_threshold = 40
                                        grayscale_saturation = 15
                                        class MockLighting:
                                            underexposure_threshold = 25
                                            overexposure_threshold = 240
                                            low_contrast_threshold = 20
                                        lighting = MockLighting()
                                    self.image_quality = MockImageQuality()
                                    
                                    class MockBackground:
                                        enabled = True
                                        std_dev_threshold = 100.0
                                        dark_threshold = 100
                                    self.background = MockBackground()
                                    
                                    class MockObjectDetection:
                                        enabled = True
                                        min_contour_area_ratio = 0.03
                                        person_scale_factor = 1.1
                                    self.object_detection = MockObjectDetection()
                                    
                                    class MockAccessories:
                                        enabled = True
                                        glasses_detection = False
                                        headwear_detection = True
                                        hand_detection = True
                                    self.accessories = MockAccessories()
                            
                            self.checks = MockChecks()
                    
                    self.system = MockSystem()
                    self.validation = MockValidation()
            
            config = MockConfig()
        
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
            "title": "Настройки валидации",
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
        hour_ago = now - timedelta(hours=1)
        
        # Общая статистика
        total_validations = db.query(ValidationRequest).count()
        
        # Статистика по статусам
        manual_review_count = db.query(ValidationRequest).filter(
            ValidationRequest.overall_status == "MANUAL_REVIEW"
        ).count()
        
        approved_total = db.query(ValidationRequest).filter(
            ValidationRequest.overall_status == "APPROVED"
        ).count()
        
        rejected_total = db.query(ValidationRequest).filter(
            ValidationRequest.overall_status == "REJECTED"
        ).count()
        
        # Статистика за сегодня
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
        
        # Статистика за последние 24 часа (все статусы)
        total_24h = db.query(ValidationRequest).filter(
            ValidationRequest.created_at >= day_ago
        ).count()
        
        # Статистика за последний час
        total_1h = db.query(ValidationRequest).filter(
            ValidationRequest.created_at >= hour_ago
        ).count()
        
        # Процент успешности (за всё время)
        approval_rate = 0.0
        if total_validations > 0:
            approval_rate = (approved_total / total_validations) * 100
        
        # Среднее время обработки
        avg_time_result = db.query(func.avg(ValidationRequest.processing_time)).filter(
            ValidationRequest.created_at >= day_ago
        ).scalar()
        avg_processing_time = float(avg_time_result) if avg_time_result else 0.0
        
        # Средний размер файла
        avg_size_result = db.query(func.avg(ValidationRequest.file_size)).filter(
            ValidationRequest.file_size.isnot(None)
        ).scalar()
        avg_file_size_mb = 0.0
        if avg_size_result:
            avg_file_size_mb = float(avg_size_result) / (1024 * 1024)  # Convert to MB
        
        # Топ причины отклонения (за последние 24 часа)
        rejection_reasons = {}
        rejected_validations = db.query(ValidationRequest).filter(
            and_(
                ValidationRequest.created_at >= day_ago,
                ValidationRequest.overall_status == "REJECTED"
            )
        ).all()
        
        for validation in rejected_validations:
            if validation.checks:
                for check in validation.checks:
                    if check.get('status') == 'FAILED' and check.get('reason'):
                        reason = check.get('reason', 'Unknown')
                        rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        # Топ 3 причины отклонения
        top_rejection_reasons = sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Системные метрики
        cpu_usage = psutil.cpu_percent(interval=0.1)
        memory_usage = psutil.virtual_memory().percent
        
        # Метрики кэша
        cache_stats = performance_monitor.get_cache_stats()
        cache_hit_rate = cache_stats.get('hit_rate', 0.0) * 100
        
        return JSONResponse({
            # Основные метрики
            "active_operations": 0,  # TODO: implement queue monitoring
            "successful_today": successful_today,
            "rejected_today": rejected_today,
            "avg_processing_time": avg_processing_time,
            
            # Новые расширенные метрики
            "total_validations": total_validations,
            "manual_review_count": manual_review_count,
            "total_24h": total_24h,
            "total_1h": total_1h,
            "approved_total": approved_total,
            "rejected_total": rejected_total,
            "approval_rate": round(approval_rate, 1),
            "avg_file_size_mb": round(avg_file_size_mb, 2),
            "top_rejection_reasons": top_rejection_reasons,
            
            # Системные метрики
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
            "total_validations": 0,
            "manual_review_count": 0,
            "total_24h": 0,
            "total_1h": 0,
            "approved_total": 0,
            "rejected_total": 0,
            "approval_rate": 0.0,
            "avg_file_size_mb": 0.0,
            "top_rejection_reasons": [],
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

@admin_app.post("/api/checks/discovery/refresh")
async def refresh_checks_discovery():
    """Принудительно обновить discovery модулей проверки"""
    try:
        from app.cv.checks.registry import check_registry
        
        # Сбрасываем кэш и принудительно переобнаруживаем
        check_registry.reset()
        check_registry.discover_checks()
        
        # Обновляем сервис discovery
        check_discovery_service._ensure_discovery()
        
        checks = check_discovery_service.get_all_checks_metadata()
        return JSONResponse({
            "success": True,
            "message": "Discovery cache refreshed successfully",
            "checks_count": len(checks),
            "checks": checks,
            "stats": check_discovery_service.get_discovery_stats()
        })
    except Exception as e:
        logger.error(f"Error refreshing discovery: {e}")
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

# ===== ДОПОЛНИТЕЛЬНЫЕ API ENDPOINTS =====

@admin_app.post("/api/checks/{check_name}/test")
async def test_check_module(check_name: str, request: Request):
    """Тестирование модуля проверки"""
    try:
        from app.cv.checks.registry import check_registry
        import numpy as np
        import cv2
        
        data = await request.json()
        config = data.get("config", {})
        
        # Получаем класс модуля
        check_class = check_registry.get_check(check_name)
        if not check_class:
            return JSONResponse({
                "success": False,
                "error": f"Модуль {check_name} не найден"
            }, status_code=404)
        
        # Создаем тестовое изображение (белый квадрат 500x500)
        test_image = np.ones((500, 500, 3), dtype=np.uint8) * 255
        
        # Создаем экземпляр модуля с переданной конфигурацией
        check_instance = check_class(**config)
        
        # Запускаем тест
        test_context = {}
        if check_name in ['face_pose', 'face_position', 'accessories', 'red_eye']:
            # Для модулей, требующих face context, создаем фиктивные данные
            test_context = {
                "face": {
                    "bbox": [100, 100, 300, 300],
                    "landmarks": [[200, 150] for _ in range(68)]  # 68 точек для dlib
                }
            }
        
        result = check_instance.check(test_image, test_context)
        
        return JSONResponse({
            "success": True,
            "result": result,
            "message": f"Модуль {check_name} протестирован успешно"
        })
        
    except Exception as e:
        logger.error(f"Error testing check module {check_name}: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/system/health")
async def get_system_health():
    """Получить состояние системы"""
    try:
        import psutil
        import time
        
        # Системные метрики
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Время работы системы
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time
        
        # Количество процессов
        process_count = len(psutil.pids())
        
        # Загрузка системы
        try:
            load_avg = psutil.getloadavg()
        except AttributeError:
            # На Windows getloadavg не доступен
            load_avg = [0, 0, 0]
        
        return JSONResponse({
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "load_avg": load_avg
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            },
            "disk": {
                "total": disk.total,
                "free": disk.free,
                "used": disk.used,
                "percent": disk.percent
            },
            "system": {
                "uptime": uptime,
                "process_count": process_count,
                "timestamp": time.time()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/config/backup")
async def backup_configuration():
    """Создать резервную копию конфигурации"""
    try:
        import tempfile
        import json
        from datetime import datetime
        
        config = config_manager.get_config()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config.model_dump(), f, indent=2, default=str)
            temp_path = f.name
        
        return FileResponse(
            temp_path,
            filename=f"config_backup_{timestamp}.json",
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error(f"Error creating config backup: {e}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@admin_app.post("/api/config/restore")
async def restore_configuration(request: Request):
    """Восстановить конфигурацию из резервной копии"""
    try:
        form = await request.form()
        backup_file = form.get("backup_file")
        
        if not backup_file:
            return JSONResponse({
                "error": "Файл резервной копии не предоставлен"
            }, status_code=400)
        
        # Читаем и валидируем конфигурацию
        content = await backup_file.read()
        config_data = json.loads(content)
        
        # Создаем объект конфигурации
        restored_config = ConfigurationSchema(**config_data)
        
        # Сохраняем конфигурацию
        config_manager.save_config(restored_config)
        
        logger.info("Configuration restored from backup successfully")
        
        return JSONResponse({
            "success": True,
            "message": "Конфигурация успешно восстановлена"
        })
        
    except Exception as e:
        logger.error(f"Error restoring configuration: {e}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/logs/recent")
async def get_recent_logs(
    lines: int = Query(100, ge=10, le=1000),
    level: str = Query("INFO")
):
    """Получить последние записи логов"""
    try:
        import os
        
        # Путь к лог файлу (предполагаем стандартное расположение)
        log_file = "/app/logs/app.log"
        
        if not os.path.exists(log_file):
            return JSONResponse({
                "logs": [],
                "message": "Лог файл не найден"
            })
        
        # Читаем последние строки
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        # Фильтруем по уровню логирования если задан
        if level != "ALL":
            filtered_lines = [line for line in recent_lines if level in line]
        else:
            filtered_lines = recent_lines
        
        return JSONResponse({
            "logs": filtered_lines,
            "total_lines": len(filtered_lines),
            "file_size": os.path.getsize(log_file)
        })
        
    except Exception as e:
        logger.error(f"Error getting recent logs: {e}")
        return JSONResponse({
            "logs": [],
            "error": str(e)
        })

@admin_app.post("/api/cache/clear")
async def clear_application_cache():
    """Очистить кэш приложения"""
    try:
        # Очищаем кэш performance monitor
        performance_monitor.clear_cache()
        
        # Очищаем кэш registry модулей
        from app.cv.checks.registry import check_registry
        check_registry.reset()
        
        logger.info("Application cache cleared successfully")
        
        return JSONResponse({
            "success": True,
            "message": "Кэш приложения очищен"
        })
        
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/database/stats")
async def get_database_stats(db: Session = Depends(get_db)):
    """Получить статистику базы данных"""
    try:
        from sqlalchemy import text
        
        # Общее количество записей валидации
        total_validations = db.query(ValidationRequest).count()
        
        # Статистика по статусам
        status_stats = db.query(
            ValidationRequest.overall_status,
            func.count(ValidationRequest.overall_status)
        ).group_by(ValidationRequest.overall_status).all()
        
        # Размер базы данных (для PostgreSQL)
        try:
            db_size_result = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()))")).scalar()
            db_size = db_size_result
        except:
            db_size = "N/A"
        
        # Статистика за последние 30 дней
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_validations = db.query(ValidationRequest).filter(
            ValidationRequest.created_at >= thirty_days_ago
        ).count()
        
        return JSONResponse({
            "total_validations": total_validations,
            "recent_validations": recent_validations,
            "status_distribution": {status: count for status, count in status_stats},
            "database_size": db_size,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@admin_app.post("/api/maintenance/cleanup")
async def run_maintenance_cleanup(db: Session = Depends(get_db)):
    """Запустить очистку базы данных"""
    try:
        # Удаляем записи старше 90 дней
        cleanup_date = datetime.utcnow() - timedelta(days=90)
        
        deleted_count = db.query(ValidationRequest).filter(
            ValidationRequest.created_at < cleanup_date
        ).count()
        
        # В production здесь было бы удаление
        # db.query(ValidationRequest).filter(
        #     ValidationRequest.created_at < cleanup_date
        # ).delete()
        # db.commit()
        
        logger.info(f"Maintenance cleanup completed, {deleted_count} records would be deleted")
        
        return JSONResponse({
            "success": True,
            "message": f"Очистка завершена. Удалено записей: {deleted_count} (в режиме симуляции)"
        })
        
    except Exception as e:
        logger.error(f"Error during maintenance cleanup: {e}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)

@admin_app.get("/api/checks/performance")
async def get_checks_performance():
    """Получить статистику производительности модулей проверки"""
    try:
        # Получаем статистику из performance monitor
        stats = performance_monitor.get_performance_stats()
        
        # Группируем по модулям проверки
        check_stats = {}
        for check_name, check_data in stats.items():
            if check_name.startswith('check_'):
                module_name = check_name.replace('check_', '')
                check_stats[module_name] = {
                    "avg_time": check_data.get("avg_time", 0),
                    "total_calls": check_data.get("total_calls", 0),
                    "error_rate": check_data.get("error_rate", 0),
                    "last_execution": check_data.get("last_execution")
                }
        
        return JSONResponse({
            "checks_performance": check_stats,
            "global_stats": {
                "cache_hits": stats.get("cache_hits", 0),
                "cache_misses": stats.get("cache_misses", 0),
                "total_requests": stats.get("total_requests", 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting checks performance: {e}")
        return JSONResponse({
            "error": str(e)
        }, status_code=500)



@admin_app.post("/system", response_class=HTMLResponse)
async def update_system_config(request: Request):
    """Обновление системных настроек"""
    try:
        form_data = await request.form()
        
        # Преобразуем данные формы в структуру конфигурации
        updates = {
            "system": {
                "processing": {
                    "max_concurrent": int(form_data.get("max_concurrent", 5)),
                    "max_check_time": float(form_data.get("max_check_time", 5.0)),
                    "stop_on_failure": bool(form_data.get("stop_on_failure"))
                },
                "storage": {
                    "max_file_size_mb": float(form_data.get("max_file_size_mb", 5.0)),
                    "allowed_formats": form_data.get("allowed_formats", "jpg,jpeg,png").split(","),
                    "storage_path": form_data.get("storage_path", "./local_storage"),
                    "max_pixels": int(form_data.get("max_pixels", 50000000))
                },
                "log_level": form_data.get("log_level", "INFO")
            }
        }
        
        # Применяем изменения
        config_manager.update_config(updates)
        
        return RedirectResponse(url="/admin/system?success=1", status_code=303)
        
    except Exception as e:
        logger.error(f"Error updating system config: {e}")
        return RedirectResponse(url="/admin/system?error=" + str(e), status_code=303)

@admin_app.post("/system/test")
async def test_system_config(request: Request):
    """Тестирование системной конфигурации"""
    try:
        form_data = await request.form()
        
        # Собираем конфигурацию из формы
        test_config = {
            "max_concurrent": int(form_data.get("max_concurrent", 5)),
            "max_check_time": float(form_data.get("max_check_time", 5.0)),
            "stop_on_failure": bool(form_data.get("stop_on_failure")),
            "max_file_size_mb": float(form_data.get("max_file_size_mb", 5.0)),
            "log_level": form_data.get("log_level", "INFO")
        }
        
        # Валидируем конфигурацию
        validation_errors = []
        
        # Проверяем диапазоны значений
        if test_config["max_concurrent"] < 1 or test_config["max_concurrent"] > 50:
            validation_errors.append("Максимальные параллельные задачи должны быть от 1 до 50")
            
        if test_config["max_check_time"] < 1.0 or test_config["max_check_time"] > 60.0:
            validation_errors.append("Максимальное время проверки должно быть от 1.0 до 60.0 секунд")
            
        if test_config["max_file_size_mb"] < 0.1 or test_config["max_file_size_mb"] > 100.0:
            validation_errors.append("Максимальный размер файла должен быть от 0.1 до 100.0 МБ")
            
        if test_config["log_level"] not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            validation_errors.append("Уровень логирования должен быть одним из: DEBUG, INFO, WARNING, ERROR")
        
        # Тестируем системные ресурсы
        try:
            import psutil
            import time
            
            # Проверяем доступность системных ресурсов
            cpu_count = psutil.cpu_count()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            # Проверяем, что настройки не превышают возможности системы
            if test_config["max_concurrent"] > cpu_count * 2:
                validation_errors.append(f"Максимальные параллельные задачи ({test_config['max_concurrent']}) превышают рекомендуемое значение для {cpu_count} CPU")
            
            # Проверяем доступную память (приблизительно 100MB на задачу)
            required_memory_mb = test_config["max_concurrent"] * 100
            available_memory_mb = memory.available / (1024 * 1024)
            
            if required_memory_mb > available_memory_mb:
                validation_errors.append(f"Недостаточно свободной памяти для {test_config['max_concurrent']} параллельных задач")
            
            # Проверяем доступное место на диске
            free_disk_gb = disk.free / (1024 * 1024 * 1024)
            if free_disk_gb < 1.0:
                validation_errors.append("Недостаточно свободного места на диске (менее 1 ГБ)")
                
        except Exception as resource_error:
            logger.warning(f"Could not check system resources: {resource_error}")
        
        if validation_errors:
            return JSONResponse({
                "success": False,
                "error": "Найдены ошибки в конфигурации",
                "validation_errors": validation_errors
            }, status_code=400)
        
        # Если все проверки прошли успешно
        return JSONResponse({
            "success": True,
            "message": "Конфигурация валидна и готова к применению",
            "tested_config": test_config,
            "system_info": {
                "cpu_cores": psutil.cpu_count() if 'psutil' in locals() else "N/A",
                "memory_gb": round(psutil.virtual_memory().total / (1024**3), 2) if 'psutil' in locals() else "N/A",
                "disk_free_gb": round(psutil.disk_usage('.').free / (1024**3), 2) if 'psutil' in locals() else "N/A"
            }
        })
        
    except ValueError as ve:
        return JSONResponse({
            "success": False,
            "error": f"Ошибка валидации значений: {str(ve)}"
        }, status_code=400)
    except Exception as e:
        logger.error(f"Error testing system config: {e}")
        return JSONResponse({
            "success": False,
            "error": f"Ошибка тестирования конфигурации: {str(e)}"
        }, status_code=500)

@admin_app.post("/system/reset")
async def reset_system_config(request: Request):
    """Сброс системных настроек к значениям по умолчанию"""
    try:
        # Значения по умолчанию
        default_config = {
            "system": {
                "processing": {
                    "max_concurrent": 5,
                    "max_check_time": 5.0,
                    "stop_on_failure": False,
                    "parallel_checks": True
                },
                "storage": {
                    "max_file_size_mb": 5.0,
                    "allowed_formats": ["jpg", "jpeg", "png", "webp", "bmp", "tiff"],
                    "storage_path": "./local_storage",
                    "max_pixels": 50000000
                },
                "log_level": "INFO"
            }
        }
        
        config_manager.update_config(default_config)
        
        return JSONResponse({
            "success": True,
            "message": "Системные настройки сброшены к значениям по умолчанию"
        })
        
    except Exception as e:
        logger.error(f"Error resetting system config: {e}")
        return JSONResponse({
            "success": False,
            "error": f"Ошибка сброса настроек: {str(e)}"
        }, status_code=500) 