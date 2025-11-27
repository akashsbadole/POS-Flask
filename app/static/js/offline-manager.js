class OfflineDataManager {
    constructor() {
        this.dbName = 'restaurant_pos_db';
        this.dbVersion = 4; // Incremented for performance optimizations
        this.db = null;
        this.isOnline = navigator.onLine;
        this.isSyncing = false;
        
        // Sync configuration
        this.syncConfig = {
            batchSize: 5,
            maxRetries: 3,
            retryDelay: 1000, // Base delay for exponential backoff
            conflictResolution: 'last-write-wins', // Default strategy
            priorityOrder: ['critical', 'high', 'normal', 'low']
        };
        
        // Data expiration policies (in milliseconds)
        this.expirationPolicies = {
            menuItems: 24 * 60 * 60 * 1000, // 24 hours
            tables: 60 * 60 * 1000, // 1 hour
            inventory: 30 * 60 * 1000, // 30 minutes
            customers: 7 * 24 * 60 * 60 * 1000, // 7 days
            syncLog: 3 * 24 * 60 * 60 * 1000, // 3 days
            conflicts: 7 * 24 * 60 * 60 * 1000, // 7 days
            failedSyncs: 7 * 24 * 60 * 60 * 1000, // 7 days
            offlineReports: 30 * 24 * 60 * 60 * 1000 // 30 days
        };
        
        // Performance optimization settings
        this.performanceConfig = {
            compressionThreshold: 1024 * 10, // Compress data larger than 10KB
            maxCacheSize: 50 * 1024 * 1024, // 50MB max cache size
            cleanupInterval: 60 * 60 * 1000, // Run cleanup every hour
            indexOptimization: true
        };
        
        // Queue management
        this.syncQueues = {
            critical: [],
            high: [],
            normal: [],
            low: []
        };
        
        // Sync status tracking
        this.syncStatus = {
            inProgress: false,
            lastSync: null,
            pendingCount: 0,
            failedCount: 0,
            successCount: 0
        };
        
        // Data validation schemas
        this.validationSchemas = {
            order: this.getOrderValidationSchema(),
            inventory: this.getInventoryValidationSchema(),
            menu: this.getMenuValidationSchema(),
            user: this.getUserValidationSchema()
        };
        
        // Bind methods to preserve 'this' context
        this.init = this.init.bind(this);
        this.setupEventListeners = this.setupEventListeners.bind(this);
        this.syncPendingOperations = this.syncPendingOperations.bind(this);
        this.showSyncNotification = this.showSyncNotification.bind(this);
        this.handleSyncComplete = this.handleSyncComplete.bind(this);
        this.validateData = this.validateData.bind(this);
        this.resolveConflict = this.resolveConflict.bind(this);
        
        this.init();
        this.setupEventListeners();
    }

    async init() {
        try {
            await this.openDatabase();
            console.log('Offline Manager: Database initialized');
            
            // Start cleanup interval
            this.startCleanupInterval();
            
            // Check storage usage
            await this.checkStorageUsage();
            
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
                
                // Create object stores with performance optimizations
                if (!db.objectStoreNames.contains('menuItems')) {
                    const menuStore = db.createObjectStore('menuItems', { keyPath: 'id' });
                    menuStore.createIndex('category', 'category_id', { unique: false });
                    menuStore.createIndex('updated', 'updated_at', { unique: false });
                    menuStore.createIndex('cached_at', 'cached_at', { unique: false });
                    menuStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('orders')) {
                    const orderStore = db.createObjectStore('orders', { keyPath: 'id' });
                    orderStore.createIndex('status', 'status', { unique: false });
                    orderStore.createIndex('created', 'created_at', { unique: false });
                    orderStore.createIndex('sync_status', 'sync_status', { unique: false });
                    orderStore.createIndex('offline_created', 'offline_created', { unique: false });
                    orderStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('cart')) {
                    const cartStore = db.createObjectStore('cart', { keyPath: 'id', autoIncrement: true });
                    cartStore.createIndex('item', 'menu_item_id', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('tables')) {
                    const tableStore = db.createObjectStore('tables', { keyPath: 'id' });
                    tableStore.createIndex('status', 'status', { unique: false });
                    tableStore.createIndex('cached_at', 'cached_at', { unique: false });
                    tableStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('syncQueue')) {
                    const syncStore = db.createObjectStore('syncQueue', { keyPath: 'id', autoIncrement: true });
                    syncStore.createIndex('timestamp', 'timestamp', { unique: false });
                    syncStore.createIndex('priority', 'priority', { unique: false });
                    syncStore.createIndex('type', 'type', { unique: false });
                    syncStore.createIndex('retry_count', 'retry_count', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('settings')) {
                    db.createObjectStore('settings', { keyPath: 'key' });
                }
                
                // New stores for enhanced offline functionality
                if (!db.objectStoreNames.contains('customers')) {
                    const customerStore = db.createObjectStore('customers', { keyPath: 'id' });
                    customerStore.createIndex('email', 'email', { unique: true });
                    customerStore.createIndex('phone', 'phone', { unique: false });
                    customerStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('inventory')) {
                    const inventoryStore = db.createObjectStore('inventory', { keyPath: 'id' });
                    inventoryStore.createIndex('ingredient', 'ingredient_id', { unique: false });
                    inventoryStore.createIndex('low_stock', 'stock_level', { unique: false });
                    inventoryStore.createIndex('cached_at', 'cached_at', { unique: false });
                    inventoryStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('syncLog')) {
                    const syncLogStore = db.createObjectStore('syncLog', { keyPath: 'id', autoIncrement: true });
                    syncLogStore.createIndex('timestamp', 'timestamp', { unique: false });
                    syncLogStore.createIndex('status', 'status', { unique: false });
                    syncLogStore.createIndex('type', 'type', { unique: false });
                    syncLogStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                // Additional stores for comprehensive offline functionality
                if (!db.objectStoreNames.contains('conflicts')) {
                    const conflictStore = db.createObjectStore('conflicts', { keyPath: 'id', autoIncrement: true });
                    conflictStore.createIndex('timestamp', 'timestamp', { unique: false });
                    conflictStore.createIndex('resolved', 'resolved', { unique: false });
                    conflictStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('failedSyncs')) {
                    const failedStore = db.createObjectStore('failedSyncs', { keyPath: 'id', autoIncrement: true });
                    failedStore.createIndex('timestamp', 'timestamp', { unique: false });
                    failedStore.createIndex('type', 'type', { unique: false });
                    failedStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                if (!db.objectStoreNames.contains('offlineReports')) {
                    const reportStore = db.createObjectStore('offlineReports', { keyPath: 'id', autoIncrement: true });
                    reportStore.createIndex('type', 'type', { unique: false });
                    reportStore.createIndex('created', 'created_at', { unique: false });
                    reportStore.createIndex('expires_at', 'expires_at', { unique: false });
                }
                
                // Add store for compression metadata
                if (!db.objectStoreNames.contains('compressionMeta')) {
                    const compressionStore = db.createObjectStore('compressionMeta', { keyPath: 'id' });
                    compressionStore.createIndex('store_name', 'store_name', { unique: false });
                }
            };
        });
    }

    // Data validation schemas
    getOrderValidationSchema() {
        return {
            required: ['table_id', 'items'],
            properties: {
                table_id: { type: 'number' },
                items: { type: 'array', minItems: 1 },
                subtotal: { type: 'number', minimum: 0 },
                tax_amount: { type: 'number', minimum: 0 },
                total: { type: 'number', minimum: 0 },
                notes: { type: 'string' }
            }
        };
    }

    getInventoryValidationSchema() {
        return {
            required: ['ingredient_id', 'stock_level'],
            properties: {
                ingredient_id: { type: 'number' },
                stock_level: { type: 'number', minimum: 0 },
                unit_cost: { type: 'number', minimum: 0 },
                minimum_stock: { type: 'number', minimum: 0 }
            }
        };
    }

    getMenuValidationSchema() {
        return {
            required: ['name', 'price', 'category_id'],
            properties: {
                name: { type: 'string', minLength: 1 },
                price: { type: 'number', minimum: 0 },
                category_id: { type: 'number' },
                description: { type: 'string' },
                is_available: { type: 'boolean' }
            }
        };
    }

    getUserValidationSchema() {
        return {
            required: ['email', 'name'],
            properties: {
                email: { type: 'string', format: 'email' },
                name: { type: 'string', minLength: 1 },
                role: { type: 'string' },
                phone: { type: 'string' }
            }
        };
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
            
            // Add new items with expiration
            for (const item of items) {
                item.cached_at = Date.now();
                item.expires_at = Date.now() + this.expirationPolicies.menuItems;
                
                // Compress large items
                if (this.shouldCompress(item)) {
                    item.compressed = true;
                    item.data = await this.compressData(item);
                }
                
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
            this.updateSyncStatus({ inProgress: true });
            
            // Get operations from all priority queues
            await this.loadSyncQueues();
            
            const totalOperations = Object.values(this.syncQueues).reduce((sum, queue) => sum + queue.length, 0);
            if (totalOperations === 0) {
                this.isSyncing = false;
                this.updateSyncStatus({ inProgress: false });
                return;
            }

            let successCount = 0;
            let failureCount = 0;
            let conflictCount = 0;
            
            // Process queues in priority order
            for (const priority of this.syncConfig.priorityOrder) {
                const queue = this.syncQueues[priority];
                if (queue.length === 0) continue;
                
                // Process in batches to avoid overwhelming server
                const batchSize = this.syncConfig.batchSize;
                const batches = [];
                for (let i = 0; i < queue.length; i += batchSize) {
                    batches.push(queue.slice(i, i + batchSize));
                }

                for (const batch of batches) {
                    const batchResults = await Promise.allSettled(batch.map(async (operation) => {
                        try {
                            // Validate data before sync
                            const isValid = await this.validateData(operation.type, operation.data);
                            if (!isValid) {
                                throw new Error('Data validation failed');
                            }
                            
                            const result = await this.syncOperation(operation);
                            await this.removeFromSyncQueue(operation.id);
                            successCount++;
                            await this.logSyncOperation(operation, 'success', result);
                            return { status: 'success', operation, result };
                        } catch (error) {
                            console.error('Offline Manager: Sync failed for operation', operation, error);
                            
                            // Check for conflicts
                            if (error.message.includes('conflict') || error.status === 409) {
                                conflictCount++;
                                await this.handleConflict(operation, error);
                                return { status: 'conflict', operation, error };
                            }
                            
                            failureCount++;
                            
                            // Update retry count with exponential backoff
                            operation.retry_count = (operation.retry_count || 0) + 1;
                            
                            // Remove if too many retries
                            if (operation.retry_count > this.syncConfig.maxRetries) {
                                await this.removeFromSyncQueue(operation.id);
                                await this.moveToFailedSyncs(operation, error);
                                await this.logSyncOperation(operation, 'failed', error);
                            } else {
                                // Calculate delay with exponential backoff
                                const delay = this.syncConfig.retryDelay * Math.pow(2, operation.retry_count - 1);
                                operation.next_retry = Date.now() + delay;
                                await this.updateRetryCount(operation);
                                await this.logSyncOperation(operation, 'retry', error);
                            }
                            return { status: 'failed', operation, error };
                        }
                    }));
                    
                    // Update queue based on results
                    this.syncQueues[priority] = this.syncQueues[priority].filter(op =>
                        !batchResults.some(result =>
                            result.status === 'success' && result.operation.id === op.id
                        )
                    );
                    
                    // Small delay between batches
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
            }
            
            // Update sync status
            this.updateSyncStatus({
                inProgress: false,
                lastSync: Date.now(),
                successCount: this.syncStatus.successCount + successCount,
                failureCount: this.syncStatus.failureCount + failureCount,
                pendingCount: Object.values(this.syncQueues).reduce((sum, queue) => sum + queue.length, 0)
            });
            
            if (successCount > 0 || failureCount > 0 || conflictCount > 0) {
                console.log(`Offline Manager: Sync completed - ${successCount} success, ${failureCount} failures, ${conflictCount} conflicts`);
                
                let message = `Sync completed: ${successCount} items synced`;
                if (failureCount > 0) message += `, ${failureCount} failed`;
                if (conflictCount > 0) message += `, ${conflictCount} conflicts`;
                
                this.showSyncNotification(message, failureCount > 0 ? 'warning' : 'success');
                
                // Update UI with sync results
                this.notifySyncComplete({
                    successCount,
                    failureCount,
                    conflictCount,
                    timestamp: Date.now()
                });
            }
            
        } catch (error) {
            console.error('Offline Manager: Sync failed', error);
            this.showSyncNotification('Sync failed', 'error');
            this.updateSyncStatus({ inProgress: false });
        } finally {
            this.isSyncing = false;
        }
    }

    // Load operations into priority queues
    async loadSyncQueues() {
        const queue = await this.getSyncQueue();
        
        // Reset queues
        this.syncQueues = {
            critical: [],
            high: [],
            normal: [],
            low: []
        };
        
        // Sort operations into priority queues
        queue.forEach(operation => {
            const priority = operation.priority || 'normal';
            if (this.syncQueues[priority]) {
                this.syncQueues[priority].push(operation);
            } else {
                this.syncQueues.normal.push(operation);
            }
        });
        
        // Sort each queue by timestamp and retry count
        Object.keys(this.syncQueues).forEach(priority => {
            this.syncQueues[priority].sort((a, b) => {
                // Prioritize operations with fewer retries
                if (a.retry_count !== b.retry_count) {
                    return a.retry_count - b.retry_count;
                }
                // Then by timestamp
                return a.timestamp - b.timestamp;
            });
        });
    }

    // Update sync status
    updateSyncStatus(updates) {
        this.syncStatus = { ...this.syncStatus, ...updates };
        
        // Dispatch status update event
        window.dispatchEvent(new CustomEvent('sync-status-update', {
            detail: this.syncStatus
        }));
    }

    // Data validation before sync
    async validateData(type, data) {
        const schema = this.validationSchemas[type];
        if (!schema) {
            console.warn(`No validation schema found for type: ${type}`);
            return true; // Allow sync if no schema exists
        }
        
        try {
            // Check required fields
            for (const field of schema.required || []) {
                if (!(field in data) || data[field] === null || data[field] === undefined) {
                    console.error(`Validation failed: Missing required field '${field}' for ${type}`);
                    return false;
                }
            }
            
            // Check field properties
            for (const [field, rules] of Object.entries(schema.properties || {})) {
                if (field in data && data[field] !== null) {
                    const value = data[field];
                    
                    // Type validation
                    if (rules.type) {
                        if (rules.type === 'number' && typeof value !== 'number') {
                            console.error(`Validation failed: Field '${field}' should be a number for ${type}`);
                            return false;
                        }
                        if (rules.type === 'string' && typeof value !== 'string') {
                            console.error(`Validation failed: Field '${field}' should be a string for ${type}`);
                            return false;
                        }
                        if (rules.type === 'boolean' && typeof value !== 'boolean') {
                            console.error(`Validation failed: Field '${field}' should be a boolean for ${type}`);
                            return false;
                        }
                        if (rules.type === 'array' && !Array.isArray(value)) {
                            console.error(`Validation failed: Field '${field}' should be an array for ${type}`);
                            return false;
                        }
                    }
                    
                    // Minimum validation
                    if (rules.minimum !== undefined && value < rules.minimum) {
                        console.error(`Validation failed: Field '${field}' should be at least ${rules.minimum} for ${type}`);
                        return false;
                    }
                    
                    // Min length validation
                    if (rules.minLength !== undefined && value.length < rules.minLength) {
                        console.error(`Validation failed: Field '${field}' should have at least ${rules.minLength} characters for ${type}`);
                        return false;
                    }
                    
                    // Min items validation
                    if (rules.minItems !== undefined && value.length < rules.minItems) {
                        console.error(`Validation failed: Field '${field}' should have at least ${rules.minItems} items for ${type}`);
                        return false;
                    }
                    
                    // Email format validation
                    if (rules.format === 'email' && !value.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
                        console.error(`Validation failed: Field '${field}' should be a valid email for ${type}`);
                        return false;
                    }
                }
            }
            
            return true;
        } catch (error) {
            console.error('Data validation error:', error);
            return false;
        }
    }

    // Handle conflicts
    async handleConflict(operation, error) {
        const conflict = {
            operation_id: operation.id,
            type: operation.type,
            action: operation.action,
            local_data: operation.data,
            server_data: error.serverData || null,
            error: error.message,
            timestamp: Date.now(),
            resolved: false
        };
        
        // Store conflict for resolution
        const transaction = this.db.transaction(['conflicts'], 'readwrite');
        const store = transaction.objectStore('conflicts');
        await store.add(conflict);
        
        // Show conflict notification
        this.showSyncNotification(`Conflict detected for ${operation.type} ${operation.action}`, 'error');
        
        // Dispatch conflict event for UI handling
        window.dispatchEvent(new CustomEvent('sync-conflict', {
            detail: conflict
        }));
    }

    // Move failed syncs to separate store
    async moveToFailedSyncs(operation, error) {
        const failedSync = {
            ...operation,
            error: error.message,
            failed_at: Date.now()
        };
        
        const transaction = this.db.transaction(['failedSyncs'], 'readwrite');
        const store = transaction.objectStore('failedSyncs');
        await store.add(failedSync);
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
            case 'inventory':
                return await this.syncInventory(action, data);
            case 'menu':
                return await this.syncMenu(action, data);
            case 'user':
                return await this.syncUser(action, data);
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

    async syncInventory(action, data) {
        try {
            let url, method;
            
            switch (action) {
                case 'create':
                    url = '/api/inventory/ingredients';
                    method = 'POST';
                    break;
                case 'update':
                    url = `/api/inventory/ingredients/${data.id}`;
                    method = 'PUT';
                    break;
                case 'delete':
                    url = `/api/inventory/ingredients/${data.id}`;
                    method = 'DELETE';
                    break;
                case 'adjust':
                    url = `/api/inventory/ingredients/${data.id}/adjust`;
                    method = 'POST';
                    break;
                default:
                    throw new Error(`Unknown inventory action: ${action}`);
            }
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Offline-Sync': 'true'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`Inventory sync failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Update local inventory data with server response
            if (result.id) {
                const transaction = this.db.transaction(['inventory'], 'readwrite');
                const store = transaction.objectStore('inventory');
                const localItem = await store.get(data.id);
                if (localItem) {
                    localItem.server_id = result.id;
                    localItem.sync_status = 'synced';
                    localItem.last_sync = Date.now();
                    await store.put(localItem);
                }
            }
            
            return result;
        } catch (error) {
            console.error('Offline Manager: Inventory sync failed', error);
            throw error;
        }
    }

    async syncMenu(action, data) {
        try {
            let url, method;
            
            switch (action) {
                case 'create':
                    url = '/api/menu/items';
                    method = 'POST';
                    break;
                case 'update':
                    url = `/api/menu/items/${data.id}`;
                    method = 'PUT';
                    break;
                case 'delete':
                    url = `/api/menu/items/${data.id}`;
                    method = 'DELETE';
                    break;
                default:
                    throw new Error(`Unknown menu action: ${action}`);
            }
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Offline-Sync': 'true'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`Menu sync failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Update local menu data with server response
            if (result.id) {
                const transaction = this.db.transaction(['menuItems'], 'readwrite');
                const store = transaction.objectStore('menuItems');
                const localItem = await store.get(data.id);
                if (localItem) {
                    localItem.server_id = result.id;
                    localItem.sync_status = 'synced';
                    localItem.last_sync = Date.now();
                    await store.put(localItem);
                }
            }
            
            return result;
        } catch (error) {
            console.error('Offline Manager: Menu sync failed', error);
            throw error;
        }
    }

    async syncUser(action, data) {
        try {
            let url, method;
            
            switch (action) {
                case 'create':
                    url = '/api/users';
                    method = 'POST';
                    break;
                case 'update':
                    url = `/api/users/${data.id}`;
                    method = 'PUT';
                    break;
                case 'profile':
                    url = `/api/users/${data.id}/profile`;
                    method = 'PUT';
                    break;
                default:
                    throw new Error(`Unknown user action: ${action}`);
            }
            
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'X-Offline-Sync': 'true'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                throw new Error(`User sync failed: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            // Update local user data with server response
            if (result.id) {
                const transaction = this.db.transaction(['customers'], 'readwrite');
                const store = transaction.objectStore('customers');
                const localUser = await store.get(data.id);
                if (localUser) {
                    localUser.server_id = result.id;
                    localUser.sync_status = 'synced';
                    localUser.last_sync = Date.now();
                    await store.put(localUser);
                }
            }
            
            return result;
        } catch (error) {
            console.error('Offline Manager: User sync failed', error);
            throw error;
        }
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
    
    // Data compression methods
    shouldCompress(data) {
        try {
            const jsonString = JSON.stringify(data);
            return jsonString.length > this.performanceConfig.compressionThreshold;
        } catch (error) {
            console.error('Error checking compression need:', error);
            return false;
        }
    }
    
    async compressData(data) {
        try {
            const jsonString = JSON.stringify(data);
            
            // Use CompressionStream API if available
            if ('CompressionStream' in window) {
                const stream = new CompressionStream('gzip');
                const writer = stream.writable.getWriter();
                const reader = stream.readable.getReader();
                
                writer.write(new TextEncoder().encode(jsonString));
                writer.close();
                
                const chunks = [];
                let done = false;
                
                while (!done) {
                    const { value, done: readerDone } = await reader.read();
                    done = readerDone;
                    if (value) chunks.push(value);
                }
                
                return new Uint8Array(chunks.reduce((acc, chunk) => [...acc, ...chunk], []));
            } else {
                // Fallback to simple compression
                return this.simpleCompress(jsonString);
            }
        } catch (error) {
            console.error('Error compressing data:', error);
            return data;
        }
    }
    
    async decompressData(compressedData) {
        try {
            // Use DecompressionStream API if available
            if ('DecompressionStream' in window && compressedData instanceof Uint8Array) {
                const stream = new DecompressionStream('gzip');
                const writer = stream.writable.getWriter();
                const reader = stream.readable.getReader();
                
                writer.write(compressedData);
                writer.close();
                
                const chunks = [];
                let done = false;
                
                while (!done) {
                    const { value, done: readerDone } = await reader.read();
                    done = readerDone;
                    if (value) chunks.push(value);
                }
                
                const decompressed = new Uint8Array(chunks.reduce((acc, chunk) => [...acc, ...chunk], []));
                return JSON.parse(new TextDecoder().decode(decompressed));
            } else {
                // Fallback to simple decompression
                return this.simpleDecompress(compressedData);
            }
        } catch (error) {
            console.error('Error decompressing data:', error);
            return compressedData;
        }
    }
    
    simpleCompress(data) {
        // Simple compression for fallback
        return btoa(data);
    }
    
    simpleDecompress(data) {
        // Simple decompression for fallback
        try {
            return JSON.parse(atob(data));
        } catch (error) {
            console.error('Error in simple decompression:', error);
            return data;
        }
    }
    
    // Data cleanup methods
    startCleanupInterval() {
        // Run cleanup periodically
        setInterval(() => {
            this.cleanupExpiredData();
            this.checkStorageUsage();
        }, this.performanceConfig.cleanupInterval);
        
        // Run initial cleanup
        setTimeout(() => this.cleanupExpiredData(), 5000);
    }
    
    async cleanupExpiredData() {
        try {
            const now = Date.now();
            const stores = [
                'menuItems', 'orders', 'tables', 'inventory',
                'customers', 'syncLog', 'conflicts', 'failedSyncs', 'offlineReports'
            ];
            
            for (const storeName of stores) {
                const transaction = this.db.transaction([storeName], 'readwrite');
                const store = transaction.objectStore(storeName);
                
                // Check if store has expires_at index
                if (store.indexNames.contains('expires_at')) {
                    const index = store.index('expires_at');
                    const range = IDBKeyRange.upperBound(now);
                    const expiredItems = await index.getAll(range);
                    
                    for (const item of expiredItems) {
                        await store.delete(item.id);
                    }
                    
                    if (expiredItems.length > 0) {
                        console.log(`Offline Manager: Cleaned up ${expiredItems.length} expired items from ${storeName}`);
                    }
                }
            }
            
            // Also clean up old compression metadata
            await this.cleanupCompressionMetadata();
            
        } catch (error) {
            console.error('Offline Manager: Failed to cleanup expired data', error);
        }
    }
    
    async cleanupCompressionMetadata() {
        try {
            const transaction = this.db.transaction(['compressionMeta'], 'readwrite');
            const store = transaction.objectStore('compressionMeta');
            const now = Date.now();
            const weekAgo = now - (7 * 24 * 60 * 60 * 1000);
            
            const index = store.index('store_name');
            const range = IDBKeyRange.upperBound(weekAgo);
            const oldMetadata = await index.getAll(range);
            
            for (const meta of oldMetadata) {
                await store.delete(meta.id);
            }
            
            if (oldMetadata.length > 0) {
                console.log(`Offline Manager: Cleaned up ${oldMetadata.length} old compression metadata entries`);
            }
        } catch (error) {
            console.error('Offline Manager: Failed to cleanup compression metadata', error);
        }
    }
    
    async checkStorageUsage() {
        try {
            const usage = await this.getStorageUsage();
            if (usage && usage.percentage > 80) {
                console.warn(`Offline Manager: Storage usage is high (${usage.percentage.toFixed(2)}%), running aggressive cleanup`);
                await this.aggressiveCleanup();
            }
        } catch (error) {
            console.error('Offline Manager: Failed to check storage usage', error);
        }
    }
    
    async aggressiveCleanup() {
        try {
            // Clean up more aggressively when storage is full
            const stores = ['syncLog', 'conflicts', 'failedSyncs'];
            
            for (const storeName of stores) {
                const transaction = this.db.transaction([storeName], 'readwrite');
                const store = transaction.objectStore(storeName);
                
                // Keep only the most recent items
                const allItems = await store.getAll();
                const sortedItems = allItems.sort((a, b) => b.timestamp - a.timestamp);
                const itemsToKeep = sortedItems.slice(0, 100); // Keep only 100 most recent
                
                // Clear and re-add kept items
                await store.clear();
                for (const item of itemsToKeep) {
                    await store.add(item);
                }
                
                const removedCount = allItems.length - itemsToKeep.length;
                if (removedCount > 0) {
                    console.log(`Offline Manager: Aggressively cleaned ${removedCount} items from ${storeName}`);
                }
            }
        } catch (error) {
            console.error('Offline Manager: Failed to perform aggressive cleanup', error);
        }
    }
    
    // Migration methods
    async migrateDatabase() {
        try {
            const currentVersion = this.db.version;
            const targetVersion = this.dbVersion;
            
            if (currentVersion < targetVersion) {
                console.log(`Offline Manager: Migrating database from version ${currentVersion} to ${targetVersion}`);
                
                // Close current database
                this.db.close();
                
                // Reopen with new version
                await this.openDatabase();
                
                console.log('Offline Manager: Database migration completed');
            }
        } catch (error) {
            console.error('Offline Manager: Database migration failed', error);
        }
    }
    
    // Performance optimization methods
    async optimizeIndexes() {
        try {
            if (!this.performanceConfig.indexOptimization) {
                return;
            }
            
            console.log('Offline Manager: Optimizing database indexes');
            
            // This would typically be handled by the browser automatically
            // But we can trigger some maintenance operations
            const stores = ['menuItems', 'orders', 'inventory', 'customers'];
            
            for (const storeName of stores) {
                const transaction = this.db.transaction([storeName], 'readonly');
                const store = transaction.objectStore(storeName);
                
                // Access all indexes to ensure they're loaded
                for (const indexName of store.indexNames) {
                    const index = store.index(indexName);
                    await index.count();
                }
            }
            
            console.log('Offline Manager: Index optimization completed');
        } catch (error) {
            console.error('Offline Manager: Index optimization failed', error);
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