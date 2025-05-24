/**
 * Основные функции административной панели
 * Использует Framework.js для управления состоянием и компонентами
 */

class AdminManager extends Framework.Component {
    constructor() {
        super(document.body, {
            initialState: {
                autoSaveEnabled: true,
                autoSaveTimeout: null
            }
        });
        
        this.init();
    }

    init() {
        console.log('AdminManager: Инициализация...');
        this.bindEvents();
        this.initAutoSave();
        this.initFormToggles();
    }

    bindEvents() {
        // Инициализировать иконки Lucide при загрузке
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    // Функциональность авто-сохранения
    scheduleAutoSave() {
        const state = this.getState();
        if (!state.autoSaveEnabled) return;
        
        if (state.autoSaveTimeout) {
            clearTimeout(state.autoSaveTimeout);
        }
        
        const timeoutId = setTimeout(() => {
            console.log('Авто-сохранение конфигурации...');
            // Здесь можно добавить логику авто-сохранения
        }, 2000);
        
        this.setState({ autoSaveTimeout: timeoutId });
    }

    initAutoSave() {
        const formInputs = document.querySelectorAll('input, select, textarea');
        formInputs.forEach(input => {
            input.addEventListener('change', () => this.scheduleAutoSave());
        });
    }

    // Инициализация переключателей
    initFormToggles() {
        const enabledSwitches = document.querySelectorAll('input[type="checkbox"][id$="_enabled"]');
        enabledSwitches.forEach(switch_ => {
            const settingsId = switch_.id.replace('_enabled', '_settings');
            switch_.addEventListener('change', function() {
                const settingsElement = document.getElementById(settingsId);
                if (settingsElement) {
                    Framework.DOMUtils.toggle(settingsElement);
                }
            });
        });
    }

    // Валидация форм
    validateForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return true;
        
        const inputs = form.querySelectorAll('input[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                Framework.DOMUtils.addClass(input, 'border-red-500');
                isValid = false;
            } else {
                Framework.DOMUtils.removeClass(input, 'border-red-500');
            }
        });
        
        return isValid;
    }

    // Переключение секций
    toggleSection(sectionId) {
        const section = document.getElementById(sectionId);
        if (section) {
            Framework.DOMUtils.toggle(section);
        }
    }
}

// Утилиты для UI взаимодействий
function toggleSection(sectionId) {
    if (adminManager) {
        adminManager.toggleSection(sectionId);
    }
}

// Валидация форм
function validateForm(formId) {
    if (adminManager) {
        return adminManager.validateForm(formId);
    }
    return true;
}

// Предпросмотр изменений
function previewChanges() {
    const form = document.getElementById('validationForm');
    if (!form) return;
    
    const formData = new FormData(form);
    const config = {};
    
    for (let [key, value] of formData.entries()) {
        config[key] = value;
    }
    
    const previewContent = document.getElementById('previewContent');
    const previewModal = document.getElementById('previewModal');
    
    if (previewContent && previewModal) {
        previewContent.textContent = JSON.stringify(config, null, 2);
        Framework.DOMUtils.removeClass(previewModal, 'hidden');
    }
}

// Закрыть предпросмотр
function closePreview() {
    const previewModal = document.getElementById('previewModal');
    if (previewModal) {
        Framework.DOMUtils.addClass(previewModal, 'hidden');
    }
}

// Сброс к настройкам по умолчанию
function resetToDefaults() {
    if (confirm('Вы уверены? Все настройки будут сброшены к значениям по умолчанию!')) {
        Framework.HttpClient.post('/admin/reset')
            .then(() => {
                window.location.reload();
            })
            .catch(error => {
                console.error('Ошибка:', error);
                Framework.NotificationSystem.show('Ошибка при сбросе настроек', 'error');
            });
    }
}

// Экспорт конфигурации
function exportConfig() {
    window.open('/admin/export', '_blank');
}

// Валидация конфигурации
function validateConfiguration() {
    const form = document.getElementById('validationForm');
    if (!form) return;
    
    if (validateForm('validationForm')) {
        Framework.NotificationSystem.show('Конфигурация валидна!', 'success');
    } else {
        Framework.NotificationSystem.show('Найдены ошибки в конфигурации. Проверьте обязательные поля.', 'error');
    }
}

// Обработка ошибок AJAX запросов
function handleAjaxError(error) {
    console.error('AJAX ошибка:', error);
    Framework.NotificationSystem.show('Произошла ошибка при выполнении запроса', 'error');
}

// Инициализация при загрузке DOM
let adminManager;

document.addEventListener('DOMContentLoaded', function() {
    console.log('admin.js: DOM загружен, инициализация...');
    adminManager = new AdminManager();
});

console.log('admin.js загружен'); 