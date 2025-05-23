import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

@pytest.fixture(scope="session")
def event_loop():
    """Creates event loop for the entire test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_client():
    """FastAPI test client"""
    from app.api.main import app
    return TestClient(app)

@pytest.fixture
def test_image_path():
    """Path to test image"""
    return Path(__file__).parent / "photos" / "test_00001.jpeg"

@pytest.fixture
def test_image_data(test_image_path):
    """Binary data of test image"""
    return test_image_path.read_bytes()

@pytest.fixture
def temp_storage_dir():
    """Temporary storage directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def mock_cv2():
    """Mock cv2 for unit tests"""
    mock = MagicMock()
    mock.CascadeClassifier.return_value.detectMultiScale.return_value = []
    return mock

@pytest.fixture
def sample_validation_request():
    """Sample validation request data"""
    return {
        "request_id": "test-123",
        "settings": {
            "face_count_min": 1,
            "face_count_max": 1,
            "min_face_size": 100,
            "blur_threshold": 100,
            "brightness_min": 50,
            "brightness_max": 200
        }
    } 