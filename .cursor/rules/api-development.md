# Правила разработки API

## FastAPI/Flask стандарты
- Используйте Pydantic модели для валидации данных
- Все описания эндпоинтов на русском языке
- Структурируйте API по версиям (/api/v1/)

## Документация эндпоинтов
```python
@app.post("/api/v1/images/process", response_model=ImageProcessResponse)
async def process_image_endpoint(
    file: UploadFile = File(...),
    options: ProcessingOptions = Body(...)
) -> ImageProcessResponse:
    """Обрабатывает загруженное изображение.
    
    Принимает файл изображения и параметры обработки, выполняет обработку
    и возвращает результат с метаданными.
    
    Args:
        file: Загружаемый файл изображения (JPEG, PNG, WEBP)
        options: Параметры обработки изображения
        
    Returns:
        Результат обработки с путем к файлу и метаданными
        
    Raises:
        HTTPException: 400 - Неверный формат файла
        HTTPException: 413 - Файл слишком большой
        HTTPException: 500 - Ошибка обработки
    """
```

## Модели данных
```python
class ImageProcessResponse(BaseModel):
    """Ответ сервера после обработки изображения."""
    
    success: bool = Field(..., description="Успешность обработки")
    message: str = Field(..., description="Сообщение о результате")
    output_url: Optional[str] = Field(None, description="URL обработанного изображения")
    metadata: ImageMetadata = Field(..., description="Метаданные изображения")
    processing_time: float = Field(..., description="Время обработки в секундах")
```

## Обработка ошибок
- Используйте HTTPException с понятными сообщениями на русском
- Логируйте все ошибки с контекстом
- Возвращайте структурированные ошибки

```python
if not file.content_type.startswith('image/'):
    raise HTTPException(
        status_code=400,
        detail="Загруженный файл должен быть изображением"
    )
```