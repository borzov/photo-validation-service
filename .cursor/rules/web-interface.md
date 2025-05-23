# Правила веб-интерфейса

## HTML/CSS/JavaScript
- Все пользовательские тексты на русском языке
- Используйте семантичную разметку HTML5
- Применяйте CSS Grid/Flexbox для лейаутов
- Применяйте shadcnuikit вместо bootstrap
- Следуйте принципам доступности (a11y)

## Шаблоны (Jinja2/Django)
```html
<!-- Все комментарии в шаблонах на русском -->
<!-- Форма загрузки изображения -->
<form id="upload-form" enctype="multipart/form-data">
    <label for="image-file">Выберите изображение для обработки:</label>
    <input type="file" id="image-file" name="file" accept="image/*" required>
    
    <!-- Параметры обработки -->
    <fieldset>
        <legend>Параметры обработки</legend>
        <!-- ... -->
    </fieldset>
</form>
```

## JavaScript/TypeScript
```javascript
/**
 * Загружает изображение на сервер для обработки
 * @param {File} file - Файл изображения
 * @param {Object} options - Параметры обработки
 * @returns {Promise<Object>} Результат обработки
 */
async function uploadImage(file, options) {
    // Проверяем размер файла перед загрузкой
    if (file.size > MAX_FILE_SIZE) {
        throw new Error('Размер файла превышает допустимый лимит');
    }
    
    // Отправляем запрос на сервер
    const response = await fetch('/api/v1/images/process', {
        method: 'POST',
        body: formData
    });
    
    return response.json();
}
```

## Локализация
- Все пользовательские сообщения на русском
- Используйте i18n для многоязычности если планируется
- Форматируйте даты и числа согласно русской локали

## Сообщения пользователю
```python
ERROR_MESSAGES = {
    'file_too_large': 'Размер файла не должен превышать 50 МБ',
    'invalid_format': 'Поддерживаются только изображения в форматах JPEG, PNG, WEBP',
    'processing_failed': 'Произошла ошибка при обработке изображения',
    'upload_success': 'Изображение успешно обработано'
}
```
