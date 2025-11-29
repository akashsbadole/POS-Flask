/**
 * Push Notification Manager for PWA
 * Handles subscription, management, and display of push notifications
 */
class PushNotificationManager {
    constructor() {
        this.subscription = null;
        this.isSupported = 'PushManager' in window && 'Notification' in window;
        this.permission = 'default';
        this.vapidPublicKey = 'BLjWZ1K8KXqC9JgQm8VhLzX7Y2R5tP9nF3W6sA4dE7gH0jK3lM6oP9qR2tU5wX8z';
        this.notificationQueue = [];
        this.isProcessingQueue = false;
        
        // Notification categories
        this.categories = {
            order: {
                title: 'Restaurant POS',
                icon: '/static/images/order-icon.png',
                requireInteraction: true,
                actions: [
                    { action: 'view', title: 'View Order' },
                    { action: 'accept', title: 'Accept' }
                ]
            },
            inventory: {
                title: 'Inventory Alert',
                icon: '/static/images/inventory-icon.png',
                requireInteraction: true,
                actions: [
                    { action: 'view', title: 'View Inventory' },
                    { action: 'reorder', title: 'Reorder' }
                ]
            },
            payment: {
                title: 'Payment Received',
                icon: '/static/images/payment-icon.png',
                requireInteraction: false
            },
            sync: {
                title: 'Sync Complete',
                icon: '/static/images/sync-icon.png',
                requireInteraction: false,
                silent: true
            },
            system: {
                title: 'System Notification',
                icon: '/static/images/icon-192x192.png',
                requireInteraction: false
            }
        };
        
        this.init();
    }
    
    async init() {
        try {
            console.log('Push Notification Manager: Initializing...');
            
            // Check support
            if (!this.isSupported) {
                console.warn('Push Notification Manager: Push notifications not supported');
                return;
            }
            
            // Get current permission
            this.permission = await Notification.requestPermission();
            
            // Setup service worker
            await this.setupServiceWorker();
            
            // Load existing subscription
            await this.loadSubscription();
            
            // Setup notification handlers
            this.setupNotificationHandlers();
            
            // Setup periodic subscription check
            this.setupPeriodicCheck();
            
            console.log('Push Notification Manager: Initialized successfully');
        } catch (error) {
            console.error('Push Notification Manager: Initialization failed', error);
        }
    }
    
    async setupServiceWorker() {
        if ('serviceWorker' in navigator) {
            const registration = await navigator.serviceWorker.ready;
            this.registration = registration;
            
            // Check if service worker is active
            if (registration.active) {
                console.log('Push Notification Manager: Service worker is active');
            } else {
                console.warn('Push Notification Manager: Service worker not active');
            }
        }
    }
    
    async requestPermission() {
        if (!this.isSupported) {
            return false;
        }
        
        try {
            const permission = await Notification.requestPermission();
            this.permission = permission;
            
            if (permission === 'granted') {
                console.log('Push Notification Manager: Permission granted');
                await this.subscribeToPush();
                return true;
            } else if (permission === 'denied') {
                console.log('Push Notification Manager: Permission denied');
                this.showPermissionDeniedMessage();
                return false;
            } else {
                console.log('Push Notification Manager: Permission dismissed');
                return false;
            }
        } catch (error) {
            console.error('Push Notification Manager: Failed to request permission', error);
            return false;
        }
    }
    
    async subscribeToPush() {
        if (!this.registration || this.permission !== 'granted') {
            return;
        }
        
        try {
            // Check existing subscription
            const existingSubscription = await this.registration.pushManager.getSubscription();
            if (existingSubscription) {
                this.subscription = existingSubscription;
                console.log('Push Notification Manager: Using existing subscription');
                return;
            }
            
            // Create new subscription
            const subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });
            
            this.subscription = subscription;
            
            // Send subscription to server
            await this.sendSubscriptionToServer(subscription);
            
            console.log('Push Notification Manager: Subscribed successfully');
            
