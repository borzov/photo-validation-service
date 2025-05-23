// JavaScript для страницы настроек валидации

// Глобальные переменные
let currentConfig = null;
let checkModules = [];
let allChecksMetadata = {};

// Инициализация страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, starting validation config load...');
    loadValidationConfig();
});

// Загрузка конфигурации валидации
async function loadValidationConfig() {
    try {
        console.log('Starting config load...');
        showLoading(true);
        
        // Загружаем текущую конфигурацию
        console.log('Fetching config from /api/v1/config/...');
        const configResponse = await fetch('/api/v1/config/');
        console.log('Config response status:', configResponse.status);
        
        if (!configResponse.ok) {
            throw new Error(`HTTP ${configResponse.status}: Не удалось загрузить конфигурацию`);
        }
        
        currentConfig = await configResponse.json();
        console.log('Config loaded:', currentConfig);
        
        // Загружаем метаданные всех модулей проверки
        await loadChecksMetadata();
        
        // Создаем форму с настройками
        generateValidationForm();
        
        // Скрываем индикатор загрузки и показываем форму
        showLoading(false);
        
    } catch (error) {
        console.error('Ошибка загрузки:', error);
        showError('Ошибка загрузки конфигурации: ' + error.message);
        showLoading(false);
    }
}

// Загрузка метаданных модулей проверки
async function loadChecksMetadata() {
    try {
        console.log('Loading checks metadata...');
        const response = await fetch('/admin/api/checks/discovery');
        
        if (!response.ok) {
            throw new Error('Failed to load checks metadata');
        }
        
        const data = await response.json();
        allChecksMetadata = data.checks || {};
        console.log('Checks metadata loaded:', allChecksMetadata);
        
    } catch (error) {
        console.error('Error loading checks metadata:', error);
        // Fallback: используем базовую структуру
        allChecksMetadata = {};
    }
}

// Показать/скрыть индикатор загрузки
function showLoading(show) {
    console.log('showLoading called with:', show);
    const loader = document.getElementById('loading-indicator');
    const container = document.getElementById('validation-form-container');
    
    console.log('Loader element:', loader);
    console.log('Container element:', container);
    
    if (loader) {
        loader.style.display = show ? 'block' : 'none';
        console.log('Loader display set to:', loader.style.display);
    }
    if (container) {
        container.style.display = show ? 'none' : 'block';
        console.log('Container display set to:', container.style.display);
    }
}

