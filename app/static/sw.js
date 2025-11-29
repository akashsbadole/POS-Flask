const CACHE_NAME = 'restaurant-pos-v3';
const DATA_CACHE_NAME = 'restaurant-pos-data-v3';
const STATIC_CACHE_NAME = 'restaurant-pos-static-v3';
const RUNTIME_CACHE_NAME = 'restaurant-pos-runtime-v3';

// Enhanced cache configuration
const CACHE_CONFIG = {
    STATIC: {
        name: STATIC_CACHE_NAME,
        maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days
        maxEntries: 100
    },
    DATA: {
        name: DATA_CACHE_NAME,
        maxAge: 24 * 60 * 60 * 1000, // 24 hours
        maxEntries: 500
    },
    RUNTIME: {
        name: RUNTIME_CACHE_NAME,
        maxAge: 60 * 60 * 1000, // 1 hour
        maxEntries: 50
    }
};

// Critical static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/css/tailwind.css',
    '/static/js/app.js',
    '/static/js/offline-manager.js',
    '/static/images/logo.png',
    '/static/images/icon-192x192.png',
    '/offline.html',
    '/manifest.json'
];

// API endpoints that support offline functionality
const OFFLINE_API_ENDPOINTS = [
    '/api/menu/items',
    '/api/menu/categories',
    '/api/cart/count',
    '/api/tables/status',
    '/api/offline/menu/items',
    '/api/offline/menu/categories',
    '/api/offline/tables',
    '/api/offline/orders/recent'
];

// Data that should be cached for offline use
const CACHEABLE_API_PATTERNS = [
    '/api/menu/',
    '/api/cart/',
    '/api/tables/',
    '/api/offline/',
    '/api/inventory/',
    '/api/orders/'
];

// Network-aware caching strategies
const CACHE_STRATEGIES = {
    STATIC: 'cacheFirst',
    API: 'networkFirst',
    IMAGE: 'cacheFirst',
    DOCUMENT: 'staleWhileRevalidate'
};

// Push notification configuration
const PUSH_CONFIG = {
    publicKey: 'BLjWZ1K8KXqC9JgQm8VhLzX7Y2R5tP9nF3W6sA4dE7gH0jK3lM6oP9qR2tU5wX8z',
    vapidPublicKey: 'BLjWZ1K8KXqC9JgQm8VhLzX7Y2R5tP9nF3W6sA4dE7gH0jK3lM6oP9qR2tU5wX8z'
};

// Background sync configuration
const SYNC_CONFIG = {
    maxRetries: 5,
    retryDelay: 1000,
    syncInterval: 5 * 60 * 1000, // 5 minutes
    batchSize: 10
};

// Enhanced install event with comprehensive caching
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        Promise.all([
            // Cache static assets with enhanced error handling
            caches.open(CACHE_CONFIG.STATIC.name).then(cache => {
                return Promise.allSettled(
                    STATIC_ASSETS.map(asset =>
                        fetch(asset, { cache: 'no-cache' }).then(response => {
                            if (response.ok) {
                                // Add cache metadata
                                const responseClone = response.clone();
                                const headers = new Headers(responseClone.headers);
                                headers.set('X-Cache-Timestamp', Date.now().toString());
                                headers.set('X-Cache-Version', CACHE_CONFIG.STATIC.name);
                                
                                const modifiedResponse = new Response(responseClone.body, {
                                    status: responseClone.status,
                                    statusText: responseClone.statusText,
                                    headers: headers
                                });
                                
                                return cache.put(asset, modifiedResponse);
                            }
                            console.warn(`Service Worker: Failed to cache ${asset}: ${response.status}`);
                            return Promise.resolve();
                        }).catch(error => {
                            console.warn(`Service Worker: Failed to cache ${asset}:`, error);
                            return Promise.resolve();
                        })
                    )
                );
            }),
            // Create data and runtime caches
            caches.open(CACHE_CONFIG.DATA.name),
            caches.open(CACHE_CONFIG.RUNTIME.name),
            // Pre-cache critical API data
            precriticalAPIData()
        ]).then(() => {
            console.log('Service Worker: Installation complete');
            // Skip waiting to activate immediately
            return self.skipWaiting();
        })
    );
});

