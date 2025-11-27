/**
 * Main Application JavaScript for Restaurant POS
 * Handles global functionality and initialization
 */

// Global app state and utilities
const RestaurantPOS = {
    // Application state
    state: {
        currentUser: null,
        cart: [],
        notifications: [],
        theme: 'light'
    },

    // Initialize the application
    init() {
        console.log('Restaurant POS App initializing...');
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.onDOMReady();
            });
        } else {
            this.onDOMReady();
        }
    },

    // Called when DOM is ready
    onDOMReady() {
        console.log('DOM ready, initializing app components...');
        
        // Initialize components
        this.initializeComponents();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize theme
        this.initializeTheme();
        
        // Initialize offline functionality
        this.initializeOffline();
        
        console.log('Restaurant POS App initialized successfully');
    },

    // Initialize app components
    initializeComponents() {
        // Initialize tooltips
        this.initTooltips();
        
        // Initialize modals
        this.initModals();
        
        // Initialize dropdowns
        this.initDropdowns();
        
        // Initialize form validation
        this.initFormValidation();
    },

    // Setup global event listeners
    setupEventListeners() {
        // Handle online/offline events
        window.addEventListener('online', () => {
            this.showNotification('Connection restored', 'success');
            if (window.offlineManager) {
                window.offlineManager.syncPendingOperations();
            }
        });

        window.addEventListener('offline', () => {
            this.showNotification('Working offline', 'warning');
        });

        // Handle visibility change for sync optimization
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && navigator.onLine) {
                if (window.offlineManager) {
                    window.offlineManager.syncPendingOperations();
                }
            }
        });
    },

    // Initialize theme system
    initializeTheme() {
        // Load saved theme or default to light
        const savedTheme = localStorage.getItem('restaurant-pos-theme') || 'light';
        this.setTheme(savedTheme);
    },

    // Set application theme
    setTheme(theme) {
        document.documentElement.classList.toggle('dark', theme === 'dark');
        localStorage.setItem('restaurant-pos-theme', theme);
        this.state.theme = theme;
    },

    // Initialize offline functionality
    initializeOffline() {
        if (window.offlineManager) {
            console.log('Offline manager available');
        } else {
            console.warn('Offline manager not available');
        }
    },

    // Show notification
    showNotification(message, type = 'info', duration = 5000) {
        const notification = {
            id: Date.now(),
            message,
            type,
            timestamp: new Date()
        };

        // Add to notifications array
        this.state.notifications.push(notification);

        // Dispatch event for Alpine.js to handle
        window.dispatchEvent(new CustomEvent('show-notification', {
            detail: notification
        }));

        // Auto remove after duration
        setTimeout(() => {
            this.removeNotification(notification.id);
        }, duration);
    },

    // Remove notification
    removeNotification(id) {
        this.state.notifications = this.state.notifications.filter(n => n.id !== id);
        
        // Dispatch event for Alpine.js to handle
        window.dispatchEvent(new CustomEvent('remove-notification', {
            detail: { id }
        }));
    },

    // Initialize tooltips
    initTooltips() {
        const tooltipElements = document.querySelectorAll('[data-tooltip]');
        tooltipElements.forEach(element => {
            element.addEventListener('mouseenter', (e) => {
                this.showTooltip(e.target);
            });
            
            element.addEventListener('mouseleave', (e) => {
                this.hideTooltip(e.target);
            });
        });
    },

    // Show tooltip
    showTooltip(element) {
        const text = element.getAttribute('data-tooltip');
        if (!text) return;

        const tooltip = document.createElement('div');
        tooltip.className = 'absolute z-50 px-2 py-1 text-xs text-white bg-gray-800 rounded shadow-lg';
        tooltip.textContent = text;
        tooltip.id = 'tooltip';
        
        document.body.appendChild(tooltip);
        
        const rect = element.getBoundingClientRect();
        tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
        tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;
    },

    // Hide tooltip
    hideTooltip(element) {
        const tooltip = document.getElementById('tooltip');
        if (tooltip) {
            tooltip.remove();
        }
    },

    // Initialize modals
    initModals() {
        const modalTriggers = document.querySelectorAll('[data-modal-target]');
        modalTriggers.forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                const targetId = e.target.getAttribute('data-modal-target');
                this.openModal(targetId);
            });
        });

        const modalCloses = document.querySelectorAll('[data-modal-close]');
        modalCloses.forEach(close => {
            close.addEventListener('click', (e) => {
                const modal = e.target.closest('.modal');
                if (modal) {
                    this.closeModal(modal.id);
                }
            });
        });
    },

    // Open modal
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('flex');
            document.body.style.overflow = 'hidden';
        }
    },

    // Close modal
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('hidden');
            modal.classList.remove('flex');
            document.body.style.overflow = '';
        }
    },

    // Initialize dropdowns
    initDropdowns() {
        const dropdownTriggers = document.querySelectorAll('[data-dropdown-target]');
        dropdownTriggers.forEach(trigger => {
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                const targetId = e.target.getAttribute('data-dropdown-target');
                this.toggleDropdown(targetId);
            });
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', () => {
            const dropdowns = document.querySelectorAll('.dropdown');
            dropdowns.forEach(dropdown => {
                dropdown.classList.add('hidden');
            });
        });
    },

    // Toggle dropdown
    toggleDropdown(dropdownId) {
        const dropdown = document.getElementById(dropdownId);
        if (dropdown) {
            dropdown.classList.toggle('hidden');
        }
    },

    // Initialize form validation
    initFormValidation() {
        const forms = document.querySelectorAll('[data-validate]');
        forms.forEach(form => {
            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                }
            });
        });
    },

    // Validate form
    validateForm(form) {
        let isValid = true;
        const requiredFields = form.querySelectorAll('[required]');
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                this.showFieldError(field, 'This field is required');
                isValid = false;
            } else {
                this.clearFieldError(field);
            }
        });

        return isValid;
    },

    // Show field error
    showFieldError(field, message) {
        field.classList.add('border-red-500');
        
        let errorElement = field.parentNode.querySelector('.field-error');
        if (!errorElement) {
            errorElement = document.createElement('span');
            errorElement.className = 'field-error text-red-500 text-sm mt-1';
            field.parentNode.appendChild(errorElement);
        }
        
        errorElement.textContent = message;
    },

    // Clear field error
    clearFieldError(field) {
        field.classList.remove('border-red-500');
        
        const errorElement = field.parentNode.querySelector('.field-error');
        if (errorElement) {
            errorElement.remove();
        }
    },

    // Format currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    },

    // Format date
    formatDate(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        };
        
        return new Intl.DateTimeFormat('en-US', { ...defaultOptions, ...options }).format(new Date(date));
    },

    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle function
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Initialize app when DOM is ready
RestaurantPOS.init();

// Make app available globally
window.RestaurantPOS = RestaurantPOS;

// Handle Alpine.js initialization
document.addEventListener('alpine:init', () => {
    console.log('Alpine.js initialized');
    
    // Add Alpine data if needed
    Alpine.data('app', () => ({
        // Global app data for Alpine.js
        notifications: RestaurantPOS.state.notifications,
        
        showNotification(message, type = 'info') {
            RestaurantPOS.showNotification(message, type);
        },
        
        removeNotification(id) {
            RestaurantPOS.removeNotification(id);
        }
    }));
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RestaurantPOS;
}