// Показать ошибку
function showError(message) {
    console.log('showError called with:', message);
    const container = document.getElementById('loading-indicator');
    if (container) {
        container.innerHTML = `
            <div class="text-center py-8">
                <div class="text-red-600 mb-4">
                    <i data-lucide="alert-circle" class="h-12 w-12 mx-auto mb-2"></i>
                    <p class="text-lg font-medium">Ошибка загрузки</p>
                    <p class="text-sm">${message}</p>
                </div>
                <button onclick="location.reload()" class="btn-primary">
                    <i data-lucide="refresh-cw" class="h-4 w-4 mr-2"></i>
                    Попробовать снова
                </button>
            </div>
        `;
        // Обновить иконки
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

// Генерация формы валидации
function generateValidationForm() {
    console.log('generateValidationForm called');
    if (!currentConfig) {
        console.error('No currentConfig available');
        return;
    }
    
    const form = document.getElementById('validationForm');
    if (!form) {
        console.error('No validationForm element found');
        return;
    }
    
    console.log('Form found, filling global settings...');
    
    // Заполняем глобальные настройки
    fillGlobalSettings();
    
    // Генерируем секции для модулей проверки
    generateModuleSections();
    
    // Добавляем обработчики событий
    setupFormHandlers();
    
    // Обновляем иконки
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    console.log('Form generation completed');
}

// Заполнение глобальных настроек
function fillGlobalSettings() {
    console.log('fillGlobalSettings called');
    const config = currentConfig;
    
    // Системные настройки
    const stopOnFailure = document.getElementById('stop_on_failure');
    if (stopOnFailure && config.system) {
        stopOnFailure.checked = config.system.stop_on_failure || false;
        console.log('Set stop_on_failure to:', stopOnFailure.checked);
    }
    
    const maxCheckTime = document.getElementById('max_check_time');
    if (maxCheckTime && config.system) {
        maxCheckTime.value = config.system.max_check_time || 5.0;
        console.log('Set max_check_time to:', maxCheckTime.value);
    }
    
    const maxConcurrent = document.getElementById('max_concurrent');
    if (maxConcurrent && config.system && config.system.processing) {
        maxConcurrent.value = config.system.processing.max_concurrent || 5;
        console.log('Set max_concurrent to:', maxConcurrent.value);
    }
    
    // Требования к изображению
    const minWidth = document.getElementById('min_width');
    if (minWidth && config.validation && config.validation.image_requirements) {
        minWidth.value = config.validation.image_requirements.min_width || 400;
    }
    
    const minHeight = document.getElementById('min_height');
    if (minHeight && config.validation && config.validation.image_requirements) {
        minHeight.value = config.validation.image_requirements.min_height || 500;
    }
    
    const maxFileSize = document.getElementById('max_file_size');
    if (maxFileSize && config.system && config.system.storage) {
        maxFileSize.value = config.system.storage.max_file_size_mb || 1.0;
    }
}

// Генерация секций модулей
function generateModuleSections() {
    console.log('generateModuleSections called');
    const container = document.getElementById('modules-container');
    if (!container) {
        console.error('No modules-container found');
        return;
    }
    
    container.innerHTML = '';
    
    // Создаем секции для всех доступных модулей
    const availableChecks = getAvailableChecks();
    console.log('Available checks for generation:', availableChecks);
    
    // Группируем по категориям
    const categories = groupChecksByCategory(availableChecks);
    
    // Создаем секцию для каждой категории
    Object.keys(categories).forEach(category => {
        const categorySection = createCategorySection(category, categories[category]);
        container.appendChild(categorySection);
    });
    
    console.log('Module sections generation completed');
}

// Получение списка доступных проверок
function getAvailableChecks() {
    const checks = [];
    
    // Из текущей конфигурации
    if (currentConfig.validation && currentConfig.validation.checks) {
        Object.keys(currentConfig.validation.checks).forEach(checkName => {
            checks.push({
                name: checkName,
                config: currentConfig.validation.checks[checkName],
                metadata: allChecksMetadata[checkName] || null
            });
        });
    }
    
    // Добавляем модули из метаданных, которых нет в конфигурации
    Object.keys(allChecksMetadata).forEach(checkName => {
        if (!checks.find(c => c.name === checkName)) {
            checks.push({
                name: checkName,
                config: { enabled: false },
                metadata: allChecksMetadata[checkName]
            });
        }
    });
    
    return checks;
}

// Группировка проверок по категориям
function groupChecksByCategory(checks) {
    const categories = {};
    
    checks.forEach(check => {
        const category = check.metadata?.category || 'other';
        const categoryDisplayName = getCategoryDisplayName(category);
        
        if (!categories[categoryDisplayName]) {
            categories[categoryDisplayName] = [];
        }
        
        categories[categoryDisplayName].push(check);
    });
    
    return categories;
}

// Получение отображаемого названия категории
function getCategoryDisplayName(category) {
    const categoryMap = {
        'face_detection': 'Детекция лица',
        'image_quality': 'Качество изображения',
        'background': 'Анализ фона',
        'other': 'Прочие проверки'
    };
    
    return categoryMap[category] || category;
}

// Создание секции категории
function createCategorySection(categoryName, checks) {
    const section = document.createElement('div');
    section.className = 'card p-6 mb-6';
    
    const categoryIcon = getCategoryIcon(categoryName);
    const categoryColor = getCategoryColor(categoryName);
    
    let sectionHTML = `
        <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <i data-lucide="${categoryIcon}" class="h-5 w-5 mr-2 ${categoryColor}"></i>
            ${categoryName}
        </h3>
        <div class="space-y-6">
    `;
    
    checks.forEach(check => {
        sectionHTML += createCheckSection(check);
    });
    
    sectionHTML += '</div>';
    section.innerHTML = sectionHTML;
    
    return section;
}

// Иконки для категорий
function getCategoryIcon(categoryName) {
    const iconMap = {
        'Детекция лица': 'user',
        'Качество изображения': 'image',
        'Анализ фона': 'layers',
        'Прочие проверки': 'settings'
    };
    
    return iconMap[categoryName] || 'settings';
}

// Цвета для категорий
function getCategoryColor(categoryName) {
    const colorMap = {
        'Детекция лица': 'text-blue-600',
        'Качество изображения': 'text-purple-600', 
        'Анализ фона': 'text-orange-600',
        'Прочие проверки': 'text-gray-600'
    };
    
    return colorMap[categoryName] || 'text-gray-600';
}

// Создание секции одной проверки
function createCheckSection(check) {
    const displayName = check.metadata?.display_name || check.name;
    const description = check.metadata?.description || '';
    const enabled = check.config?.enabled || false;
    
    let html = `
        <div class="border border-gray-200 rounded-lg p-4">
            <div class="flex items-center justify-between mb-3">
                <div>
                    <h4 class="font-medium text-gray-900">${displayName}</h4>
                    ${description ? `<p class="text-sm text-gray-500">${description}</p>` : ''}
                </div>
                <label class="switch">
                    <input type="checkbox" name="${check.name}_enabled" ${enabled ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
            </div>
    `;
    
    // Создаем параметры на основе метаданных
    if (check.metadata && check.metadata.parameters && check.metadata.parameters.length > 0) {
        html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">';
        
        check.metadata.parameters.forEach(param => {
            html += createParameterField(check.name, param, check.config);
        });
        
        html += '</div>';
    }
    
    html += '</div>';
    
    return html;
}

// Создание поля для параметра
function createParameterField(checkName, parameter, config) {
    const value = config[parameter.name] !== undefined ? config[parameter.name] : parameter.default;
    const fieldName = `${checkName}_${parameter.name}`;
    
    let fieldHTML = `
        <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
                ${getParameterDisplayName(parameter.name)}
                ${parameter.required ? '<span class="text-red-500">*</span>' : ''}
            </label>
    `;
    
    if (parameter.type === 'bool') {
        fieldHTML += `
            <label class="switch">
                <input type="checkbox" name="${fieldName}" ${value ? 'checked' : ''}>
                <span class="slider"></span>
            </label>
        `;
    } else if (parameter.type === 'int' || parameter.type === 'float') {
        const step = parameter.type === 'float' ? '0.1' : '1';
        const min = parameter.min_value !== undefined ? `min="${parameter.min_value}"` : '';
        const max = parameter.max_value !== undefined ? `max="${parameter.max_value}"` : '';
        
        fieldHTML += `
            <input type="number" name="${fieldName}" value="${value}" 
                   step="${step}" ${min} ${max} class="form-input w-full">
        `;
    } else if (parameter.choices && parameter.choices.length > 0) {
        fieldHTML += `<select name="${fieldName}" class="form-input w-full">`;
        parameter.choices.forEach(choice => {
            const selected = choice === value ? 'selected' : '';
            fieldHTML += `<option value="${choice}" ${selected}>${choice}</option>`;
        });
        fieldHTML += '</select>';
    } else {
        fieldHTML += `
            <input type="text" name="${fieldName}" value="${value}" class="form-input w-full">
        `;
    }
    
    if (parameter.description) {
        fieldHTML += `<p class="text-xs text-gray-500 mt-1">${parameter.description}</p>`;
    }
    
    fieldHTML += '</div>';
    
    return fieldHTML;
}

// Получение отображаемого названия параметра
function getParameterDisplayName(paramName) {
    const displayMap = {
        'min_count': 'Минимум лиц',
        'max_count': 'Максимум лиц',
        'confidence_threshold': 'Порог уверенности',
        'min_area_ratio': 'Мин. площадь лица',
        'max_area_ratio': 'Макс. площадь лица',
        'max_yaw': 'Макс. поворот (°)',
        'max_pitch': 'Макс. наклон (°)',
        'max_roll': 'Макс. вращение (°)',
        'blurriness_threshold': 'Порог размытости',
        'laplacian_threshold': 'Порог Лапласиана',
        'grayscale_saturation_threshold': 'Порог ч/б',
        'underexposure_threshold': 'Порог недосвета',
        'overexposure_threshold': 'Порог пересвета',
        'low_contrast_threshold': 'Порог контраста',
        'std_dev_threshold': 'Порог однородности',
        'dark_threshold': 'Порог темноты',
        'min_contour_area_ratio': 'Мин. размер контура',
        'person_scale_factor': 'Масштаб детекции',
        'glasses_detection': 'Детекция очков',
        'headwear_detection': 'Детекция головных уборов',
        'hand_detection': 'Детекция рук',
        'red_threshold': 'Порог красного',
        'red_ratio_threshold': 'Соотношение красного',
        'min_red_pixel_ratio': 'Доля красных пикселей',
        'require_color': 'Требовать цветное',
        'shadow_ratio_threshold': 'Порог теней',
        'highlight_ratio_threshold': 'Порог бликов',
        'edge_density_threshold': 'Порог текстуры',
        'grad_mean_threshold': 'Порог градиента'
    };
    
    return displayMap[paramName] || paramName;
}

// Настройка обработчиков форм
function setupFormHandlers() {
    console.log('setupFormHandlers called');
    const form = document.getElementById('validationForm');
    if (!form) return;
    
    form.addEventListener('submit', handleFormSubmit);
}

// Обработка отправки формы
async function handleFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const formData = new FormData(form);
    
    try {
        // Преобразуем FormData в объект конфигурации
        const configUpdates = parseFormDataToConfig(formData);
        
        // Отправляем обновления через API
        const response = await fetch('/api/v1/config/', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                updates: configUpdates,
                validate: true
            })
        });
        
        if (response.ok) {
            showNotification('Настройки успешно сохранены!', 'success');
            // Перенаправление на ту же страницу с параметром успеха
            window.location.href = '/admin/validation?success=1';
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка сохранения настроек');
        }
    } catch (error) {
        console.error('Ошибка сохранения:', error);
        showNotification('Ошибка при сохранении настроек: ' + error.message, 'error');
    }
}

