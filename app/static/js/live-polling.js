/**
 * HTMX Live Polling Enhancement
 * Provides smart polling logic and visual feedback for dashboard updates
 */

class LivePollingManager {
    constructor() {
        this.pollingInstances = new Map();
        this.globalSettings = {
            businessHours: { start: 8, end: 22 }, // 8 AM to 10 PM
            idleTimeout: 300000, // 5 minutes in milliseconds
            retryDelay: 5000, // 5 seconds retry on error
            maxRetries: 3
        };
        this.init();
    }

    init() {
        // Set up global event listeners
        this.setupVisibilityDetection();
        this.setupIdleDetection();
        this.setupNetworkStatusMonitoring();
        this.setupGlobalErrorHandling();
        
        // Initialize existing polling components
        this.initializeExistingComponents();
        
        console.log('Live Polling Manager initialized');
    }

    setupVisibilityDetection() {
        // Handle tab visibility changes
        document.addEventListener('visibilitychange', () => {
            const isVisible = !document.hidden;
            this.pollingInstances.forEach((instance, key) => {
                if (isVisible) {
                    instance.resume();
                } else {
                    instance.pause();
                }
            });
        });
    }

    setupIdleDetection() {
        let idleTimer;
        let isActive = true;

        const resetIdleTimer = () => {
            isActive = true;
            this.pollingInstances.forEach((instance) => {
                instance.resume();
            });
        };

        const handleUserActivity = () => {
            clearTimeout(idleTimer);
            resetIdleTimer();
        };

        // Reset timer on user activity
        ['mousedown', 'keypress', 'scroll', 'touchstart', 'click'].forEach(event => {
            document.addEventListener(event, handleUserActivity, true);
        });

        // Set up idle detection
        idleTimer = setTimeout(() => {
            isActive = false;
            this.pollingInstances.forEach((instance) => {
                instance.pause();
            });
        }, this.globalSettings.idleTimeout);
    }

    setupNetworkStatusMonitoring() {
        // Monitor network connectivity
        window.addEventListener('online', () => {
            this.pollingInstances.forEach((instance) => {
                instance.resume();
            });
            this.showNotification('Connection restored', 'success');
        });

        window.addEventListener('offline', () => {
            this.pollingInstances.forEach((instance) => {
                instance.pause();
            });
            this.showNotification('Connection lost', 'error');
        });
    }

    setupGlobalErrorHandling() {
        // Note: HTMX event handlers are now managed by body-class-manager.js
        // to prevent conflicts and ensure consistent body class management
        // Error handling is now delegated to the centralized HTMX event system
    }

    initializeExistingComponents() {
        // Find and initialize existing live poll components
        document.querySelectorAll('[x-data*="livePollManager"]').forEach(element => {
            const xData = element.getAttribute('x-data');
            const match = xData.match(/livePollManager\('([^']+)',\s*(\d+),\s*'([^']+)'\)/);
            
            if (match) {
                const [, endpoint, interval, targetId] = match;
                this.createPollingInstance(element, endpoint, parseInt(interval), targetId);
            }
        });
    }

    createPollingInstance(element, endpoint, interval, targetId) {
        const instance = {
            element,
            endpoint,
            interval: interval * 1000, // Convert to milliseconds
            targetId,
            isPolling: true,
            isPaused: false,
            pollTimer: null,
            lastData: null,
            retryCount: 0,
            
            start() {
                if (this.isPolling && !this.isPaused) {
                    this.scheduleNextPoll();
                }
            },
            
            stop() {
                if (this.pollTimer) {
                    clearTimeout(this.pollTimer);
                    this.pollTimer = null;
                }
            },
            
            pause() {
                this.isPaused = true;
                this.stop();
            },
            
            resume() {
                this.isPaused = false;
                this.start();
            },
            
            scheduleNextPoll() {
                this.stop();
                this.pollTimer = setTimeout(() => {
                    this.makeRequest();
                }, this.interval);
            },
            
            makeRequest() {
                if (!this.isPolling || this.isPaused) return;
                
                // Show loading state
                this.showLoading();
                
                // Use centralized HTMX handling to prevent conflicts
                if (window.bodyClassManager) {
                    window.bodyClassManager.addImmediateClass('htmx-request');
                }
                
                htmx.ajax('GET', this.endpoint, {
                    target: `#${this.targetId}`,
                    swap: 'innerHTML',
                    headers: {
                        'X-Live-Poll': 'true',
                        'X-Requested-With': 'HTMX'
                    }
                }).then(() => {
                    this.hideLoading();
                    if (window.bodyClassManager) {
                        window.bodyClassManager.removeImmediateClass('htmx-request');
                    }
                    this.scheduleNextPoll();
                }).catch((error) => {
                    this.hideLoading();
                    if (window.bodyClassManager) {
                        window.bodyClassManager.removeImmediateClass('htmx-request');
                    }
                    console.error('Polling error:', error);
                    this.scheduleNextPoll(); // Continue polling even on error
                });
            },
            
            showLoading() {
                const loadingIndicator = this.element.querySelector('.htmx-indicator');
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'block';
                }
            },
            
            hideLoading() {
                const loadingIndicator = this.element.querySelector('.htmx-indicator');
                if (loadingIndicator) {
                    loadingIndicator.style.display = 'none';
                }
            }
        };
        
