/**
 * Легковесный фреймворк для управления состоянием и компонентами
 */

// Система событий
class EventEmitter {
    constructor() {
        this.events = {};
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }

    off(event, callback) {
        if (!this.events[event]) return;
        this.events[event] = this.events[event].filter(cb => cb !== callback);
    }

    emit(event, data) {
        if (!this.events[event]) return;
        this.events[event].forEach(callback => callback(data));
    }
}

// Управление состоянием
class StateManager extends EventEmitter {
    constructor(initialState = {}) {
        super();
        this.state = { ...initialState };
    }

    setState(updates) {
        const prevState = { ...this.state };
        this.state = { ...this.state, ...updates };
        this.emit('stateChange', { prevState, newState: this.state, updates });
    }

    getState() {
        return { ...this.state };
    }

    subscribe(callback) {
        this.on('stateChange', callback);
        return () => this.off('stateChange', callback);
    }
}

// Базовый компонент
class Component extends EventEmitter {
    constructor(element, options = {}) {
        super();
        this.element = typeof element === 'string' ? document.querySelector(element) : element;
        this.options = options;
        this.state = new StateManager(options.initialState || {});
        this.mounted = false;
        
        if (this.element) {
            this.mount();
        }
    }

    mount() {
        if (this.mounted) return;
        this.mounted = true;
        this.bindEvents();
        this.render();
        this.emit('mounted');
    }

    unmount() {
        if (!this.mounted) return;
        this.mounted = false;
        this.unbindEvents();
        this.emit('unmounted');
    }

    bindEvents() {
        // Переопределяется в дочерних классах
    }

    unbindEvents() {
        // Переопределяется в дочерних классах
    }

    render() {
        // Переопределяется в дочерних классах
    }

    setState(updates) {
        this.state.setState(updates);
    }

    getState() {
        return this.state.getState();
    }
}

// Утилиты для работы с DOM
class DOMUtils {
    static createElement(tag, attributes = {}, children = []) {
        const element = document.createElement(tag);
        
        Object.keys(attributes).forEach(key => {
            if (key === 'className') {
                element.className = attributes[key];
            } else if (key === 'innerHTML') {
                element.innerHTML = attributes[key];
            } else if (key.startsWith('data-')) {
                element.setAttribute(key, attributes[key]);
            } else {
                element[key] = attributes[key];
            }
        });

        children.forEach(child => {
            if (typeof child === 'string') {
                element.appendChild(document.createTextNode(child));
            } else if (child instanceof Node) {
                element.appendChild(child);
            }
        });

        return element;
    }

    static show(element) {
        if (element) element.style.display = 'block';
    }

    static hide(element) {
        if (element) element.style.display = 'none';
    }

    static toggle(element) {
        if (!element) return;
        element.style.display = element.style.display === 'none' ? 'block' : 'none';
    }

    static addClass(element, className) {
        if (element) element.classList.add(className);
    }

    static removeClass(element, className) {
        if (element) element.classList.remove(className);
    }

    static toggleClass(element, className) {
        if (element) element.classList.toggle(className);
    }
}

// HTTP клиент
class HttpClient {
    static async request(url, options = {}) {
        const config = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('HTTP Request failed:', error);
            throw error;
        }
    }

    static get(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    }

    static post(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static put(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static delete(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }
}

// Система уведомлений
class NotificationSystem {
    constructor() {
        this.container = null;
        this.notifications = [];
        this.init();
    }

    init() {
        this.container = DOMUtils.createElement('div', {
            id: 'notification-container',
            className: 'fixed top-4 right-4 z-50 space-y-2'
        });
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 5000) {
        const notification = this.createNotification(message, type);
        this.container.appendChild(notification);
        this.notifications.push(notification);

        // Автоматическое удаление
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }

        return notification;
    }

    createNotification(message, type) {
        const typeClasses = {
            success: 'bg-green-500 text-white',
            error: 'bg-red-500 text-white',
            warning: 'bg-yellow-500 text-black',
            info: 'bg-blue-500 text-white'
        };

        const typeIcons = {
            success: 'check-circle',
            error: 'alert-circle',
            warning: 'alert-triangle',
            info: 'info'
        };

        const notification = DOMUtils.createElement('div', {
            className: `notification p-4 rounded-lg shadow-lg ${typeClasses[type] || typeClasses.info} flex items-center space-x-2 min-w-80`,
            innerHTML: `
                <i data-lucide="${typeIcons[type] || typeIcons.info}" class="h-5 w-5"></i>
                <span class="flex-1">${message}</span>
                <button class="close-btn text-white hover:text-gray-200">
                    <i data-lucide="x" class="h-4 w-4"></i>
                </button>
            `
        });

        // Обработчик закрытия
        const closeBtn = notification.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => {
            this.remove(notification);
        });

        // Обновляем иконки
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        return notification;
    }

    remove(notification) {
        if (notification && notification.parentNode) {
            notification.parentNode.removeChild(notification);
            this.notifications = this.notifications.filter(n => n !== notification);
        }
    }

    clear() {
        this.notifications.forEach(notification => {
            this.remove(notification);
        });
    }
}

// Глобальные экземпляры
window.Framework = {
    EventEmitter,
    StateManager,
    Component,
    DOMUtils,
    HttpClient,
    NotificationSystem: new NotificationSystem()
};

console.log('Framework.js загружен'); 