// Парсинг FormData в объект конфигурации
function parseFormDataToConfig(formData) {
    const config = {
        system: {
            processing: {},
            storage: {}
        },
        validation: {
            image_requirements: {},
            checks: {}
        }
    };
    
    // Обрабатываем каждое поле формы
    for (let [key, value] of formData.entries()) {
        if (key === 'stop_on_failure') {
            config.system.stop_on_failure = value === 'on';
        } else if (key === 'max_check_time') {
            config.system.max_check_time = parseFloat(value);
        } else if (key === 'max_concurrent') {
            config.system.processing.max_concurrent = parseInt(value);
        } else if (key === 'min_width') {
            config.validation.image_requirements.min_width = parseInt(value);
        } else if (key === 'min_height') {
            config.validation.image_requirements.min_height = parseInt(value);
        } else if (key === 'max_file_size') {
            config.system.storage.max_file_size_mb = parseFloat(value);
        } else if (key.endsWith('_enabled')) {
            // Поле включения модуля
            const checkName = key.replace('_enabled', '');
            if (!config.validation.checks[checkName]) {
                config.validation.checks[checkName] = {};
            }
            config.validation.checks[checkName].enabled = value === 'on';
        } else if (key.includes('_')) {
            // Параметр модуля
            const parts = key.split('_');
            if (parts.length >= 2) {
                const checkName = parts[0];
                const paramName = parts.slice(1).join('_');
                
                if (!config.validation.checks[checkName]) {
                    config.validation.checks[checkName] = {};
                }
                
                // Определяем тип значения из метаданных
                const metadata = allChecksMetadata[checkName];
                const param = metadata?.parameters?.find(p => p.name === paramName);
                
                if (param) {
                    if (param.type === 'bool') {
                        config.validation.checks[checkName][paramName] = value === 'on';
                    } else if (param.type === 'int') {
                        config.validation.checks[checkName][paramName] = parseInt(value);
                    } else if (param.type === 'float') {
                        config.validation.checks[checkName][paramName] = parseFloat(value);
                    } else {
                        config.validation.checks[checkName][paramName] = value;
                    }
                } else {
                    // Fallback для параметров без метаданных
                    config.validation.checks[checkName][paramName] = value;
                }
            }
        }
    }
    
    return config;
}

// Функция для отображения уведомлений (если не определена в admin.js)
function showNotification(message, type = 'info') {
    if (typeof window.showNotification === 'function') {
        window.showNotification(message, type);
        return;
    }
    
    // Fallback реализация
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'error' : 'success'} fixed top-4 right-4 z-50`;
    notification.innerHTML = `
        <i data-lucide="${type === 'error' ? 'alert-circle' : 'check-circle'}" class="h-5 w-5 inline mr-2"></i>
        ${message}
    `;
    
    document.body.appendChild(notification);
    
    // Автоматическое удаление через 5 секунд
    setTimeout(() => {
        notification.remove();
    }, 5000);
    
    // Обновить иконки
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
} 