import pytest
import asyncio
import tempfile
import os
from unittest.mock import patch

# Use SQLite for testing
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="session")
def event_loop():
    """Creates event loop for the entire test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment with SQLite database"""
    with patch.dict(os.environ, {"DATABASE_URL": TEST_DATABASE_URL}):
        yield

@pytest.fixture(autouse=True)
def mock_storage():
    """Мокает хранилище для всех тестов"""
    with patch('app.storage.client.storage_client') as mock:
        mock.save_file.return_value = None
        mock.get_file.return_value = b"fake file content"
        mock.delete_file.return_value = None
        yield mock

@pytest.fixture(autouse=True)
def mock_database():
    """Мокает базу данных для всех тестов"""
    with patch('app.db.repositories.ValidationRequestRepository') as mock:
        mock.create.return_value = None
        mock.update_status.return_value = None
        mock.update_result.return_value = None
        mock.update_error.return_value = None
        yield mock

@pytest.fixture
def temp_dir():
    """Создает временную директорию для тестов"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture(autouse=True)
def cleanup_test_db():
    """Clean up test database after each test"""
    yield
    # Clean up test database file
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except:
            pass 