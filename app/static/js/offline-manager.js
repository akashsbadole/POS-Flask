class OfflineDataManager {
    constructor() {
        this.dbName = 'restaurant_pos_db';
        this.dbVersion = 2; // Incremented for new stores
        this.db = null;
        this.isOnline = navigator.onLine;
        this.isSyncing = false;
        
        // Bind methods to preserve 'this' context
        this.init = this.init.bind(this);
        this.setupEventListeners = this.setupEventListeners.bind(this);
        this.syncPendingOperations = this.syncPendingOperations.bind(this);
        this.showSyncNotification = this.showSyncNotification.bind(this);
        this.handleSyncComplete = this.handleSyncComplete.bind(this);
        
        this.init();
        this.setupEventListeners();
    }

    async init() {
        try {
            await this.openDatabase();
            console.log('Offline Manager: Database initialized');
            if (this.isOnline) {
                this.syncPendingOperations();
            }
        } catch (error) {
            console.error('Offline Manager: Initialization failed', error);
        }
    }

    openDatabase() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create object stores
                if (!db.objectStoreNames.contains('menuItems')) {
                    const menuStore = db.createObjectStore('menuItems', { keyPath: 'id' });
                    menuStore.createIndex('category', 'category_id', { unique: false });
                    menuStore.createIndex('updated', 'updated_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('orders')) {
                    const orderStore = db.createObjectStore('orders', { keyPath: 'id' });
                    orderStore.createIndex('status', 'status', { unique: false });
                    orderStore.createIndex('created', 'created_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('cart')) {
                    const cartStore = db.createObjectStore('cart', { keyPath: 'id', autoIncrement: true });
                    cartStore.createIndex('item', 'menu_item_id', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('tables')) {
                    const tableStore = db.createObjectStore('tables', { keyPath: 'id' });
                    tableStore.createIndex('status', 'status', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('syncQueue')) {
                    const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
                    syncStore.createIndex('timestamp', 'timestamp', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('settings')) {
                    db.createObjectStore('settings', { keyPath: 'key' });
                }
                
                // New stores for enhanced offline functionality
                if (!db.objectStoreNames.contains('customers')) {
                    const customerStore = db.createObjectStore('customers', { keyPath: 'id' });
                    customerStore.createIndex('email', 'email', { unique: true });
                    customerStore.createIndex('phone', 'phone', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('inventory')) {
                    const inventoryStore = db.createObjectStore('inventory', { keyPath: 'id' });
                    inventoryStore.createIndex('ingredient', 'ingredient_id', { unique: false });
                    inventoryStore.createIndex('low_stock', 'stock_level', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('syncLog')) {
                    const syncLogStore = db.createObjectStore('syncLog', { keyPath: 'id', autoIncrement: true });
                    syncLogStore.createIndex('timestamp', 'timestamp', { unique: false });
                    syncLogStore.createIndex('status', 'status', { unique: false });
                }
            };
        });
    }

    setupEventListeners() {
        // Network status listeners
        window.addEventListener('online', () => {
            this.isOnline = true;
            console.log('Offline Manager: Connection restored');
            this.syncPendingOperations();
            this.showSyncNotification('Connection restored', 'success');
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            console.log('Offline Manager: Connection lost');
            this.showSyncNotification('Working offline', 'warning');
        });
        
        // Service worker messages
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data && event.data.type === 'SYNC_COMPLETE') {
                    this.handleSyncComplete(event.data.data);
                }
            });
        }
        
        // Page visibility change for sync optimization
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && this.isOnline) {
                this.syncPendingOperations();
            }
        });
        
        // Before unload for data preservation
        window.addEventListener('beforeunload', () => {
            this.savePendingData();
        });
    }

    // Menu Management
    async cacheMenuItems(items) {
        try {
            const transaction = this.db.transaction(['menuItems'], 'readwrite');
            const store = transaction.objectStore('menuItems');
            
            // Clear existing items
            await store.clear();
            
            // Add new items
            for (const item of items) {
                item.cached_at = Date.now();
                await store.put(item);
            }
            
            console.log(`Offline Manager: Cached ${items.length} menu items`);
        } catch (error) {
            console.error('Offline Manager: Failed to cache menu items', error);
        }
    }

    async getMenuItems(categoryId = null) {
        try {
            const transaction = this.db.transaction(['menuItems'], 'readonly');
            const store = transaction.objectStore('menuItems');
            
            if (categoryId) {
                const index = store.index('category');
                return await index.getAll(categoryId);
            } else {
                return await store.getAll();
            }
        } catch (error) {
            console.error('Offline Manager: Failed to get menu items', error);
            return [];
        }
    }

    // Order Management
    async saveOrder(order) {
        try {
            const transaction = this.db.transaction(['orders', 'syncQueue'], 'readwrite');
            const orderStore = transaction.objectStore('orders');
            const syncStore = transaction.objectStore('syncQueue');
            
            // Add offline timestamp
            order.offline_created = Date.now();
            order.sync_status = 'pending';
            
            await orderStore.add(order);
            
            // Add to sync queue if online
            if (this.isOnline) {
                await syncStore.add({
                    type: 'order',
                    action: 'create',
                    data: order,
                    timestamp: Date.now()
                });
            }
            
            console.log('Offline Manager: Order saved offline', order.id);
            return order;
        } catch (error) {
            console.error('Offline Manager: Failed to save order', error);
            throw error;
        }
    }

    async getOrders() {
        try {
            const transaction = this.db.transaction(['orders'], 'readonly');
            const store = transaction.objectStore('orders');
            const index = store.index('created');
            return await index.getAll();
        } catch (error) {
            console.error('Offline Manager: Failed to get orders', error);
            return [];
        }
    }

    // Cart Management
    async addToCart(item) {
        try {
            const transaction = this.db.transaction(['cart'], 'readwrite');
            const store = transaction.objectStore('cart');
            
            // Check if item already in cart
            const index = store.index('item');
            const existingItems = await index.getAll(item.menu_item_id);
            
            if (existingItems.length > 0) {
                // Update quantity
                const existingItem = existingItems[0];
                existingItem.quantity += item.quantity;
                await store.put(existingItem);
            } else {
                // Add new item
                await store.add(item);
            }
            
            console.log('Offline Manager: Item added to cart', item);
        } catch (error) {
            console.error('Offline Manager: Failed to add to cart', error);
        }
    }

    async getCart() {
        try {
            const transaction = this.db.transaction(['cart'], 'readonly');
            const store = transaction.objectStore('cart');
            return await store.getAll();
        } catch (error) {
            console.error('Offline Manager: Failed to get cart', error);
            return [];
        }
    }

    async clearCart() {
        try {
            const transaction = this.db.transaction(['cart'], 'readwrite');
            const store = transaction.objectStore('cart');
            await store.clear();
            console.log('Offline Manager: Cart cleared');
        } catch (error) {
            console.error('Offline Manager: Failed to clear cart', error);
        }
    }

    // Table Management
    async cacheTables(tables) {
        try {
            const transaction = this.db.transaction(['tables'], 'readwrite');
            const store = transaction.objectStore('tables');
            
            await store.clear();
            
            for (const table of tables) {
                table.cached_at = Date.now();
                await store.put(table);
            }
            
            console.log(`Offline Manager: Cached ${tables.length} tables`);
        } catch (error) {
            console.error('Offline Manager: Failed to cache tables', error);
        }
    }

    async getTables() {
        try {
            const transaction = this.db.transaction(['tables'], 'readonly');
            const store = transaction.objectStore('tables');
            return await store.getAll();
        } catch (error) {
            console.error('Offline Manager: Failed to get tables', error);
            return [];
        }
    }

    // Sync Queue Management
    async addToSyncQueue(operation) {
        try {
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            
            await store.add({
                ...operation,
                timestamp: Date.now(),
                retry_count: 0
            });
            
            console.log('Offline Manager: Operation added to sync queue', operation);
        } catch (error) {
            console.error('Offline Manager: Failed to add to sync queue', error);
        }
    }

    async getSyncQueue() {
        try {
            const transaction = this.db.transaction(['syncQueue'], 'readonly');
            const store = transaction.objectStore('syncQueue');
            const index = store.index('timestamp');
            return await index.getAll();
        } catch (error) {
            console.error('Offline Manager: Failed to get sync queue', error);
            return [];
        }
    }

    async removeFromSyncQueue(id) {
        try {
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            await store.delete(id);
        } catch (error) {
            console.error('Offline Manager: Failed to remove from sync queue', error);
        }
    }

    // Sync Operations
    async syncPendingOperations() {
        // Prevent concurrent syncs
        if (this.isSyncing) {
            console.log('Offline Manager: Sync already in progress');
            return;
        }

        if (!this.isOnline) {
            console.log('Offline Manager: Still offline, skipping sync');
            return;
        }

        try {
            this.isSyncing = true;
            const queue = await this.getSyncQueue();
            
            if (queue.length === 0) {
                this.isSyncing = false;
                return;
            }

            let successCount = 0;
            let failureCount = 0;
            
            // Process in batches to avoid overwhelming server
            const batchSize = 5;
            const batches = [];
            for (let i = 0; i < queue.length; i += batchSize) {
                batches.push(queue.slice(i, i + batchSize));
            }

            for (const batch of batches) {
                await Promise.all(batch.map(async (operation) => {
                    try {
                        const result = await this.syncOperation(operation);
                        await this.removeFromSyncQueue(operation.id);
                        successCount++;
                        await this.logSyncOperation(operation, 'success', result);
                    } catch (error) {
                        console.error('Offline Manager: Sync failed for operation', operation, error);
                        failureCount++;
                        
                        // Update retry count
                        operation.retry_count = (operation.retry_count || 0) + 1;
                        
                        // Remove if too many retries
                        if (operation.retry_count > 3) {
                            await this.removeFromSyncQueue(operation.id);
                            await this.logSyncOperation(operation, 'failed', error);
                        } else {
                            // Update retry count and delay
                            await this.updateRetryCount(operation);
                            await this.logSyncOperation(operation, 'retry', error);
                        }
                    }
                }));
                
                // Small delay between batches
                await new Promise(resolve => setTimeout(resolve, 500));
            }
            
            if (successCount > 0 || failureCount > 0) {
                console.log(`Offline Manager: Sync completed - ${successCount} success, ${failureCount} failures`);
                this.showSyncNotification(`Sync completed: ${successCount} items synced`, 'success');
                
                // Update UI with sync results
                this.notifySyncComplete({
                    successCount,
                    failureCount,
                    timestamp: Date.now()
                });
            }
            
        } catch (error) {
            console.error('Offline Manager: Sync failed', error);
            this.showSyncNotification('Sync failed', 'error');
        } finally {
            this.isSyncing = false;
        }
    }

    async syncOperation(operation) {
        const { type, action, data } = operation;
        
        switch (type) {
            case 'order':
                return await this.syncOrder(action, data);
            case 'cart':
                return await this.syncCart(action, data);
            case 'table':
                return await this.syncTable(action, data);
            default:
                throw new Error(`Unknown sync operation type: ${type}`);
        }
    }

    async syncOrder(action, data) {
        const response = await fetch('/api/orders', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Offline-Sync': 'true'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`Sync failed: ${response.statusText}`);
        }

        const result = await response.json();
        
        // Update local order with server ID
        if (result.id) {
            const transaction = this.db.transaction(['orders'], 'readwrite');
            const store = transaction.objectStore('orders');
            const localOrder = await store.get(data.id);
            if (localOrder) {
                localOrder.server_id = result.id;
                localOrder.sync_status = 'synced';
                await store.put(localOrder);
            }
        }

        return result;
    }

    async syncCart(action, data) {
        // Cart sync implementation
        console.log('Offline Manager: Syncing cart operation', action, data);
        return true;
    }

    async syncTable(action, data) {
        // Table sync implementation
        console.log('Offline Manager: Syncing table operation', action, data);
        return true;
    }

    // Settings Management
    async saveSetting(key, value) {
        try {
            const transaction = this.db.transaction(['settings'], 'readwrite');
            const store = transaction.objectStore('settings');
            await store.put({ key, value });
        } catch (error) {
            console.error('Offline Manager: Failed to save setting', error);
        }
    }

    async getSetting(key, defaultValue = null) {
        try {
            const transaction = this.db.transaction(['settings'], 'readonly');
            const store = transaction.objectStore('settings');
            const result = await store.get(key);
            return result ? result.value : defaultValue;
        } catch (error) {
            console.error('Offline Manager: Failed to get setting', error);
            return defaultValue;
        }
    }

    // Utility Methods
    async clearCache() {
        try {
            const stores = ['menuItems', 'orders', 'cart', 'tables', 'syncQueue'];
            
            for (const storeName of stores) {
                const transaction = this.db.transaction([storeName], 'readwrite');
                const store = transaction.objectStore(storeName);
                await store.clear();
            }
            
            console.log('Offline Manager: Cache cleared');
        } catch (error) {
            console.error('Offline Manager: Failed to clear cache', error);
        }
    }

    async getStorageUsage() {
        try {
            if ('storage' in navigator && 'estimate' in navigator.storage) {
                const estimate = await navigator.storage.estimate();
                return {
                    used: estimate.usage,
                    available: estimate.quota,
                    percentage: (estimate.usage / estimate.quota) * 100
                };
            }
            return null;
        } catch (error) {
            console.error('Offline Manager: Failed to get storage usage', error);
            return null;
        }
    }

    handleSyncComplete(data) {
        console.log('Offline Manager: Sync completed', data);
        // Update UI or notify user
        this.notifySyncComplete(data);
    }

    notifySyncComplete(data) {
        // Create notification if supported
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('Sync Complete', {
                body: `${data.synced} items synced successfully`,
                icon: '/static/images/icon-192x192.png',
                badge: '/static/images/badge.png'
            });
        }
        
        // Dispatch custom event for UI updates
        window.dispatchEvent(new CustomEvent('offline-sync-complete', {
            detail: data
        }));
    }

    async updateRetryCount(operation) {
        try {
            const transaction = this.db.transaction(['syncQueue'], 'readwrite');
            const store = transaction.objectStore('syncQueue');
            await store.put(operation);
        } catch (error) {
            console.error('Offline Manager: Failed to update retry count', error);
        }
    }

    // Show sync notification
    showSyncNotification(message, type = 'info') {
        // Use the global notification system if available
        if (window.RestaurantPOS && window.RestaurantPOS.showNotification) {
            window.RestaurantPOS.showNotification(message, type);
        } else {
            // Fallback to console and basic notification
            console.log(`Sync [${type}]: ${message}`);
            
            // Create a simple notification if no global system available
            const notification = document.createElement('div');
            notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${
                type === 'error' ? 'bg-red-100 border-2 border-red-300 text-red-800' :
                type === 'warning' ? 'bg-yellow-100 border-2 border-yellow-300 text-yellow-800' :
                type === 'success' ? 'bg-green-100 border-2 border-green-300 text-green-800' :
                'bg-blue-100 border-2 border-blue-300 text-blue-800'
            }`;
            notification.innerHTML = `
                <div class="flex items-center">
                    <span class="text-xl mr-2">
                        ${type === 'error' ? '🌶️' :
                          type === 'warning' ? '⚠️' :
                          type === 'success' ? '✅' : 'ℹ️'}
                    </span>
                    <span class="font-medium">${message}</span>
                </div>
            `;
            
            document.body.appendChild(notification);
            
            // Auto remove after 5 seconds
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 5000);
        }
    }

    // Log sync operation
    async logSyncOperation(operation, status, result) {
        try {
            const transaction = this.db.transaction(['syncLog'], 'readwrite');
            const store = transaction.objectStore('syncLog');
            
            await store.add({
                operation_id: operation.id,
                operation_type: operation.type,
                operation_action: operation.action,
                status: status,
                result: result ? JSON.stringify(result) : null,
                timestamp: Date.now()
            });
        } catch (error) {
            console.error('Offline Manager: Failed to log sync operation', error);
        }
    }

    // Save pending data before unload
    async savePendingData() {
        try {
            // This is a placeholder for saving any critical pending data
            // In a real implementation, you might save cart data, form data, etc.
            console.log('Offline Manager: Saving pending data before unload');
        } catch (error) {
            console.error('Offline Manager: Failed to save pending data', error);
        }
    }
}

// Initialize offline manager
window.OfflineDataManager = OfflineDataManager;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.offlineManager = new OfflineDataManager();
    });
} else {
    window.offlineManager = new OfflineDataManager();
}