            // Show success message
            this.showSuccessMessage('Notifications enabled! You\'ll receive updates even when the app is closed.');
            
        } catch (error) {
            console.error('Push Notification Manager: Failed to subscribe', error);
            this.showErrorMessage('Failed to enable notifications. Please try again.');
        }
    }
    
    async unsubscribeFromPush() {
        if (!this.subscription) {
            return;
        }
        
        try {
            await this.subscription.unsubscribe();
            this.subscription = null;
            
            // Remove from server
            await this.removeSubscriptionFromServer();
            
            console.log('Push Notification Manager: Unsubscribed successfully');
            this.showSuccessMessage('Notifications disabled. You won\'t receive push updates.');
            
        } catch (error) {
            console.error('Push Notification Manager: Failed to unsubscribe', error);
            this.showErrorMessage('Failed to disable notifications. Please try again.');
        }
    }
    
    async sendSubscriptionToServer(subscription) {
        try {
            const response = await fetch('/api/push/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    subscription: subscription.toJSON(),
                    user_agent: navigator.userAgent,
                    platform: this.getPlatform()
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }
            
            console.log('Push Notification Manager: Subscription sent to server');
        } catch (error) {
            console.error('Push Notification Manager: Failed to send subscription to server', error);
        }
    }
    
    async removeSubscriptionFromServer() {
        try {
            const response = await fetch('/api/push/unsubscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    subscription: this.subscription.toJSON()
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }
            
            console.log('Push Notification Manager: Subscription removed from server');
        } catch (error) {
            console.error('Push Notification Manager: Failed to remove subscription from server', error);
        }
    }
    
    async loadSubscription() {
        try {
            const response = await fetch('/api/push/subscription');
            if (response.ok) {
                const data = await response.json();
                if (data.subscription) {
                    // Validate subscription is still valid
                    const isValid = await this.validateSubscription(data.subscription);
                    if (isValid) {
                        this.subscription = data.subscription;
                        console.log('Push Notification Manager: Loaded existing subscription');
                    } else {
                        console.log('Push Notification Manager: Existing subscription invalid, creating new one');
                        await this.subscribeToPush();
                    }
                }
            }
        } catch (error) {
            console.warn('Push Notification Manager: Failed to load subscription', error);
        }
    }
    
    async validateSubscription(subscription) {
        try {
            // Try to get subscription info from push manager
            const existingSubscription = await this.registration.pushManager.getSubscription();
            return existingSubscription && existingSubscription.endpoint === subscription.endpoint;
        } catch (error) {
            console.warn('Push Notification Manager: Failed to validate subscription', error);
            return false;
        }
    }
    
    setupNotificationHandlers() {
        // Handle notification clicks
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data && event.data.type === 'NOTIFICATION_CLICK') {
                    this.handleNotificationClick(event.data.data);
                }
            });
        }
        
        // Handle notification close
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data && event.data.type === 'NOTIFICATION_CLOSE') {
                    this.handleNotificationClose(event.data.data);
                }
            });
        }
    }
    
    handleNotificationClick(data) {
        console.log('Push Notification Manager: Notification clicked', data);
        
        // Track analytics
        this.trackNotificationEvent('click', data);
        
        // Handle based on action
        switch (data.action) {
            case 'view':
            case 'view-order':
                this.navigateTo('/orders');
                break;
            case 'view-inventory':
                this.navigateTo('/inventory');
                break;
            case 'accept':
                this.handleOrderAction(data.orderId, 'accept');
                break;
            case 'reorder':
                this.navigateTo('/inventory/reorder');
                break;
            default:
                this.navigateTo('/');
                break;
        }
    }
    
    handleNotificationClose(data) {
        console.log('Push Notification Manager: Notification closed', data);
        
        // Track analytics
        this.trackNotificationEvent('close', data);
    }
    
    async handleOrderAction(orderId, action) {
        try {
            const response = await fetch(`/api/orders/${orderId}/${action}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                this.navigateTo('/orders');
            } else {
                this.showErrorMessage('Failed to process order action');
            }
        } catch (error) {
            console.error('Push Notification Manager: Failed to handle order action', error);
            this.showErrorMessage('Failed to process order action');
        }
    }
    
    navigateTo(path) {
        // Navigate to specific path
        window.location.href = path;
    }
    
    async trackNotificationEvent(event, data) {
        try {
            const response = await fetch('/api/analytics/notification', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    event: event,
                    notification_id: data.notificationId,
                    action: data.action,
                    timestamp: Date.now()
                })
            });
        } catch (error) {
            console.warn('Push Notification Manager: Failed to track notification event', error);
        }
    }
    
    setupPeriodicCheck() {
        // Check subscription validity every hour
        setInterval(async () => {
            if (this.subscription) {
                const isValid = await this.validateSubscription(this.subscription);
                if (!isValid) {
                    console.log('Push Notification Manager: Subscription invalid, renewing...');
                    await this.subscribeToPush();
                }
            }
        }, 60 * 60 * 1000); // 1 hour
    }
    
    showSuccessMessage(message) {
        this.showToast(message, 'success');
    }
    
    showErrorMessage(message) {
        this.showToast(message, 'error');
    }
    
    showPermissionDeniedMessage() {
        this.showToast('Notifications are blocked. Please enable them in your browser settings.', 'warning', 10000);
    }
    
    showToast(message, type = 'info', duration = 5000) {
        // Create toast notification
        const toast = document.createElement('div');
        toast.className = `fixed top-4 right-4 z-50 max-w-sm transform translate-x-full transition-transform duration-300 ease-out`;
        
        const bgColor = type === 'success' ? 'bg-green-500' : 
                       type === 'error' ? 'bg-red-500' : 
                       type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';
        
        toast.innerHTML = `
            <div class="${bgColor} text-white px-6 py-4 rounded-lg shadow-lg flex items-center space-x-3">
                <div class="flex-shrink-0">
                    ${this.getToastIcon(type)}
                </div>
                <div class="flex-1">
                    <p class="text-sm font-medium">${message}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="flex-shrink-0 text-white hover:bg-white hover:bg-opacity-20 rounded-full p-1 transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.classList.remove('translate-x-full');
        }, 100);
        
        // Auto-remove
        setTimeout(() => {
            if (toast.parentElement) {
                toast.classList.add('translate-x-full');
                setTimeout(() => {
                    if (toast.parentElement) {
                        toast.remove();
                    }
                }, 300);
            }
        }, duration);
    }
    
    getToastIcon(type) {
        const icons = {
            success: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>',
            error: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>',
            warning: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path></svg>',
            info: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h1m1-4h1M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>'
        };
        
        return icons[type] || icons.info;
    }
    
    getPlatform() {
        const userAgent = navigator.userAgent.toLowerCase();
        
        if (userAgent.includes('android')) {
            return 'android';
        } else if (userAgent.includes('iphone') || userAgent.includes('ipad')) {
            return 'ios';
        } else if (userAgent.includes('windows')) {
            return 'windows';
        } else if (userAgent.includes('mac')) {
            return 'macos';
        } else {
            return 'web';
        }
    }
    
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        
        return outputArray;
    }
    
    // Public methods
    async enableNotifications() {
        if (this.permission === 'granted') {
            this.showSuccessMessage('Notifications are already enabled!');
            return true;
        }
        
        return await this.requestPermission();
    }
    
    async disableNotifications() {
        await this.unsubscribeFromPush();
    }
    
    async toggleNotifications() {
        if (this.subscription) {
            await this.disableNotifications();
        } else {
            await this.enableNotifications();
        }
    }
    
    getStatus() {
        return {
            supported: this.isSupported,
            permission: this.permission,
            subscribed: !!this.subscription,
            subscription: this.subscription ? this.subscription.toJSON() : null
        };
    }
    
    // Queue management for offline scenarios
    queueNotification(notification) {
        this.notificationQueue.push(notification);
        this.processQueue();
    }
    
    async processQueue() {
        if (this.isProcessingQueue || this.notificationQueue.length === 0) {
            return;
        }
        
        this.isProcessingQueue = true;
        
        while (this.notificationQueue.length > 0) {
            const notification = this.notificationQueue.shift();
            
            try {
                await this.showNotification(notification);
            } catch (error) {
                console.error('Push Notification Manager: Failed to show queued notification', error);
            }
        }
        
        this.isProcessingQueue = false;
    }
    
    async showNotification(notification) {
        if (!('Notification' in window) || Notification.permission !== 'granted') {
            return;
        }
        
        const category = this.categories[notification.category] || this.categories.system;
        
        const notificationOptions = {
            title: notification.title || category.title,
            body: notification.body,
            icon: category.icon,
            badge: '/static/images/badge.png',
            tag: notification.id || `notification-${Date.now()}`,
            requireInteraction: category.requireInteraction,
            silent: category.silent || false,
            data: {
                ...notification.data,
                category: notification.category,
                timestamp: Date.now()
            }
        };
        
        // Add actions if specified
        if (category.actions) {
            notificationOptions.actions = category.actions;
        }
        
        // Create notification
        const notificationInstance = new Notification(notificationOptions.title, notificationOptions);
        
        // Handle click
        notificationInstance.onclick = () => {
            this.handleNotificationClick({
                ...notification.data,
                action: 'view'
            });
            notificationInstance.close();
        };
        
        // Handle close
        notificationInstance.onclose = () => {
            this.handleNotificationClose({
                ...notification.data,
                action: 'dismiss'
            });
        };
        
        return notificationInstance;
    }
}

// Initialize push notification manager
window.pushNotificationManager = null;

document.addEventListener('DOMContentLoaded', async () => {
    window.pushNotificationManager = new PushNotificationManager();
    
    // Expose global functions for UI integration
    window.enablePushNotifications = () => window.pushNotificationManager.enableNotifications();
    window.disablePushNotifications = () => window.pushNotificationManager.disableNotifications();
    window.togglePushNotifications = () => window.pushNotificationManager.toggleNotifications();
    window.getPushNotificationStatus = () => window.pushNotificationManager.getStatus();
});

// Handle service worker messages for notifications
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
        if (event.data && event.data.type === 'PUSH_NOTIFICATION') {
            if (window.pushNotificationManager) {
                window.pushNotificationManager.showNotification(event.data.notification);
            }
        }
    });
}