from typing import Any, Dict, Optional

class PhotoValidationError(Exception):
    """
    Базовый класс для всех исключений сервиса
    """
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)

class FileValidationError(PhotoValidationError):
    """
    Ошибка валидации файла (формат, размер и т.д.)
    """
    def __init__(
        self,
        message: str,
        code: str = "FILE_VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, code=code, details=details)

class StorageError(PhotoValidationError):
    """
    Ошибка при работе с хранилищем файлов
    """
    def __init__(
        self,
        message: str,
        code: str = "STORAGE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, code=code, details=details)

class DatabaseError(PhotoValidationError):
    """
    Ошибка при работе с базой данных
    """
    def __init__(
        self,
        message: str,
        code: str = "DATABASE_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, code=code, details=details)

class CVProcessingError(PhotoValidationError):
    """
    Ошибка при обработке изображения средствами компьютерного зрения
    """
    def __init__(
        self,
        message: str,
        code: str = "CV_PROCESSING_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, code=code, details=details)
