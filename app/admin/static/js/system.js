/**
 * Модуль управления системными настройками
 * Использует Framework.js для управления состоянием и компонентами
 */

class SystemConfigManager extends Framework.Component {
    constructor() {
        super('#systemForm', {
            initialState: {
                testing: false,
                resetting: false
            }
        });
        
        this.init();
    }

    init() {
        console.log('SystemConfigManager: Инициализация...');
        this.bindEvents();
    }

    bindEvents() {
        // Не используем стандартную отправку формы, так как это обычная форма
        // Просто добавляем обработчики для кнопок
    }

    async testConfiguration() {
        if (this.getState().testing) return;
        
        this.setState({ testing: true });
        
        try {
            const form = document.getElementById('systemForm');
            const formData = new FormData(form);
            
            Framework.NotificationSystem.show('Тестирование конфигурации...', 'info');
            
            const response = await Framework.HttpClient.request('/admin/system/test', {
                method: 'POST',
                body: formData,
                headers: {} // Убираем Content-Type для FormData
            });
            
            if (response.success) {
                this.showTestResults(response);
            } else {
                this.showTestErrors(response);
            }
            
        } catch (error) {
            console.error('Ошибка тестирования:', error);
            Framework.NotificationSystem.show('Ошибка тестирования: ' + error.message, 'error');
        } finally {
            this.setState({ testing: false });
        }
    }

    showTestResults(response) {
        const message = response.message;
        const systemInfo = response.system_info;
        
        let details = '';
        if (systemInfo) {
            details = `\n\nИнформация о системе:\n` +
                     `CPU ядер: ${systemInfo.cpu_cores}\n` +
                     `Память: ${systemInfo.memory_gb} ГБ\n` +
                     `Свободное место: ${systemInfo.disk_free_gb} ГБ`;
        }
        
        Framework.NotificationSystem.show(message + details, 'success', 8000);
    }

    showTestErrors(response) {
        let errorMessage = response.error;
        
        if (response.validation_errors && response.validation_errors.length > 0) {
            errorMessage += '\n\nОшибки валидации:\n• ' + response.validation_errors.join('\n• ');
        }
        
        Framework.NotificationSystem.show(errorMessage, 'error', 10000);
    }

    async resetToDefaults() {
        if (this.getState().resetting) return;
        
        if (!confirm('Вы уверены? Все системные настройки будут сброшены к значениям по умолчанию!')) {
            return;
        }

        this.setState({ resetting: true });
        
        try {
            Framework.NotificationSystem.show('Сброс настроек...', 'info');
            
            const response = await Framework.HttpClient.request('/admin/system/reset', {
                method: 'POST'
            });
            
            if (response.success) {
                Framework.NotificationSystem.show(response.message, 'success');
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                Framework.NotificationSystem.show('Ошибка сброса: ' + response.error, 'error');
            }
            
        } catch (error) {
            console.error('Ошибка сброса:', error);
            Framework.NotificationSystem.show('Ошибка сброса настроек: ' + error.message, 'error');
        } finally {
            this.setState({ resetting: false });
        }
    }
}

// Глобальные функции для совместимости с шаблоном
function testConfiguration() {
    if (systemManager) {
        systemManager.testConfiguration();
    }
}

function resetToDefaults() {
    if (systemManager) {
        systemManager.resetToDefaults();
    }
}

// Инициализация при загрузке DOM
let systemManager;

document.addEventListener('DOMContentLoaded', function() {
    console.log('system.js: DOM загружен, инициализация...');
    systemManager = new SystemConfigManager();
    
    // Инициализируем иконки Lucide
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
});

console.log('system.js загружен'); 