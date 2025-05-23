// Основные функции административной панели

// Инициализация после загрузки DOM
document.addEventListener('DOMContentLoaded', function() {
    // Инициализировать иконки Lucide
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    
    // Добавить обработчики для авто-сохранения
    initAutoSave();
    
    // Инициализировать переключатели форм
    initFormToggles();
});

// Утилиты для UI взаимодействий
function toggleSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.toggle('hidden');
    }
}

// Валидация форм
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return true;
    
    const inputs = form.querySelectorAll('input[required]');
    let isValid = true;
    
    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('border-red-500');
            isValid = false;
        } else {
            input.classList.remove('border-red-500');
        }
    });
    
    return isValid;
}

// Функциональность авто-сохранения
let autoSaveTimeout;
function scheduleAutoSave() {
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
        console.log('Авто-сохранение конфигурации...');
        // Здесь можно добавить логику авто-сохранения
    }, 2000);
}

function initAutoSave() {
    const formInputs = document.querySelectorAll('input, select, textarea');
    formInputs.forEach(input => {
        input.addEventListener('change', scheduleAutoSave);
    });
}

// Инициализация переключателей
function initFormToggles() {
    const enabledSwitches = document.querySelectorAll('input[type="checkbox"][id$="_enabled"]');
    enabledSwitches.forEach(switch_ => {
        const settingsId = switch_.id.replace('_enabled', '_settings');
        switch_.addEventListener('change', function() {
            toggleSection(settingsId);
        });
    });
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
        previewModal.classList.remove('hidden');
    }
}

// Закрыть предпросмотр
function closePreview() {
    const previewModal = document.getElementById('previewModal');
    if (previewModal) {
        previewModal.classList.add('hidden');
    }
}

// Сброс к настройкам по умолчанию
function resetToDefaults() {
    if (confirm('Вы уверены? Все настройки будут сброшены к значениям по умолчанию!')) {
        fetch('/admin/reset', { method: 'POST' })
            .then(response => {
                if (response.ok) {
                    window.location.reload();
                } else {
                    alert('Ошибка при сбросе настроек');
                }
            })
            .catch(error => {
                console.error('Ошибка:', error);
                alert('Ошибка при сбросе настроек');
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
        alert('Конфигурация валидна!');
    } else {
        alert('Найдены ошибки в конфигурации. Проверьте обязательные поля.');
    }
}

// Функции для работы с уведомлениями
function showNotification(message, type = 'info') {
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

// Обработка ошибок AJAX запросов
function handleAjaxError(error) {
    console.error('AJAX ошибка:', error);
    showNotification('Произошла ошибка при выполнении запроса', 'error');
} 