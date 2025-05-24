/**
 * Модуль управления настройками валидации
 * Использует Framework.js для управления состоянием и компонентами
 */

class ValidationConfigManager extends Framework.Component {
    constructor() {
        super('#validation-form-container', {
            initialState: {
                loading: true,
                config: null,
                checksMetadata: {},
                error: null,
                initialized: false
            }
        });

        this.loadingIndicator = document.getElementById('loading-indicator');
        this.modulesContainer = document.getElementById('modules-container');
        
        this.init();
    }

    async init() {
        console.log('ValidationConfigManager: Инициализация...');
        
        try {
            this.setState({ loading: true, error: null });
            this.showLoading(true);
            
            await this.loadConfiguration();
            await this.loadChecksMetadata();
            
            this.setState({ loading: false, initialized: true });
            this.render();
            this.showLoading(false);
            
            console.log('ValidationConfigManager: Инициализация завершена');
        } catch (error) {
            console.error('ValidationConfigManager: Ошибка инициализации:', error);
            this.setState({ loading: false, error: error.message });
            this.showError('Ошибка загрузки конфигурации: ' + error.message);
        }
    }

    async loadConfiguration() {
        console.log('Загрузка конфигурации...');
        const config = await Framework.HttpClient.get('/api/v1/config/');
        this.setState({ config });
        console.log('Конфигурация загружена:', config);
    }

    async loadChecksMetadata() {
        console.log('Загрузка метаданных модулей...');
        try {
            const data = await Framework.HttpClient.get('/admin/api/checks/discovery');
            this.setState({ checksMetadata: data.checks || {} });
            console.log('Метаданные модулей загружены:', data.checks);
        } catch (error) {
            console.error('Ошибка загрузки метаданных:', error);
            this.setState({ checksMetadata: {} });
        }
    }

    showLoading(show) {
        if (this.loadingIndicator) {
            Framework.DOMUtils[show ? 'show' : 'hide'](this.loadingIndicator);
        }
        if (this.element) {
            Framework.DOMUtils[show ? 'hide' : 'show'](this.element);
        }
    }

