import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import tempfile
import os
from io import BytesIO
from PIL import Image
import cv2
import numpy as np

from app.api.main import app
from app.db.repositories import ValidationRequestRepository
from app.storage.client import storage_client

client = TestClient(app)

@pytest.fixture
def sample_jpeg_image():
    """Создает простое JPEG изображение для тестов"""
    img = Image.new('RGB', (800, 600), color='red')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

@pytest.fixture
def sample_png_image():
    """Создает простое PNG изображение для тестов"""
    img = Image.new('RGB', (800, 600), color='blue')
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

@pytest.fixture
def small_image():
    """Создает маленькое изображение для тестов ограничений"""
    img = Image.new('RGB', (200, 200), color='green')
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes.getvalue()

class TestHealthEndpoints:
    """Тесты для эндпоинтов здоровья системы"""
    
    def test_health_endpoint(self):
        """Тест основного health эндпоинта"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
    
    def test_metrics_endpoint(self):
        """Тест эндпоинта метрик"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "current_memory_usage_mb" in data
    
    def test_detailed_metrics_endpoint(self):
        """Тест детального эндпоинта метрик"""
        response = client.get("/metrics/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "metrics" in data

class TestValidationEndpoints:
    """Тесты для валидации изображений"""
    
    @patch.object(ValidationRequestRepository, 'create')
    @patch.object(storage_client, 'save_file')
    def test_validate_jpeg_success(self, mock_save, mock_create, sample_jpeg_image):
        """Тест успешной валидации JPEG изображения"""
        mock_create.return_value = None
        mock_save.return_value = None
        
        response = client.post(
            "/api/v1/validate",
            files={"file": ("test.jpg", sample_jpeg_image, "image/jpeg")}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "requestId" in data
        assert isinstance(data["requestId"], str)
    
    @patch.object(ValidationRequestRepository, 'create')
    @patch.object(storage_client, 'save_file')
    def test_validate_png_success(self, mock_save, mock_create, sample_png_image):
        """Тест успешной валидации PNG изображения"""
        mock_create.return_value = None
        mock_save.return_value = None
        
        response = client.post(
            "/api/v1/validate",
            files={"file": ("test.png", sample_png_image, "image/png")}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "requestId" in data
    
    def test_validate_small_image_failure(self, small_image):
        """Тест отклонения слишком маленького изображения"""
        response = client.post(
            "/api/v1/validate",
            files={"file": ("small.jpg", small_image, "image/jpeg")}
        )
        
        assert response.status_code == 400
        assert "too small" in response.json()["detail"].lower()
    
    def test_validate_invalid_format(self):
        """Тест отклонения неподдерживаемого формата"""
        fake_content = b"fake file content"
        response = client.post(
            "/api/v1/validate",
            files={"file": ("test.txt", fake_content, "text/plain")}
        )
        
        assert response.status_code == 400
        assert "format" in response.json()["detail"].lower()
    
    def test_validate_no_file(self):
        """Тест запроса без файла"""
        response = client.post("/api/v1/validate")
        assert response.status_code == 422
    
    def test_validate_empty_filename(self, sample_jpeg_image):
        """Test file without filename"""
        response = client.post(
            "/api/v1/validate",
            files={"file": ("", sample_jpeg_image, "image/jpeg")}
        )
        
        assert response.status_code == 422  # FastAPI validation error for empty filename

class TestResultsEndpoints:
    """Тесты для получения результатов валидации"""
    
    @patch.object(ValidationRequestRepository, 'get_by_id')
    def test_get_results_processing(self, mock_get):
        """Test getting result in PROCESSING status"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "request_id": "test-id",
            "status": "PROCESSING",
            "overall_status": None,
            "checks": None,
            "issues": None,
            "processed_at": None,
            "processing_time": None,
            "error_message": None,
            "created_at": "2023-01-01T00:00:00"
        }
        mock_get.return_value = mock_result
        
        response = client.get("/api/v1/results/test-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "PROCESSING"
        assert data["overallStatus"] is None
    
    @patch.object(ValidationRequestRepository, 'get_by_id')
    def test_get_results_completed(self, mock_get):
        """Test getting completed result"""
        mock_result = MagicMock()
        mock_result.to_dict.return_value = {
            "request_id": "test-id",
            "status": "COMPLETED",
            "overall_status": "PASSED",
            "checks": [],
            "issues": [],
            "processed_at": "2023-01-01T00:00:00",
            "processing_time": 1.5,
            "error_message": None,
            "created_at": "2023-01-01T00:00:00"
        }
        mock_get.return_value = mock_result
        
        response = client.get("/api/v1/results/test-id")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["overallStatus"] == "PASSED"
    
    @patch.object(ValidationRequestRepository, 'get_by_id')
    def test_get_results_not_found(self, mock_get):
        """Тест запроса несуществующего результата"""
        mock_get.return_value = None
        
        response = client.get("/api/v1/results/nonexistent-id")
        assert response.status_code == 404 