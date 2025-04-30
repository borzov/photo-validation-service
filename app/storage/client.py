import os
from typing import BinaryIO
from app.core.config import settings
from app.core.exceptions import StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)

class StorageClient:
    """
    Клиент для работы с локальным хранилищем файлов
    """
    def __init__(self):
        # Создаем директорию для хранения файлов
        os.makedirs(settings.STORAGE_PATH, exist_ok=True)
        logger.info(f"Initialized storage client with path: {settings.STORAGE_PATH}")
    
    def save_file(self, file_path: str, content: bytes) -> None:
        """
        Сохраняет файл в хранилище
        """
        try:
            full_path = os.path.join(settings.STORAGE_PATH, file_path)
            with open(full_path, "wb") as f:
                f.write(content)
            logger.info(f"Saved file to storage: {file_path}")
        except Exception as e:
            logger.error(f"Error saving file to storage: {str(e)}")
            raise StorageError(f"Failed to save file: {str(e)}")
    
    def get_file(self, file_path: str) -> bytes:
        """
        Получает файл из хранилища
        """
        try:
            full_path = os.path.join(settings.STORAGE_PATH, file_path)
            with open(full_path, "rb") as f:
                content = f.read()
            logger.info(f"Retrieved file from storage: {file_path}")
            return content
        except Exception as e:
            logger.error(f"Error retrieving file from storage: {str(e)}")
            raise StorageError(f"Failed to retrieve file: {str(e)}")
    
    def delete_file(self, file_path: str) -> None:
        """
        Удаляет файл из хранилища
        """
        try:
            full_path = os.path.join(settings.STORAGE_PATH, file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info(f"Deleted file from storage: {file_path}")
        except Exception as e:
            logger.error(f"Error deleting file from storage: {str(e)}")
            raise StorageError(f"Failed to delete file: {str(e)}")

# Создаем экземпляр клиента для использования в приложении
storage_client = StorageClient()