        // Store the instance
        this.pollingInstances.set(targetId, instance);
        
        // Start polling
        instance.start();
    }

    showNotification(message, type = 'info') {
        // Create and show a notification
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transform transition-all duration-300 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            type === 'warning' ? 'bg-yellow-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.innerHTML = `
            <div class="flex items-center">
                <span class="mr-2">
                    ${type === 'success' ? '✅' :
                      type === 'error' ? '❌' :
                      type === 'warning' ? '⚠️' : 'ℹ️'}
                </span>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full', 'opacity-0');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    // Public API for manual control
    pauseAll() {
        this.pollingInstances.forEach((instance) => {
            instance.pause();
        });
    }

    resumeAll() {
        this.pollingInstances.forEach((instance) => {
            instance.resume();
        });
    }

    updateInterval(targetId, newInterval) {
        const instance = this.pollingInstances.get(targetId);
        if (instance) {
            instance.interval = newInterval * 1000;
            if (instance.isPolling && !instance.isPaused) {
                instance.scheduleNextPoll();
            }
        }
    }

    // Add value change animations
    static animateValueChange(element, newValue, oldValue) {
        if (newValue !== oldValue) {
            element.classList.add('value-change');
            if (newValue > oldValue) {
                element.classList.add('value-increase');
                element.classList.remove('value-decrease');
            } else {
                element.classList.add('value-decrease');
                element.classList.remove('value-increase');
            }
            
            // Remove animation classes after 2 seconds
            setTimeout(() => {
                element.classList.remove('value-change', 'value-increase', 'value-decrease');
            }, 2000);
        }
    }

    // Add pulse animation for critical updates
    static addPulseAnimation(element) {
        element.classList.add('critical-update');
        
        // Remove pulse after 5 seconds
        setTimeout(() => {
            element.classList.remove('critical-update');
        }, 5000);
    }
}

// Initialize the live polling manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.livePollingManager = new LivePollingManager();
});

// Add custom CSS animations
const style = document.createElement('style');
style.textContent = `
    .htmx-indicator {
        display: none;
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        background: rgba(59, 130, 246, 0.9);
        color: white;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 14px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .value-change {
        transition: all 0.3s ease-in-out;
        position: relative;
    }

    .value-change::after {
        content: '';
        position: absolute;
        top: -2px;
        right: -2px;
        width: 8px;
        height: 8px;
        background: rgba(59, 130, 246, 0.3);
        border-radius: 50%;
        animation: pulse 1s ease-out;
    }

    @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.2); opacity: 0.7; }
        100% { transform: scale(1); opacity: 1; }
    }

    .value-increase {
        color: #059669;
        font-weight: 600;
    }

    .value-decrease {
        color: #dc2626;
        font-weight: 600;
    }

    .critical-update {
        animation: criticalPulse 2s ease-in-out infinite;
        border: 2px solid #ef4444;
        border-radius: 4px;
    }

    @keyframes criticalPulse {
        0%, 100% { background-color: rgba(239, 68, 68, 0.1); }
        50% { background-color: rgba(239, 68, 68, 0.3); }
    }

    .live-update-highlight {
        animation: liveUpdateGlow 2s ease-in-out;
    }

    @keyframes liveUpdateGlow {
        0% { background-color: transparent; }
        50% { background-color: rgba(59, 130, 246, 0.1); }
        100% { background-color: transparent; }
    }
`;

document.head.appendChild(style);

// Export for global access
window.LivePollingManager = LivePollingManager;