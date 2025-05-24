/**
 * Модуль мониторинга операций
 * Использует Framework.js для управления состоянием и компонентами
 */

class OperationsManager extends Framework.Component {
    constructor() {
        super('#operations-container', {
            initialState: {
                updateInterval: null,
                isUpdating: false,
                lastUpdateTime: null,
                charts: {
                    processing: null,
                    success: null,
                    metrics: null
                }
            }
        });
        
        // Константы
        this.UPDATE_INTERVAL = 5000; // 5 секунд
        this.MAX_CHART_POINTS = 20;
        
        this.init();
    }

    init() {
        console.log('OperationsManager: Инициализация...');
        this.initializeCharts();
        this.startDataUpdate();
        this.bindEvents();
    }

    bindEvents() {
        // Настройка обработчиков событий
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.stopDataUpdate();
            } else {
                this.startDataUpdate();
            }
        });
    }

    // Инициализация графиков
    initializeCharts() {
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js не загружен, графики недоступны');
            return;
        }

        this.initProcessingTimeChart();
        this.initSuccessRateChart();
        this.initSystemMetricsChart();
    }

    initProcessingTimeChart() {
        const ctx = document.getElementById('processingTimeChart');
        if (!ctx) return;

        const charts = this.getState().charts;
        charts.processing = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Время обработки (сек)',
                    data: [],
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.1,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Секунды'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Время'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        this.setState({ charts });
    }

    initSuccessRateChart() {
        const ctx = document.getElementById('successRateChart');
        if (!ctx) return;

        const charts = this.getState().charts;
        charts.success = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Одобрено', 'Отклонено', 'На проверке'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: [
                        'rgb(34, 197, 94)',
                        'rgb(239, 68, 68)',
                        'rgb(251, 191, 36)'
                    ],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });

        this.setState({ charts });
    }

    initSystemMetricsChart() {
        const ctx = document.getElementById('systemMetricsChart');
        if (!ctx) return;

        const charts = this.getState().charts;
        charts.metrics = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['CPU', 'Memory', 'Cache Hit Rate'],
                datasets: [{
                    label: 'Использование (%)',
                    data: [0, 0, 0],
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(16, 185, 129, 0.8)',
                        'rgba(245, 158, 11, 0.8)'
                    ],
                    borderColor: [
                        'rgb(59, 130, 246)',
                        'rgb(16, 185, 129)',
                        'rgb(245, 158, 11)'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Проценты'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });

        this.setState({ charts });
    }

    // Запуск обновления данных
    startDataUpdate() {
        if (this.getState().updateInterval) return;

        this.updateOperationsData();
        const intervalId = setInterval(() => this.updateOperationsData(), this.UPDATE_INTERVAL);
        
        this.setState({ updateInterval: intervalId });
        console.log('Запущено обновление данных операций с интервалом:', this.UPDATE_INTERVAL);
    }

    // Остановка обновления данных
    stopDataUpdate() {
        const { updateInterval } = this.getState();
        if (updateInterval) {
            clearInterval(updateInterval);
            this.setState({ updateInterval: null });
            console.log('Остановлено обновление данных операций');
        }
    }

    // Обновление данных операций
    async updateOperationsData() {
        if (this.getState().isUpdating) return;

        this.setState({ isUpdating: true });

        try {
            await Promise.all([
                this.updateMetrics(),
                this.updateCurrentOperations(),
                this.updateValidationHistory()
            ]);

            this.updateLastRefreshTime();

        } catch (error) {
            console.error('Ошибка обновления данных операций:', error);
            Framework.NotificationSystem.show('Ошибка обновления данных: ' + error.message, 'error');
        } finally {
            this.setState({ isUpdating: false });
        }
    }

    // Обновление метрик
    async updateMetrics() {
        try {
            const metrics = await Framework.HttpClient.get('/admin/api/metrics');
            
            // Обновляем основные метрики
            this.updateMetricValue('active-operations', metrics.active_operations);
            this.updateMetricValue('successful-today', metrics.successful_today);
            this.updateMetricValue('rejected-today', metrics.rejected_today);
            this.updateMetricValue('avg-processing-time', metrics.avg_processing_time.toFixed(2) + 's');
            
            // Обновляем новые расширенные метрики
            this.updateMetricValue('total-validations', metrics.total_validations || 0);
            this.updateMetricValue('manual-review-count', metrics.manual_review_count || 0);
            this.updateMetricValue('approval-rate', (metrics.approval_rate || 0).toFixed(1) + '%');
            this.updateMetricValue('avg-file-size', (metrics.avg_file_size_mb || 0).toFixed(2) + ' МБ');
            
            // Обновляем статистику за период
            this.updateMetricValue('total-24h', metrics.total_24h || 0);
            this.updateMetricValue('total-1h', metrics.total_1h || 0);
            
            // Обновляем топ причины отклонения
            this.updateTopRejectionReasons(metrics.top_rejection_reasons || []);
            
            // Обновляем системные метрики
            this.updateMetricValue('cpu-usage', metrics.cpu_usage.toFixed(1) + '%');
            this.updateMetricValue('memory-usage', metrics.memory_usage.toFixed(1) + '%');
            
            // Обновляем прогресс-бары
            this.updateProgressBar('cpu-progress', metrics.cpu_usage);
            this.updateProgressBar('memory-progress', metrics.memory_usage);
            
            // Обновляем графики
            this.updateSystemMetricsChart(metrics);
            this.updateProcessingTimeChart(metrics);
            
        } catch (error) {
            console.error('Ошибка загрузки метрик:', error);
        }
    }

    updateMetricValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    }

    updateProgressBar(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.width = Math.min(value, 100) + '%';
        }
    }

    updateTopRejectionReasons(reasons) {
        const container = document.getElementById('top-rejection-reasons');
        if (!container) return;

        if (!reasons || reasons.length === 0) {
            container.innerHTML = '<p class="text-sm text-gray-500">Нет данных</p>';
            return;
        }

        let html = '';
        reasons.slice(0, 3).forEach(([reason, count], index) => {
            const colors = ['text-red-600', 'text-orange-600', 'text-yellow-600'];
            const truncatedReason = reason.length > 40 ? reason.substring(0, 40) + '...' : reason;
            
            html += `
                <div class="flex justify-between items-center text-sm">
                    <span class="flex-1 ${colors[index]} font-medium" title="${reason}">
                        ${index + 1}. ${truncatedReason}
                    </span>
                    <span class="text-gray-600 font-semibold ml-2">${count}</span>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }

    updateSystemMetricsChart(metrics) {
        const { charts } = this.getState();
        if (!charts.metrics) return;

        charts.metrics.data.datasets[0].data = [
            metrics.cpu_usage,
            metrics.memory_usage,
            metrics.cache_hit_rate || 0
        ];
        charts.metrics.update();
    }

    updateProcessingTimeChart(metrics) {
        const { charts } = this.getState();
        if (!charts.processing) return;

        const now = new Date().toLocaleTimeString();
        
        charts.processing.data.labels.push(now);
        charts.processing.data.datasets[0].data.push(metrics.avg_processing_time);
        
        // Ограничиваем количество точек
        if (charts.processing.data.labels.length > this.MAX_CHART_POINTS) {
            charts.processing.data.labels.shift();
            charts.processing.data.datasets[0].data.shift();
        }
        
        charts.processing.update();
    }

    // Обновление активных операций
    async updateCurrentOperations() {
        try {
            const operations = await Framework.HttpClient.get('/admin/api/operations/current');
            this.updateActiveOperationsList(operations);
        } catch (error) {
            console.error('Ошибка загрузки активных операций:', error);
        }
    }

    updateActiveOperationsList(operations) {
        const container = document.getElementById('active-operations-list');
        if (!container) return;

        if (!operations || operations.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-4">Нет активных операций</p>';
            return;
        }

        container.innerHTML = operations.map(op => `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div class="flex items-center space-x-3">
                    <div class="h-6 w-6 rounded-full bg-blue-100 flex items-center justify-center">
                        <i data-lucide="clock" class="h-4 w-4 text-blue-600"></i>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-gray-900">${op.filename}</p>
                        <p class="text-xs text-gray-500">ID: ${op.validation_id}</p>
                    </div>
                </div>
                <div class="text-right">
                    <p class="text-sm text-gray-900">${op.current_check}</p>
                    <p class="text-xs text-gray-500">${op.elapsed_time}s</p>
                </div>
            </div>
        `).join('');

        // Обновляем иконки
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }

    // Обновление истории валидации
    async updateValidationHistory() {
        try {
            const response = await Framework.HttpClient.get('/admin/api/validation/history?limit=10');
            this.updateValidationHistoryTable(response.items || []);
            this.updateSuccessRateChart(response.items || []);
        } catch (error) {
            console.error('Ошибка загрузки истории валидации:', error);
        }
    }

    updateValidationHistoryTable(items) {
        const tbody = document.getElementById('validation-history-tbody');
        if (!tbody) return;

        if (!items || items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-gray-500">Нет данных</td></tr>';
            return;
        }

        tbody.innerHTML = items.map(item => `
            <tr class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    ${item.id}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${item.filename}
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                    ${this.getStatusBadge(item.status)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${item.processing_time ? item.processing_time.toFixed(2) + 's' : 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${new Date(item.created_at).toLocaleString()}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <button onclick="viewValidationDetails('${item.id}')" 
                            class="text-blue-600 hover:text-blue-900">
                        Подробнее
                    </button>
                </td>
            </tr>
        `).join('');
    }

    getStatusBadge(status) {
        const statusConfig = {
            'APPROVED': { class: 'bg-green-100 text-green-800', text: 'Одобрено' },
            'REJECTED': { class: 'bg-red-100 text-red-800', text: 'Отклонено' },
            'MANUAL_REVIEW': { class: 'bg-yellow-100 text-yellow-800', text: 'На проверке' },
            'PROCESSING': { class: 'bg-blue-100 text-blue-800', text: 'Обработка' },
            'PENDING': { class: 'bg-gray-100 text-gray-800', text: 'Ожидание' },
            'FAILED': { class: 'bg-red-100 text-red-800', text: 'Ошибка' }
        };

        const config = statusConfig[status] || { class: 'bg-gray-100 text-gray-800', text: status || 'Неизвестно' };
        return `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.class}">
                    ${config.text}
                </span>`;
    }

    updateSuccessRateChart(items) {
        const { charts } = this.getState();
        if (!charts.success || !items) return;

        const statusCounts = {
            'APPROVED': 0,
            'REJECTED': 0,
            'MANUAL_REVIEW': 0
        };

        items.forEach(item => {
            if (statusCounts.hasOwnProperty(item.status)) {
                statusCounts[item.status]++;
            }
        });

        charts.success.data.datasets[0].data = [
            statusCounts.APPROVED,
            statusCounts.REJECTED,
            statusCounts.MANUAL_REVIEW
        ];
        charts.success.update();
    }

    updateLastRefreshTime() {
        const now = new Date();
        this.setState({ lastUpdateTime: now });
        
        const timeElement = document.getElementById('last-refresh-time');
        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString();
        }
    }

    // Методы для экспорта и очистки
    async exportReports() {
        try {
            Framework.NotificationSystem.show('Экспорт отчетов...', 'info');
            const blob = await Framework.HttpClient.get('/admin/api/reports/export');
            
            // Создаем ссылку для скачивания
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `operations_report_${new Date().toISOString().split('T')[0]}.csv`;
            link.click();
            window.URL.revokeObjectURL(url);
            
            Framework.NotificationSystem.show('Отчет экспортирован успешно', 'success');
        } catch (error) {
            console.error('Ошибка экспорта:', error);
            Framework.NotificationSystem.show('Ошибка экспорта отчета', 'error');
        }
    }

    async clearOldRecords() {
        if (!confirm('Удалить записи старше 30 дней? Это действие нельзя отменить.')) {
            return;
        }

        try {
            Framework.NotificationSystem.show('Очистка старых записей...', 'info');
            await Framework.HttpClient.delete('/admin/api/operations/cleanup');
            Framework.NotificationSystem.show('Старые записи удалены', 'success');
            
            // Обновляем данные
            this.updateOperationsData();
        } catch (error) {
            console.error('Ошибка очистки:', error);
            Framework.NotificationSystem.show('Ошибка очистки записей', 'error');
        }
    }
}

// Глобальные функции для совместимости с шаблоном
function refreshData() {
    if (operationsManager) {
        operationsManager.updateOperationsData();
    }
}

function exportReport() {
    if (operationsManager) {
        operationsManager.exportReports();
    }
}

function clearOldRecords() {
    if (operationsManager) {
        operationsManager.clearOldRecords();
    }
}

async function viewValidationDetails(validationId) {
    try {
        const details = await Framework.HttpClient.get(`/admin/api/validation/${validationId}/details`);
        showValidationDetailsModal(details);
    } catch (error) {
        console.error('Ошибка загрузки деталей:', error);
        Framework.NotificationSystem.show('Ошибка загрузки деталей валидации', 'error');
    }
}

function showValidationDetailsModal(details) {
    const modal = document.getElementById('validation-details-modal');
    const content = document.getElementById('validation-details-content');
    
    // Маппинг названий проверок на русский язык
    const checkNameMap = {
        'face_count': 'Количество лиц',
        'face_pose': 'Поза лица',
        'face_position': 'Позиция лица',
        'image_quality': 'Качество изображения',
        'blurriness': 'Размытость',
        'lighting': 'Освещение',
        'color_mode': 'Цветность',
        'colormode': 'Цветность',
        'background': 'Анализ фона',
        'object_detection': 'Детекция объектов',
        'extraneous_objects': 'Посторонние объекты',
        'accessories': 'Аксессуары',
        'red_eye': 'Красные глаза',
        'real_photo': 'Реальность фото',
        'fileFormat': 'Формат файла',
        'fileSize': 'Размер файла',
        'dimensions': 'Размеры изображения'
    };
    
    if (modal && content) {
        content.innerHTML = `
            <div class="space-y-6">
                <div>
                    <h4 class="text-lg font-medium text-gray-900 mb-2">Основная информация</h4>
                    <dl class="grid grid-cols-1 gap-x-4 gap-y-2 sm:grid-cols-2">
                        <div>
                            <dt class="text-sm font-medium text-gray-500">ID валидации</dt>
                            <dd class="text-sm text-gray-900">${details.id}</dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Имя файла</dt>
                            <dd class="text-sm text-gray-900">${details.filename}</dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Размер файла</dt>
                            <dd class="text-sm text-gray-900">${formatFileSize(details.file_size || 0)}</dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Статус</dt>
                            <dd class="text-sm text-gray-900">${details.status}</dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Время обработки</dt>
                            <dd class="text-sm text-gray-900">${details.processing_time ? details.processing_time.toFixed(2) + 's' : 'N/A'}</dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Дата создания</dt>
                            <dd class="text-sm text-gray-900">${new Date(details.created_at).toLocaleString()}</dd>
                        </div>
                        <div>
                            <dt class="text-sm font-medium text-gray-500">Проверок пройдено</dt>
                            <dd class="text-sm text-gray-900">${details.checks_passed || 0} из ${details.total_checks || 0}</dd>
                        </div>
                    </dl>
                </div>
                
                ${details.check_results && details.check_results.length > 0 ? `
                <div>
                    <h4 class="font-semibold text-gray-900 mb-3">Детали проверок</h4>
                    <div class="space-y-2">
                        ${details.check_results.map(check => {
                            const checkName = checkNameMap[check.check] || check.check || 'Неизвестная проверка';
                            const reason = check.reason || '';
                            const processingTime = check.processing_time || (check.details && check.details.processing_time);
                            
                            return `
                            <div class="flex items-start justify-between p-3 bg-gray-50 rounded-lg">
                                <div class="flex items-start space-x-3">
                                    <div class="h-6 w-6 rounded-full flex items-center justify-center ${
                                        check.status === 'PASSED' ? 'bg-green-100' : 
                                        check.status === 'FAILED' ? 'bg-red-100' : 
                                        check.status === 'NEEDS_REVIEW' ? 'bg-yellow-100' : 'bg-gray-100'
                                    }">
                                        <i data-lucide="${
                                            check.status === 'PASSED' ? 'check' : 
                                            check.status === 'FAILED' ? 'x' : 
                                            check.status === 'NEEDS_REVIEW' ? 'alert-circle' : 'help-circle'
                                        }" class="h-4 w-4 ${
                                            check.status === 'PASSED' ? 'text-green-600' : 
                                            check.status === 'FAILED' ? 'text-red-600' : 
                                            check.status === 'NEEDS_REVIEW' ? 'text-yellow-600' : 'text-gray-600'
                                        }"></i>
                                    </div>
                                    <div class="flex-1 min-w-0">
                                        <p class="text-sm font-medium text-gray-900">${checkName}</p>
                                        <p class="text-xs text-gray-500">${check.check}</p>
                                        ${reason ? `<p class="text-xs text-red-600 mt-1">${reason}</p>` : ''}
                                    </div>
                                </div>
                                <div class="text-right flex-shrink-0">
                                    <p class="text-sm font-medium ${
                                        check.status === 'PASSED' ? 'text-green-600' : 
                                        check.status === 'FAILED' ? 'text-red-600' : 
                                        check.status === 'NEEDS_REVIEW' ? 'text-yellow-600' : 'text-gray-600'
                                    }">${check.status}</p>
                                    ${processingTime ? `<p class="text-xs text-gray-500">${processingTime.toFixed ? processingTime.toFixed(3) + 's' : processingTime}</p>` : ''}
                                </div>
                            </div>
                            `;
                        }).join('')}
                    </div>
                </div>
                ` : ''}
            </div>
        `;
        
        Framework.DOMUtils.removeClass(modal, 'hidden');
        
        // Обновляем иконки
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

function closeValidationDetailsModal() {
    const modal = document.getElementById('validation-details-modal');
    if (modal) {
        Framework.DOMUtils.addClass(modal, 'hidden');
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Инициализация при загрузке DOM
let operationsManager;

document.addEventListener('DOMContentLoaded', function() {
    console.log('operations.js: DOM загружен, инициализация...');
    operationsManager = new OperationsManager();
});

console.log('operations.js загружен'); 