/**
 * Enhanced Body Class Manager for Restaurant POS
 * Centralized management of body element classes to prevent flickering
 * during HTMX requests and other dynamic class changes
 */

class BodyClassManager {
    constructor() {
        this.pendingClasses = new Set();
        this.currentClasses = new Set();
        this.debounceTimer = null;
        this.htmxRequestActive = false;
        this.htmxSending = false;
        this.classUpdateQueue = [];
        this.isProcessingQueue = false;
        this.init();
    }

    init() {
        // Initialize with current body classes
        this.currentClasses = new Set(document.body.className.split(' ').filter(c => c));
        
        // Listen for HTMX events
        this.setupHtmxListeners();
        
        // Listen for auth events
        this.setupAuthListeners();
        
        // Listen for theme events
        this.setupThemeListeners();
        
        // Listen for accessibility events
        this.setupAccessibilityListeners();
        
        // Listen for device detection events
        this.setupDeviceListeners();
        
        console.log('Enhanced Body Class Manager initialized');
    }

    setupHtmxListeners() {
        // Comprehensive HTMX event handling with proper coordination
        document.body.addEventListener('htmx:beforeRequest', (event) => {
            this.htmxRequestActive = true;
            // Add htmx-request class immediately without debouncing
            this.addImmediateClass('htmx-request');
        });

        document.body.addEventListener('htmx:afterRequest', (event) => {
            this.htmxRequestActive = false;
            // Remove htmx-request class immediately without debouncing
            this.removeImmediateClass('htmx-request');
        });

        document.body.addEventListener('htmx:responseError', (event) => {
            this.htmxRequestActive = false;
            // Remove htmx-request class immediately without debouncing
            this.removeImmediateClass('htmx-request');
        });

        // Handle sending state
        document.body.addEventListener('htmx:beforeSend', () => {
            this.htmxSending = true;
            this.addImmediateClass('htmx-sending');
        });

        document.body.addEventListener('htmx:sendError', () => {
            this.htmxSending = false;
            this.removeImmediateClass('htmx-sending');
        });

        document.body.addEventListener('htmx:settle', () => {
            this.htmxSending = false;
            this.removeImmediateClass('htmx-sending');
        });

        // Additional coordination events
        document.body.addEventListener('htmx:beforeSwap', () => {
            // Prevent class changes during DOM swapping
            this.htmxRequestActive = true;
        });

        document.body.addEventListener('htmx:afterSwap', () => {
            // Allow class changes after DOM swapping is complete
            this.htmxRequestActive = false;
        });

        // Handle request configuration
        document.body.addEventListener('htmx:configRequest', (event) => {
            // Add custom headers to identify HTMX requests
            event.detail.headers['X-HTMX-Body-Class-Managed'] = 'true';
        });
    }

    setupAuthListeners() {
        window.addEventListener('user-authenticated', () => {
            this.addClass('user-authenticated');
            this.removeClass('user-not-authenticated');
        });

        window.addEventListener('user-not-authenticated', () => {
            this.addClass('user-not-authenticated');
            this.removeClass('user-authenticated');
        });
    }

    setupThemeListeners() {
        window.addEventListener('themeChanged', (event) => {
            const { theme } = event.detail;
            this.updateThemeClasses(theme);
        });
    }

    setupAccessibilityListeners() {
        window.addEventListener('accessibility-toggled', (event) => {
            const { classes } = event.detail;
            this.toggleAccessibilityClasses(classes);
        });
    }

    setupDeviceListeners() {
        window.addEventListener('device-detected', (event) => {
            const { device } = event.detail;
            this.updateDeviceClasses(device);
        });
    }

    addClass(className) {
        if (!this.pendingClasses.has(className)) {
            this.pendingClasses.add(className);
            this.scheduleUpdate();
        }
    }

    removeClass(className) {
        if (this.pendingClasses.has(className)) {
            this.pendingClasses.delete(className);
        } else if (this.currentClasses.has(className)) {
            // Queue for removal if it's in current classes
            this.classUpdateQueue.push({ action: 'remove', class: className });
            this.scheduleUpdate();
        }
    }

    toggleClass(className) {
        if (this.pendingClasses.has(className) || this.currentClasses.has(className)) {
            this.removeClass(className);
        } else {
            this.addClass(className);
        }
    }