    showError(message) {
        console.error('Ошибка:', message);
        if (this.loadingIndicator) {
            this.loadingIndicator.innerHTML = `
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
            if (typeof lucide !== 'undefined') {
                lucide.createIcons();
            }
        }
    }

    render() {
        const state = this.getState();
        if (!state.config || !state.initialized) return;

        this.fillGlobalSettings();
        this.generateModuleSections();
        
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    fillGlobalSettings() {
        const { config } = this.getState();
        
        this.setFieldValue('stop_on_failure', config.system?.processing?.stop_on_failure || false);
        this.setFieldValue('max_check_time', config.system?.processing?.max_check_time || 5.0);
        this.setFieldValue('max_concurrent', config.system?.processing?.max_concurrent || 5);
        this.setFieldValue('min_width', config.validation?.image_requirements?.min_width || 400);
        this.setFieldValue('min_height', config.validation?.image_requirements?.min_height || 500);
        this.setFieldValue('max_file_size', config.system?.storage?.max_file_size_mb || 1.0);
    }

    setFieldValue(fieldId, value) {
        const field = document.getElementById(fieldId);
        if (field) {
            if (field.type === 'checkbox') {
                field.checked = Boolean(value);
            } else {
                field.value = value;
            }
            console.log(`Установлено ${fieldId} = ${value}`);
        }
    }

    generateModuleSections() {
        if (!this.modulesContainer) return;
        
        this.modulesContainer.innerHTML = '';
        
        const availableChecks = this.getAvailableChecks();
        const categories = this.groupChecksByCategory(availableChecks);
        
        Object.keys(categories).forEach(category => {
            const categorySection = this.createCategorySection(category, categories[category]);
            this.modulesContainer.appendChild(categorySection);
        });
        
        console.log('Секции модулей созданы');
    }

    getAvailableChecks() {
        const { config, checksMetadata } = this.getState();
        const checks = [];
        
        // Из текущей конфигурации
        if (config.validation?.checks) {
            Object.keys(config.validation.checks).forEach(checkName => {
                checks.push({
                    name: checkName,
                    config: config.validation.checks[checkName],
                    metadata: checksMetadata[checkName] || null
                });
            });
        }
        
        // Добавляем модули из метаданных, которых нет в конфигурации
        Object.keys(checksMetadata).forEach(checkName => {
            if (!checks.find(c => c.name === checkName)) {
                checks.push({
                    name: checkName,
                    config: { enabled: false },
                    metadata: checksMetadata[checkName]
                });
            }
        });
        
        return checks;
    }

    groupChecksByCategory(checks) {
        const categories = {};
        
        checks.forEach(check => {
            const category = check.metadata?.category || 'other';
            const categoryDisplayName = this.getCategoryDisplayName(category);
            
            if (!categories[categoryDisplayName]) {
                categories[categoryDisplayName] = [];
            }
            
            categories[categoryDisplayName].push(check);
        });
        
        return categories;
    }

    getCategoryDisplayName(category) {
        const categoryMap = {
            'face_detection': 'Детекция лица',
            'image_quality': 'Качество изображения',
            'background': 'Анализ фона',
            'other': 'Прочие проверки'
        };
        
        return categoryMap[category] || category;
    }

    createCategorySection(categoryName, checks) {
        const categoryIcon = this.getCategoryIcon(categoryName);
        const categoryColor = this.getCategoryColor(categoryName);
        
        const section = Framework.DOMUtils.createElement('div', {
            className: 'card p-6 mb-6',
            innerHTML: `
                <h3 class="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                    <i data-lucide="${categoryIcon}" class="h-5 w-5 mr-2 ${categoryColor}"></i>
                    ${categoryName}
                </h3>
                <div class="space-y-6">
                    ${checks.map(check => this.createCheckSection(check)).join('')}
                </div>
            `
        });
        
        return section;
    }

    getCategoryIcon(categoryName) {
        const iconMap = {
            'Детекция лица': 'user',
            'Качество изображения': 'image',
            'Анализ фона': 'layers',
            'Прочие проверки': 'settings'
        };
        
        return iconMap[categoryName] || 'settings';
    }

    getCategoryColor(categoryName) {
        const colorMap = {
            'Детекция лица': 'text-blue-600',
            'Качество изображения': 'text-purple-600', 
            'Анализ фона': 'text-orange-600',
            'Прочие проверки': 'text-gray-600'
        };
        
        return colorMap[categoryName] || 'text-gray-600';
    }

    createCheckSection(check) {
        const displayName = check.metadata?.display_name || check.name;
        const description = check.metadata?.description || '';
        const enabled = check.config?.enabled || false;
        
        let parametersHTML = '';
        if (check.metadata?.parameters?.length > 0) {
            parametersHTML = `
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    ${check.metadata.parameters.map(param => 
                        this.createParameterField(check.name, param, check.config)
                    ).join('')}
                </div>
            `;
        }
        
        return `
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
                ${parametersHTML}
            </div>
        `;
    }

    createParameterField(checkName, parameter, config) {
        const value = config[parameter.name] !== undefined ? config[parameter.name] : parameter.default;
        const fieldName = `${checkName}_${parameter.name}`;
        const displayName = this.getParameterDisplayName(parameter.name);
        
        let inputHTML = '';
        
        if (parameter.type === 'bool') {
            inputHTML = `
                <label class="switch">
                    <input type="checkbox" name="${fieldName}" ${value ? 'checked' : ''}>
                    <span class="slider"></span>
                </label>
            `;
        } else if (parameter.type === 'int' || parameter.type === 'float') {
            const step = parameter.type === 'float' ? '0.1' : '1';
            const min = parameter.min_value !== undefined ? `min="${parameter.min_value}"` : '';
            const max = parameter.max_value !== undefined ? `max="${parameter.max_value}"` : '';
            
            inputHTML = `
                <input type="number" name="${fieldName}" value="${value}" 
                       step="${step}" ${min} ${max} class="form-input w-full">
            `;
        } else if (parameter.choices?.length > 0) {
            inputHTML = `
                <select name="${fieldName}" class="form-input w-full">
                    ${parameter.choices.map(choice => 
                        `<option value="${choice}" ${choice === value ? 'selected' : ''}>${choice}</option>`
                    ).join('')}
                </select>
            `;
        } else {
            inputHTML = `
                <input type="text" name="${fieldName}" value="${value}" class="form-input w-full">
            `;
        }
        
        return `
            <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    ${displayName}
                    ${parameter.required ? '<span class="text-red-500">*</span>' : ''}
                </label>
                ${inputHTML}
                ${parameter.description ? `<p class="text-xs text-gray-500 mt-1">${parameter.description}</p>` : ''}
            </div>
        `;
    }

    getParameterDisplayName(paramName) {
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
            'low_contrast_threshold': 'Порог контраста'
        };
        
        return displayMap[paramName] || paramName;
    }

    bindEvents() {
        const form = document.getElementById('validationForm');
        if (form) {
            form.addEventListener('submit', this.handleFormSubmit.bind(this));
        }
    }

    async handleFormSubmit(event) {
        event.preventDefault();
        console.log('Отправка формы...');
        
        try {
            const formData = new FormData(event.target);
            const configUpdates = this.parseFormDataToConfig(formData);
            
            await Framework.HttpClient.put('/api/v1/config/', {
                updates: configUpdates,
                validate: true
            });
            
            Framework.NotificationSystem.show('Настройки успешно сохранены!', 'success');
            setTimeout(() => {
                window.location.href = '/admin/validation?success=1';
            }, 1000);
            
        } catch (error) {
            console.error('Ошибка сохранения:', error);
            Framework.NotificationSystem.show('Ошибка при сохранении настроек: ' + error.message, 'error');
        }
    }

    parseFormDataToConfig(formData) {
        const { checksMetadata } = this.getState();
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
        
        for (let [key, value] of formData.entries()) {
            if (key === 'stop_on_failure') {
                config.system.processing.stop_on_failure = value === 'on';
            } else if (key === 'max_check_time') {
                config.system.processing.max_check_time = parseFloat(value);
            } else if (key === 'max_concurrent') {
                config.system.processing.max_concurrent = parseInt(value);
            } else if (key === 'min_width') {
                config.validation.image_requirements.min_width = parseInt(value);
            } else if (key === 'min_height') {
                config.validation.image_requirements.min_height = parseInt(value);
            } else if (key === 'max_file_size') {
                config.system.storage.max_file_size_mb = parseFloat(value);
            } else if (key.endsWith('_enabled')) {
                const checkName = key.replace('_enabled', '');
                if (!config.validation.checks[checkName]) {
                    config.validation.checks[checkName] = {};
                }
                config.validation.checks[checkName].enabled = value === 'on';
            } else if (key.includes('_')) {
                const parts = key.split('_');
                if (parts.length >= 2) {
                    const checkName = parts[0];
                    const paramName = parts.slice(1).join('_');
                    
                    if (!config.validation.checks[checkName]) {
                        config.validation.checks[checkName] = {};
                    }
                    
                    const metadata = checksMetadata[checkName];
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
                        config.validation.checks[checkName][paramName] = value;
                    }
                }
            }
        }
        
        return config;
    }
}

// Глобальные функции для совместимости с шаблоном
function resetToDefaults() {
    if (validationManager && validationManager.getState().initialized) {
        if (confirm('Сбросить все настройки к значениям по умолчанию?')) {
            location.reload();
        }
    }
}

function exportConfig() {
    if (validationManager) {
        const { config } = validationManager.getState();
        if (config) {
            const dataStr = JSON.stringify(config, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'validation_config.json';
            link.click();
            URL.revokeObjectURL(url);
        }
    }
}

function previewChanges() {
    const modal = document.getElementById('previewModal');
    const content = document.getElementById('previewContent');
    
    if (modal && content && validationManager) {
        const form = document.getElementById('validationForm');
        if (form) {
            const formData = new FormData(form);
            const config = validationManager.parseFormDataToConfig(formData);
            content.textContent = JSON.stringify(config, null, 2);
            modal.classList.remove('hidden');
        }
    }
}

function closePreview() {
    const modal = document.getElementById('previewModal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

function validateConfiguration() {
    if (validationManager && validationManager.getState().initialized) {
        Framework.NotificationSystem.show('Конфигурация валидна!', 'success');
    }
}

// Инициализация при загрузке DOM
let validationManager;

document.addEventListener('DOMContentLoaded', function() {
    console.log('validation.js: DOM загружен, инициализация...');
    validationManager = new ValidationConfigManager();
});

console.log('validation.js загружен'); 