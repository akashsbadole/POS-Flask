/**
 * Socket.IO Manager for Kitchen Real-time Updates
 * Handles WebSocket connections and event management for kitchen operations
 */

class SocketManager {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.heartbeatInterval = null;
        this.eventHandlers = {};
        
        // Initialize Socket.IO connection
        this.init();
    }
    
    init() {
        try {
            // Connect to Socket.IO server
            this.socket = io({
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: true,
                timeout: 20000,
                forceNew: false
            });
            
            // Set up event listeners
            this.setupEventListeners();
            
            console.log('Socket.IO manager initialized');
        } catch (error) {
            console.error('Failed to initialize Socket.IO:', error);
            this.handleConnectionError(error);
        }
    }
    
    setupEventListeners() {
        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to Socket.IO server');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            // Join kitchen room if on kitchen page
            if (window.location.pathname.includes('/kitchen')) {
                this.joinKitchen();
            }
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Trigger custom event
            this.triggerCustomEvent('socket:connected');
        });
        
        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from Socket.IO server:', reason);
            this.isConnected = false;
            this.stopHeartbeat();
            
            // Trigger custom event
            this.triggerCustomEvent('socket:disconnected', { reason });
            
            // Attempt to reconnect if not intentional
            if (reason !== 'io client disconnect') {
                this.attemptReconnect();
            }
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
            this.handleConnectionError(error);
        });
        
        this.socket.on('reconnect', (attemptNumber) => {
            console.log(`Reconnected to Socket.IO server after ${attemptNumber} attempts`);
            this.isConnected = true;
            this.reconnectAttempts = 0;
            
            // Re-join kitchen room if needed
            if (window.location.pathname.includes('/kitchen')) {
                this.joinKitchen();
            }
            
            // Trigger custom event
            this.triggerCustomEvent('socket:reconnected', { attemptNumber });
        });
        
        this.socket.on('reconnect_error', (error) => {
            console.error('Socket.IO reconnection error:', error);
        });
        
        this.socket.on('reconnect_failed', () => {
            console.error('Failed to reconnect to Socket.IO server after maximum attempts');
            this.triggerCustomEvent('socket:reconnect_failed');
        });
        
        // Kitchen-specific events
        this.socket.on('new_order', (data) => {
            console.log('New order received:', data);
            this.triggerCustomEvent('kitchen:new_order', data);
            this.showNotification(`New Order ${data.order.order_number}`, data.message, 'info');
        });
        
        this.socket.on('order_status_update', (data) => {
            console.log('Order status updated:', data);
            this.triggerCustomEvent('kitchen:order_status_update', data);
            this.showNotification(`Order ${data.order.order_number}`, data.message, 'success');
        });
        
        this.socket.on('kitchen_stats', (data) => {
            console.log('Kitchen stats updated:', data);
            this.triggerCustomEvent('kitchen:stats_update', data);
        });
        
        this.socket.on('kitchen_ticket', (data) => {
            console.log('Kitchen ticket updated:', data);
            this.triggerCustomEvent('kitchen:ticket_update', data);
            this.showNotification(`Kitchen Ticket`, data.message, 'info');
        });
        
        this.socket.on('order_assigned', (data) => {
            console.log('Order assigned:', data);
            this.triggerCustomEvent('kitchen:order_assigned', data);
            this.showNotification(`Order Assigned`, data.message, 'info');
        });
        
        this.socket.on('kitchen_orders', (data) => {
            console.log('Kitchen orders received:', data);
            this.triggerCustomEvent('kitchen:orders_received', data);
        });
        
        this.socket.on('order_details', (data) => {
            console.log('Order details received:', data);
            this.triggerCustomEvent('kitchen:order_details', data);
        });
        
        this.socket.on('kitchen_heartbeat_response', (data) => {
            console.log('Heartbeat response:', data);
            this.triggerCustomEvent('kitchen:heartbeat', data);
        });
        
        // Timer events
        this.socket.on('timer_update', (data) => {
            console.log('Timer update:', data);
            this.triggerCustomEvent('kitchen:timer_update', data);
            this.showNotification(`Timer ${data.action}`, data.message, 'info');
        });
        
        this.socket.on('timer_completed', (data) => {
            console.log('Timer completed:', data);
            this.triggerCustomEvent('kitchen:timer_completed', data);
            this.showNotification('Timer Completed', data.message, 'success');
            
            // Play completion sound
            this.playTimerSound('complete');
        });
        
        this.socket.on('status', (data) => {
            console.log('Status message:', data.msg);
            this.triggerCustomEvent('socket:status', data);
        });
        
        this.socket.on('error', (data) => {
            console.error('Socket.IO error:', data.msg);
            this.triggerCustomEvent('socket:error', data);
            this.showNotification('Error', data.msg, 'error');
        });
    }
    
    handleConnectionError(error) {
        this.triggerCustomEvent('socket:connection_error', error);
        this.showNotification('Connection Error', 'Failed to connect to real-time updates', 'error');
    }
    
    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            
            setTimeout(() => {
                this.socket.connect();
            }, this.reconnectDelay);
            
            // Exponential backoff
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
        } else {
            console.error('Maximum reconnection attempts reached');
            this.showNotification('Connection Lost', 'Unable to reconnect to real-time updates', 'error');
        }
    }
    
    startHeartbeat() {
        // Send heartbeat every 30 seconds to keep connection alive
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected && window.location.pathname.includes('/kitchen')) {
                this.socket.emit('kitchen_heartbeat');
            }
        }, 30000);
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    // Public methods
    joinKitchen() {
        if (this.isConnected) {
            this.socket.emit('join_kitchen');
            console.log('Joined kitchen room');
        }
    }
    
    leaveKitchen() {
        if (this.isConnected) {
            this.socket.emit('leave_kitchen');
            console.log('Left kitchen room');
        }
    }
    
    requestKitchenOrders() {
        if (this.isConnected) {
            this.socket.emit('request_kitchen_orders');
        }
    }
    
    requestOrderDetails(orderId) {
        if (this.isConnected) {
            this.socket.emit('request_order_details', { order_id: orderId });
        }
    }
    
    // Timer management methods
    startTimer(orderId) {
        if (this.isConnected) {
            this.socket.emit('timer_start', { order_id: orderId });
        }
    }
    
    adjustTimer(orderId, adjustment) {
        if (this.isConnected) {
            this.socket.emit('timer_adjust', {
                order_id: orderId,
                adjustment: adjustment
            });
        }
    }
    
    completeTimer(orderId) {
        if (this.isConnected) {
            this.socket.emit('timer_complete', { order_id: orderId });
        }
    }
    
    playTimerSound(type) {
        // Create audio context for timer sounds
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Different frequencies for different timer events
            switch (type) {
                case 'warning':
                    oscillator.frequency.value = 800;
                    gainNode.gain.value = 0.1;
                    break;
                case 'critical':
                    oscillator.frequency.value = 1200;
                    gainNode.gain.value = 0.2;
                    break;
                case 'complete':
                    oscillator.frequency.value = 600;
                    gainNode.gain.value = 0.15;
                    break;
            }
            
            oscillator.start();
            oscillator.stop(audioContext.currentTime + 0.3);
        } catch (e) {
            console.warn('Could not play timer sound:', e);
        }
    }
    
    // Event handling
    on(event, callback) {
        if (!this.eventHandlers[event]) {
            this.eventHandlers[event] = [];
        }
        this.eventHandlers[event].push(callback);
    }
    
    off(event, callback) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event] = this.eventHandlers[event].filter(cb => cb !== callback);
        }
    }
    
    triggerCustomEvent(event, data = null) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`Error in event handler for ${event}:`, error);
                }
            });
        }
    }
    
    // Notification system
    showNotification(title, message, type = 'info') {
        // Create a simple notification (can be enhanced with a proper notification library)
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 max-w-sm transform transition-all duration-300 translate-x-full`;
        
        // Set color based on type
        const colors = {
            'info': 'bg-blue-500 text-white',
            'success': 'bg-green-500 text-white',
            'warning': 'bg-yellow-500 text-white',
            'error': 'bg-red-500 text-white'
        };
        
        notification.className += ` ${colors[type] || colors.info}`;
        
        notification.innerHTML = `
            <div class="flex items-start">
                <div class="flex-1">
                    <h4 class="font-semibold">${title}</h4>
                    <p class="text-sm mt-1">${message}</p>
                </div>
                <button class="ml-4 text-white hover:text-gray-200" onclick="this.parentElement.parentElement.remove()">
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
                    </svg>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.classList.add('translate-x-full');
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);
    }
    
    // Utility methods
    isSocketConnected() {
        return this.isConnected;
    }
    
    disconnect() {
        this.stopHeartbeat();
        if (this.socket) {
            this.socket.disconnect();
            this.isConnected = false;
        }
    }
}

// Initialize Socket.IO manager when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.socketManager = new SocketManager();
    
    // Auto-join kitchen room if on kitchen page
    if (window.location.pathname.includes('/kitchen')) {
        // Wait for connection to be established
        window.socketManager.on('socket:connected', () => {
            window.socketManager.joinKitchen();
            window.socketManager.requestKitchenOrders();
        });
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SocketManager;
}