// Pre-cache critical API data
async function precriticalAPIData() {
    try {
        const dataCache = await caches.open(CACHE_CONFIG.DATA.name);
        
        // Pre-cache menu data
        const menuResponse = await fetch('/api/offline/menu/items');
        if (menuResponse.ok) {
            await dataCache.put('/api/offline/menu/items', menuResponse);
        }
        
        // Pre-cache categories
        const categoriesResponse = await fetch('/api/offline/menu/categories');
        if (categoriesResponse.ok) {
            await dataCache.put('/api/offline/menu/categories', categoriesResponse);
        }
        
        // Pre-cache tables
        const tablesResponse = await fetch('/api/offline/tables');
        if (tablesResponse.ok) {
            await dataCache.put('/api/offline/tables', tablesResponse);
        }
        
        console.log('Service Worker: Critical API data pre-cached');
    } catch (error) {
        console.warn('Service Worker: Failed to pre-cache critical data:', error);
    }
}

// Enhanced activate event with intelligent cache cleanup
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        Promise.all([
            // Clean up old caches
            caches.keys().then(cacheNames => {
                const currentCacheNames = [
                    CACHE_CONFIG.STATIC.name,
                    CACHE_CONFIG.DATA.name,
                    CACHE_CONFIG.RUNTIME.name
                ];
                
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (!currentCacheNames.includes(cacheName)) {
                            console.log('Service Worker: Deleting old cache:', cacheName);
                            return caches.delete(cacheName);
                        }
                    })
                );
            }),
            // Take control of all open pages
            clients.claim(),
            // Initialize background sync
            initializeBackgroundSync()
        ]).then(() => {
            console.log('Service Worker: Activation complete');
        })
    );
});

// Initialize background sync
async function initializeBackgroundSync() {
    try {
        if ('periodicSync' in self.registration) {
            // Register periodic sync for data updates
            await self.registration.periodicSync.register('data-sync', {
                minInterval: SYNC_CONFIG.syncInterval
            });
            console.log('Service Worker: Periodic sync registered');
        }
        
        // Register for one-off sync events
        if ('sync' in self.registration) {
            console.log('Service Worker: Background sync available');
        }
    } catch (error) {
        console.warn('Service Worker: Failed to initialize background sync:', error);
    }
}

// Fetch event - implement sophisticated caching strategy
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Handle different request types
    if (request.method === 'GET') {
        if (isStaticAsset(request.url)) {
            // Cache-first for static assets
            event.respondWith(cacheFirst(request, STATIC_CACHE_NAME));
        } else if (isAPIRequest(request.url)) {
            // Network-first for API requests with offline fallback
            event.respondWith(networkFirst(request, DATA_CACHE_NAME));
        } else {
            // Stale-while-revalidate for other requests
            event.respondWith(staleWhileRevalidate(request, CACHE_NAME));
        }
    } else if (request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE') {
        // Handle offline POST/PUT/DELETE requests
        event.respondWith(handleOfflineMutations(request));
    }
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync triggered:', event.tag);
    
    if (event.tag === 'offline-mutations') {
        event.waitUntil(syncOfflineMutations());
    } else if (event.tag === 'order-sync') {
        event.waitUntil(syncOrderData());
    } else if (event.tag === 'inventory-sync') {
        event.waitUntil(syncInventoryData());
    } else if (event.tag === 'menu-sync') {
        event.waitUntil(syncMenuData());
    } else if (event.tag === 'user-sync') {
        event.waitUntil(syncUserData());
    }
});