    updateThemeClasses(themeName) {
        // Remove all existing theme classes
        this.currentClasses.forEach(cls => {
            if (cls.startsWith('theme-')) {
                this.removeClass(cls);
            }
        });
        
        // Add new theme class
        this.addClass(`theme-${themeName}`);
        this.scheduleUpdate();
    }

    toggleAccessibilityClasses(classes) {
        classes.forEach(cls => {
            this.toggleClass(cls);
        });
        this.scheduleUpdate();
    }

    updateDeviceClasses(device) {
        if (device.isTouch) {
            this.addClass('touch-device');
        } else {
            this.removeClass('touch-device');
        }
        this.scheduleUpdate();
    }

    scheduleUpdate() {
        // Clear existing timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        // Schedule update with optimized delay to prevent flickering
        this.debounceTimer = setTimeout(() => {
            this.processUpdateQueue();
            this.applyChanges();
        }, 16); // ~1 frame at 60fps
    }

    processUpdateQueue() {
        if (this.isProcessingQueue || this.classUpdateQueue.length === 0) return;
        
        this.isProcessingQueue = true;
        
        // Process queued updates
        this.classUpdateQueue.forEach(update => {
            if (update.action === 'remove') {
                this.pendingClasses.delete(update.class);
            } else if (update.action === 'add') {
                this.pendingClasses.add(update.class);
            }
        });
        
        // Clear queue
        this.classUpdateQueue = [];
        this.isProcessingQueue = false;
    }

    // Immediate class updates for critical changes (like HTMX events)
    addImmediateClass(className) {
        this.currentClasses.add(className);
        // Apply immediately without transition to prevent flickering
        this.applyClassesToDOMImmediate(this.currentClasses);
    }

    removeImmediateClass(className) {
        this.currentClasses.delete(className);
        // Apply immediately without transition to prevent flickering
        this.applyClassesToDOMImmediate(this.currentClasses);
    }

    applyClassesToDOMImmediate(classes) {
        // Apply classes immediately without any transitions
        const classString = Array.from(classes).join(' ').trim();
        document.body.className = classString;
    }

    applyChanges() {
        // Calculate final classes
        const finalClasses = new Set(this.currentClasses);
        
        // Apply pending changes
        this.pendingClasses.forEach(cls => {
            finalClasses.add(cls);
        });

        // Apply to DOM with appropriate transition handling
        this.applyClassesToDOM(finalClasses);
        
        // Update current state
        this.currentClasses = finalClasses;
        this.pendingClasses.clear();
    }

    applyClassesToDOM(classes) {
        const classString = Array.from(classes).join(' ').trim();
        
        // Only add transitions if not during HTMX requests
        if (!this.htmxRequestActive && !this.htmxSending) {
            // Add transition class for smooth changes
            document.body.classList.add('class-transitioning');
            
            // Apply classes
            document.body.className = classString;
            
            // Remove transition class after animation
            setTimeout(() => {
                document.body.classList.remove('class-transitioning');
            }, 300);
        } else {
            // During HTMX requests, apply immediately without transitions
            document.body.className = classString;
        }
    }

    // Public API for other scripts
    addClasses(classNames) {
        classNames.forEach(cls => this.addClass(cls));
    }

    removeClasses(classNames) {
        classNames.forEach(cls => this.removeClass(cls));
    }

    hasClass(className) {
        return this.currentClasses.has(className) || this.pendingClasses.has(className);
    }

    // Force immediate update (for critical changes)
    forceUpdate() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        this.processUpdateQueue();
        this.applyChanges();
    }

    // Get current state
    getCurrentClasses() {
        return Array.from(this.currentClasses);
    }

    getPendingClasses() {
        return Array.from(this.pendingClasses);
    }

    // Debug method to log current state
    logState() {
        console.log('Body Class Manager State:', {
            current: Array.from(this.currentClasses),
            pending: Array.from(this.pendingClasses),
            htmxRequestActive: this.htmxRequestActive,
            htmxSending: this.htmxSending
        });
    }
}

// Initialize and make globally available
let bodyClassManager;

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        bodyClassManager = new BodyClassManager();
        window.bodyClassManager = bodyClassManager;
        window.BodyClassManager = BodyClassManager;
    });
} else {
    bodyClassManager = new BodyClassManager();
    window.bodyClassManager = bodyClassManager;
    window.BodyClassManager = BodyClassManager;
}