// Enhanced push notifications with rich interactions
self.addEventListener('push', event => {
    console.log('Service Worker: Push received');
    
    let notificationData = {
        title: 'Restaurant POS',
        body: 'New notification',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        },
        actions: [
            {
                action: 'view',
                title: 'View'
            },
            {
                action: 'dismiss',
                title: 'Dismiss'
            }
        ],
        requireInteraction: false,
        silent: false
    };
    
    // Parse push data if available
    if (event.data) {
        try {
            const pushData = event.data.json();
            notificationData = {
                ...notificationData,
                ...pushData,
                data: {
                    ...notificationData.data,
                    ...pushData.data
                }
            };
        } catch (error) {
            // Fallback to text data
            notificationData.body = event.data.text();
        }
    }
    
    // Customize notification based on type
    if (notificationData.data.type) {
        notificationData = customizeNotification(notificationData.data.type, notificationData);
    }
    
    event.waitUntil(
        self.registration.showNotification(notificationData.title, notificationData)
    );
});

// Customize notification based on type
function customizeNotification(type, baseNotification) {
    switch (type) {
        case 'order':
            return {
                ...baseNotification,
                title: 'New Order',
                body: 'A new order has been placed',
                icon: '/static/images/order-icon.png',
                actions: [
                    { action: 'view-order', title: 'View Order' },
                    { action: 'accept-order', title: 'Accept' }
                ],
                requireInteraction: true,
                vibrate: [200, 100, 200]
            };
            
        case 'inventory':
            return {
                ...baseNotification,
                title: 'Inventory Alert',
                body: 'Low stock detected',
                icon: '/static/images/inventory-icon.png',
                actions: [
                    { action: 'view-inventory', title: 'View Inventory' },
                    { action: 'reorder', title: 'Reorder' }
                ],
                requireInteraction: true,
                vibrate: [100, 50, 100, 50, 100]
            };
            
        case 'sync':
            return {
                ...baseNotification,
                title: 'Sync Complete',
                body: 'Offline data has been synced',
                icon: '/static/images/sync-icon.png',
                requireInteraction: false,
                silent: true
            };
            
        default:
            return baseNotification;
    }
}

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    console.log('Service Worker: Notification clicked', event);
    
    event.notification.close();
    
    const action = event.action;
    const notificationData = event.notification.data;
    
    // Handle different actions
    if (action === 'view' || action === 'view-order') {
        event.waitUntil(
            clients.openWindow('/orders')
        );
    } else if (action === 'view-inventory') {
        event.waitUntil(
            clients.openWindow('/inventory')
        );
    } else if (action === 'accept-order') {
        event.waitUntil(
            handleOrderAction(notificationData.orderId, 'accept')
        );
    } else if (action === 'reorder') {
        event.waitUntil(
            clients.openWindow('/inventory/reorder')
        );
    } else {
        // Default action - open app
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Handle order actions from notifications
async function handleOrderAction(orderId, action) {
    try {
        const response = await fetch(`/api/orders/${orderId}/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            // Open the orders page to show updated status
            const client = await clients.openWindow('/orders');
            return client;
        }
    } catch (error) {
        console.error('Service Worker: Failed to handle order action:', error);
    }
}

// Handle notification close
self.addEventListener('notificationclose', event => {
    console.log('Service Worker: Notification closed', event);
    
    // Log notification close for analytics
    const notificationData = event.notification.data;
    logNotificationEvent('close', notificationData);
});

// Log notification events for analytics
async function logNotificationEvent(event, data) {
    try {
        const response = await fetch('/api/analytics/notification', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                event: event,
                data: data,
                timestamp: Date.now()
            })
        });
    } catch (error) {
        console.warn('Service Worker: Failed to log notification event:', error);
    }
}

// Cache strategies
function cacheFirst(request, cacheName) {
    return caches.open(cacheName).then(cache => {
        return cache.match(request).then(response => {
            if (response) {
                return response;
            }
            return fetch(request).then(response => {
                // Cache successful responses
                if (response.ok) {
                    cache.put(request, response.clone());
                }
                return response;
            });
        });
    });
}

function networkFirst(request, cacheName) {
    return fetch(request).then(response => {
        // Cache successful API responses
        if (response.ok && isCacheableAPIResponse(request.url)) {
            caches.open(cacheName).then(cache => {
                cache.put(request, response.clone());
            });
        }
        return response;
    }).catch(() => {
        // Network failed, try cache
        return caches.open(cacheName).then(cache => {
            return cache.match(request).then(response => {
                if (response) {
                    // Return cached response with offline indicator
                    const responseClone = response.clone();
                    const headers = new Headers(responseClone.headers);
                    headers.set('X-Offline-Cache', 'true');
                    
                    return new Response(responseClone.body, {
                        status: responseClone.status,
                        statusText: responseClone.statusText,
                        headers: headers
                    });
                }
                
                // No cached response, return offline page for navigation requests
                if (request.mode === 'navigate') {
                    return caches.match('/offline.html');
                }
                
                // Return error response for API requests
                return new Response(
                    JSON.stringify({ 
                        error: 'Offline - No cached data available',
                        offline: true 
                    }),
                    {
                        status: 503,
                        statusText: 'Service Unavailable',
                        headers: { 'Content-Type': 'application/json' }
                    }
                );
            });
        });
    });
}

function staleWhileRevalidate(request, cacheName) {
    return caches.open(cacheName).then(cache => {
        return cache.match(request).then(response => {
            const fetchPromise = fetch(request).then(networkResponse => {
                if (networkResponse.ok) {
                    cache.put(request, networkResponse.clone());
                }
                return networkResponse;
            });
            
            // Return cached version immediately, then update in background
            return response || fetchPromise;
        });
    });
}

// Helper functions
function isStaticAsset(url) {
    return url.includes('/static/') || 
           url.includes('.css') || 
           url.includes('.js') || 
           url.includes('.png') || 
           url.includes('.jpg') || 
           url.includes('.svg');
}

function isAPIRequest(url) {
    return url.includes('/api/') || 
           OFFLINE_API_ENDPOINTS.some(endpoint => url.includes(endpoint));
}

function isCacheableAPIResponse(url) {
    return CACHEABLE_API_PATTERNS.some(pattern => url.includes(pattern));
}

// Handle offline mutations (POST/PUT/DELETE)
function handleOfflineMutations(request) {
    return new Promise((resolve) => {
        // Determine priority based on URL and method
        const priority = determineMutationPriority(request.url, request.method);
        
        // Store mutation for later sync
        const mutation = {
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body: request.body,
            timestamp: Date.now(),
            priority: priority,
            retry_count: 0,
            id: generateMutationId()
        };
        
        // Store in IndexedDB for later sync
        storeOfflineMutation(mutation).then(() => {
            // Register background sync if available
            registerBackgroundSync(mutation.type || 'offline-mutations');
            
            // Return immediate response for optimistic UI updates
            resolve(new Response(
                JSON.stringify({
                    success: true,
                    offline: true,
                    message: 'Action will be synced when online',
                    mutation_id: mutation.id,
                    priority: priority
                }),
                {
                    status: 202,
                    statusText: 'Accepted',
                    headers: { 'Content-Type': 'application/json' }
                }
            ));
        });
    });
}

// Determine mutation priority based on URL and method
function determineMutationPriority(url, method) {
    // Critical operations that should sync first
    if (url.includes('/orders') && method === 'POST') {
        return 'critical';
    }
    
    // High priority operations
    if (url.includes('/inventory') && method === 'PUT') {
        return 'high';
    }
    
    // Normal priority for most operations
    return 'normal';
}

// Generate unique mutation ID
function generateMutationId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// Register background sync if available
function registerBackgroundSync(tag) {
    if ('serviceWorker' in navigator && 'sync' in window.ServiceWorkerRegistration.prototype) {
        self.registration.sync.register(tag)
            .then(() => {
                console.log(`Service Worker: Background sync registered for ${tag}`);
            })
            .catch(error => {
                console.error('Service Worker: Background sync registration failed:', error);
            });
    }
}

// Store offline mutations in IndexedDB
function storeOfflineMutation(mutation) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('offline-mutations', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['mutations'], 'readwrite');
            const store = transaction.objectStore('mutations');
            
            // Determine mutation type based on URL
            if (!mutation.type) {
                if (mutation.url.includes('/orders')) {
                    mutation.type = 'order';
                } else if (mutation.url.includes('/inventory')) {
                    mutation.type = 'inventory';
                } else if (mutation.url.includes('/menu')) {
                    mutation.type = 'menu';
                } else if (mutation.url.includes('/users')) {
                    mutation.type = 'user';
                } else {
                    mutation.type = 'general';
                }
            }
            
            store.add(mutation);
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
        
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('mutations')) {
                const store = db.createObjectStore('mutations', { keyPath: 'id', autoIncrement: true });
                // Create indexes for better query performance
                store.createIndex('timestamp', 'timestamp', { unique: false });
                store.createIndex('priority', 'priority', { unique: false });
                store.createIndex('type', 'type', { unique: false });
                store.createIndex('retry_count', 'retry_count', { unique: false });
            }
        };
    });
}

// Sync offline mutations when back online
function syncOfflineMutations() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('offline-mutations', 1);
        
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['mutations'], 'readwrite');
            const store = transaction.objectStore('mutations');
            
            const getAllRequest = store.getAll();
            
            getAllRequest.onsuccess = () => {
                const mutations = getAllRequest.result;
                
                if (mutations.length === 0) {
                    resolve();
                    return;
                }
                
                // Group mutations by type for priority processing
                const criticalMutations = mutations.filter(m => m.priority === 'critical');
                const normalMutations = mutations.filter(m => m.priority !== 'critical');
                const orderedMutations = [...criticalMutations, ...normalMutations];
                
                // Sync each mutation with retry logic
                const syncPromises = orderedMutations.map(mutation => {
                    return syncWithRetry(mutation)
                        .then(response => {
                            if (response.ok) {
                                // Remove successful mutation from storage
                                store.delete(mutation.id);
                                logSyncSuccess(mutation);
                            }
                            return response;
                        })
                        .catch(error => {
                            console.error('Failed to sync mutation:', error);
                            handleSyncFailure(mutation, error);
                            return null;
                        });
                });
                
                Promise.all(syncPromises).then(() => {
                    resolve();
                }).catch(reject);
            };
        };
        
        request.onerror = () => reject(request.error);
    });
}

// Sync with exponential backoff retry logic
function syncWithRetry(mutation, maxRetries = 3) {
    return new Promise((resolve, reject) => {
        let attempt = 0;
        
        function attemptSync() {
            attempt++;
            
            fetch(mutation.url, {
                method: mutation.method,
                headers: mutation.headers,
                body: mutation.body
            })
            .then(response => {
                if (response.ok) {
                    resolve(response);
                } else if (response.status >= 400 && response.status < 500) {
                    // Client error, don't retry
                    reject(new Error(`Client error: ${response.status}`));
                } else if (attempt < maxRetries) {
                    // Server error, retry with exponential backoff
                    const delay = Math.pow(2, attempt) * 1000; // 2^attempt seconds
                    setTimeout(attemptSync, delay);
                } else {
                    reject(new Error(`Max retries exceeded: ${response.status}`));
                }
            })
            .catch(error => {
                if (attempt < maxRetries) {
                    const delay = Math.pow(2, attempt) * 1000;
                    setTimeout(attemptSync, delay);
                } else {
                    reject(error);
                }
            });
        }
        
        attemptSync();
    });
}

// Handle sync failure
function handleSyncFailure(mutation, error) {
    // Update retry count
    mutation.retry_count = (mutation.retry_count || 0) + 1;
    
    // Check if we should give up on this mutation
    if (mutation.retry_count > 3) {
        // Move to failed mutations store for manual review
        moveToFailedMutations(mutation, error);
    } else {
        // Update mutation with new retry count
        updateMutationRetryCount(mutation);
    }
}

// Move failed mutations to separate store
function moveToFailedMutations(mutation, error) {
    const request = indexedDB.open('offline-mutations', 1);
    
    request.onsuccess = () => {
        const db = request.result;
        
        // Create failed mutations store if it doesn't exist
        if (!db.objectStoreNames.contains('failedMutations')) {
            const newVersion = db.version + 1;
            db.close();
            
            const upgradeRequest = indexedDB.open('offline-mutations', newVersion);
            upgradeRequest.onupgradeneeded = (event) => {
                const upgradedDb = event.target.result;
                if (!upgradedDb.objectStoreNames.contains('failedMutations')) {
                    upgradedDb.createObjectStore('failedMutations', { keyPath: 'id', autoIncrement: true });
                }
            };
            upgradeRequest.onsuccess = () => {
                const finalDb = upgradeRequest.result;
                const transaction = finalDb.transaction(['failedMutations'], 'readwrite');
                const store = transaction.objectStore('failedMutations');
                
                store.add({
                    ...mutation,
                    error: error.message,
                    failed_at: Date.now()
                });
            };
        } else {
            const transaction = db.transaction(['failedMutations'], 'readwrite');
            const store = transaction.objectStore('failedMutations');
            
            store.add({
                ...mutation,
                error: error.message,
                failed_at: Date.now()
            });
        }
    };
}

// Update mutation retry count
function updateMutationRetryCount(mutation) {
    const request = indexedDB.open('offline-mutations', 1);
    
    request.onsuccess = () => {
        const db = request.result;
        const transaction = db.transaction(['mutations'], 'readwrite');
        const store = transaction.objectStore('mutations');
        
        store.put(mutation);
    };
}

// Log successful sync
function logSyncSuccess(mutation) {
    const request = indexedDB.open('offline-mutations', 1);
    
    request.onsuccess = () => {
        const db = request.result;
        
        // Create sync log store if it doesn't exist
        if (!db.objectStoreNames.contains('syncLog')) {
            const newVersion = db.version + 1;
            db.close();
            
            const upgradeRequest = indexedDB.open('offline-mutations', newVersion);
            upgradeRequest.onupgradeneeded = (event) => {
                const upgradedDb = event.target.result;
                if (!upgradedDb.objectStoreNames.contains('syncLog')) {
                    const logStore = upgradedDb.createObjectStore('syncLog', { keyPath: 'id', autoIncrement: true });
                    logStore.createIndex('timestamp', 'timestamp', { unique: false });
                    logStore.createIndex('type', 'type', { unique: false });
                }
            };
            upgradeRequest.onsuccess = () => {
                const finalDb = upgradeRequest.result;
                const transaction = finalDb.transaction(['syncLog'], 'readwrite');
                const store = transaction.objectStore('syncLog');
                
                store.add({
                    mutation_id: mutation.id,
                    type: mutation.type || 'unknown',
                    url: mutation.url,
                    method: mutation.method,
                    synced_at: Date.now(),
                    retry_count: mutation.retry_count || 0
                });
            };
        } else {
            const transaction = db.transaction(['syncLog'], 'readwrite');
            const store = transaction.objectStore('syncLog');
            
            store.add({
                mutation_id: mutation.id,
                type: mutation.type || 'unknown',
                url: mutation.url,
                method: mutation.method,
                synced_at: Date.now(),
                retry_count: mutation.retry_count || 0
            });
        }
    };
}

// Specific sync functions for different data types
function syncOrderData() {
    console.log('Service Worker: Syncing order data');
    return syncOfflineMutations();
}

function syncInventoryData() {
    console.log('Service Worker: Syncing inventory data');
    return syncOfflineMutations();
}

function syncMenuData() {
    console.log('Service Worker: Syncing menu data');
    return syncOfflineMutations();
}

function syncUserData() {
    console.log('Service Worker: Syncing user data');
    return syncOfflineMutations();
}

// Conflict resolution function
function resolveConflict(localData, serverData, strategy = 'last-write-wins') {
    switch (strategy) {
        case 'last-write-wins':
            return localData.timestamp > serverData.timestamp ? localData : serverData;
        
        case 'server-wins':
            return serverData;
        
        case 'client-wins':
            return localData;
        
        case 'merge':
            return mergeData(localData, serverData);
        
        default:
            return localData.timestamp > serverData.timestamp ? localData : serverData;
    }
}

// Simple data merge function
function mergeData(localData, serverData) {
    const merged = { ...serverData };
    
    // Only merge specific fields that are safe to merge
    const mergeableFields = ['notes', 'description', 'tags'];
    
    mergeableFields.forEach(field => {
        if (localData[field] && localData[field] !== serverData[field]) {
            merged[field] = localData[field];
        }
    });
    
    return merged;
}

// Enhanced periodic cache cleanup with performance monitoring
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'CACHE_CLEANUP') {
        cleanupExpiredCache();
    } else if (event.data && event.data.type === 'PERFORMANCE_REPORT') {
        generatePerformanceReport();
    } else if (event.data && event.data.type === 'FORCE_SYNC') {
        syncAllData();
    }
});

// Enhanced cache cleanup with intelligent strategies
async function cleanupExpiredCache() {
    console.log('Service Worker: Starting cache cleanup');
    
    try {
        // Cleanup data cache
        await cleanupCacheByName(CACHE_CONFIG.DATA.name, CACHE_CONFIG.DATA.maxAge);
        
        // Cleanup runtime cache
        await cleanupCacheByName(CACHE_CONFIG.RUNTIME.name, CACHE_CONFIG.RUNTIME.maxAge);
        
        // Cleanup static cache (less aggressive)
        await cleanupCacheByName(CACHE_CONFIG.STATIC.name, CACHE_CONFIG.STATIC.maxAge);
        
        // Cleanup expired IndexedDB data
        await cleanupIndexedDB();
        
        // Check storage usage
        await checkStorageQuota();
        
        console.log('Service Worker: Cache cleanup completed');
    } catch (error) {
        console.error('Service Worker: Cache cleanup failed:', error);
    }
}

// Cleanup specific cache by name
async function cleanupCacheByName(cacheName, maxAge) {
    const cache = await caches.open(cacheName);
    const requests = await cache.keys();
    const now = Date.now();
    let deletedCount = 0;
    
    for (const request of requests) {
        const response = await cache.match(request);
        if (response) {
            const cacheTimestamp = response.headers.get('X-Cache-Timestamp');
            const responseDate = response.headers.get('date');
            
            let cacheTime;
            if (cacheTimestamp) {
                cacheTime = parseInt(cacheTimestamp);
            } else if (responseDate) {
                cacheTime = new Date(responseDate).getTime();
            } else {
                // Fallback to current time (will be kept)
                cacheTime = now;
            }
            
            if (now - cacheTime > maxAge) {
                await cache.delete(request);
                deletedCount++;
            }
        }
    }
    
    if (deletedCount > 0) {
        console.log(`Service Worker: Cleaned ${deletedCount} expired entries from ${cacheName}`);
    }
}

// Cleanup IndexedDB data
async function cleanupIndexedDB() {
    try {
        const db = await openIndexedDB('offline-mutations', 1);
        const now = Date.now();
        
        // Cleanup old sync logs
        if (db.objectStoreNames.contains('syncLog')) {
            const transaction = db.transaction(['syncLog'], 'readwrite');
            const store = transaction.objectStore('syncLog');
            const index = store.index('timestamp');
            const cutoffTime = now - (7 * 24 * 60 * 60 * 1000); // 7 days ago
            
            const range = IDBKeyRange.upperBound(cutoffTime);
            const oldEntries = await index.getAll(range);
            
            for (const entry of oldEntries) {
                await store.delete(entry.id);
            }
            
            if (oldEntries.length > 0) {
                console.log(`Service Worker: Cleaned ${oldEntries.length} old sync log entries`);
            }
        }
        
        // Cleanup failed syncs
        if (db.objectStoreNames.contains('failedSyncs')) {
            const transaction = db.transaction(['failedSyncs'], 'readwrite');
            const store = transaction.objectStore('failedSyncs');
            const index = store.index('timestamp');
            const cutoffTime = now - (30 * 24 * 60 * 60 * 1000); // 30 days ago
            
            const range = IDBKeyRange.upperBound(cutoffTime);
            const oldEntries = await index.getAll(range);
            
            for (const entry of oldEntries) {
                await store.delete(entry.id);
            }
            
            if (oldEntries.length > 0) {
                console.log(`Service Worker: Cleaned ${oldEntries.length} old failed sync entries`);
            }
        }
        
        db.close();
    } catch (error) {
        console.warn('Service Worker: IndexedDB cleanup failed:', error);
    }
}

// Helper to open IndexedDB
function openIndexedDB(name, version) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open(name, version);
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

// Check storage quota and optimize if needed
async function checkStorageQuota() {
    try {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            const estimate = await navigator.storage.estimate();
            const usagePercentage = (estimate.usage / estimate.quota) * 100;
            
            console.log(`Service Worker: Storage usage: ${usagePercentage.toFixed(2)}%`);
            
            if (usagePercentage > 80) {
                console.warn('Service Worker: Storage usage high, running aggressive cleanup');
                await aggressiveCleanup();
            }
            
            // Send storage info to clients
            const clients = await self.clients.matchAll();
            clients.forEach(client => {
                client.postMessage({
                    type: 'STORAGE_UPDATE',
                    data: {
                        usage: estimate.usage,
                        quota: estimate.quota,
                        percentage: usagePercentage
                    }
                });
            });
        }
    } catch (error) {
        console.warn('Service Worker: Failed to check storage quota:', error);
    }
}

// Aggressive cleanup when storage is full
async function aggressiveCleanup() {
    console.log('Service Worker: Running aggressive cleanup');
    
    try {
        // Clear runtime cache completely
        const runtimeCache = await caches.open(CACHE_CONFIG.RUNTIME.name);
        await runtimeCache.keys().then(requests => {
            return Promise.all(requests.map(request => runtimeCache.delete(request)));
        });
        
        // Reduce data cache size
        const dataCache = await caches.open(CACHE_CONFIG.DATA.name);
        const requests = await dataCache.keys();
        const sortedRequests = requests.sort((a, b) => {
            // Sort by URL priority - keep menu items, clear others
            const aPriority = getRequestPriority(a.url);
            const bPriority = getRequestPriority(b.url);
            return bPriority - aPriority;
        });
        
        // Keep only high priority items
        const keepCount = Math.floor(sortedRequests.length * 0.5); // Keep 50%
        const deleteRequests = sortedRequests.slice(keepCount);
        
        for (const request of deleteRequests) {
            await dataCache.delete(request);
        }
        
        console.log(`Service Worker: Aggressively cleaned ${deleteRequests.length} cache entries`);
    } catch (error) {
        console.error('Service Worker: Aggressive cleanup failed:', error);
    }
}

// Get request priority for cleanup
function getRequestPriority(url) {
    if (url.includes('/menu/')) return 10; // Highest priority
    if (url.includes('/tables/')) return 8;
    if (url.includes('/orders/')) return 7;
    if (url.includes('/inventory/')) return 6;
    if (url.includes('/api/offline/')) return 9; // High priority
    return 1; // Lowest priority
}

// Generate performance report
async function generatePerformanceReport() {
    try {
        const report = {
            timestamp: Date.now(),
            caches: {},
            storage: null,
            sync: {}
        };
        
        // Analyze cache sizes
        for (const [key, config] of Object.entries(CACHE_CONFIG)) {
            const cache = await caches.open(config.name);
            const requests = await cache.keys();
            report.caches[key] = {
                name: config.name,
                entries: requests.length,
                maxAge: config.maxAge,
                maxEntries: config.maxEntries
            };
        }
        
        // Get storage info
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            const estimate = await navigator.storage.estimate();
            report.storage = {
                used: estimate.usage,
                quota: estimate.quota,
                percentage: (estimate.usage / estimate.quota) * 100
            };
        }
        
        // Get sync status
        const db = await openIndexedDB('offline-mutations', 1);
        if (db.objectStoreNames.contains('mutations')) {
            const transaction = db.transaction(['mutations'], 'readonly');
            const store = transaction.objectStore('mutations');
            const mutations = await store.getAll();
            
            report.sync = {
                pendingMutations: mutations.length,
                criticalMutations: mutations.filter(m => m.priority === 'critical').length,
                highMutations: mutations.filter(m => m.priority === 'high').length,
                normalMutations: mutations.filter(m => m.priority === 'normal').length
            };
        }
        db.close();
        
        // Send report to clients
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'PERFORMANCE_REPORT',
                data: report
            });
        });
        
        console.log('Service Worker: Performance report generated', report);
    } catch (error) {
        console.error('Service Worker: Failed to generate performance report:', error);
    }
}