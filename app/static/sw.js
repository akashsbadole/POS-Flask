const CACHE_NAME = 'restaurant-pos-v2';
const DATA_CACHE_NAME = 'restaurant-pos-data-v2';
const STATIC_CACHE_NAME = 'restaurant-pos-static-v2';

// Critical static assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/static/css/style.css',
    '/static/js/app.js',
    '/static/images/logo.png',
    '/offline.html'
];

// API endpoints that support offline functionality
const OFFLINE_API_ENDPOINTS = [
    '/api/menu/items',
    '/api/menu/categories',
    '/api/cart/count',
    '/api/tables/status'
];

// Data that should be cached for offline use
const CACHEABLE_API_PATTERNS = [
    '/api/menu/',
    '/api/cart/',
    '/api/tables/'
];

// Install event - cache critical resources
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    
    event.waitUntil(
        Promise.all([
            // Cache static assets
            caches.open(STATIC_CACHE_NAME).then(cache => {
                return cache.addAll(STATIC_ASSETS);
            }),
            // Create data cache
            caches.open(DATA_CACHE_NAME)
        ])
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME && 
                        cacheName !== DATA_CACHE_NAME && 
                        cacheName !== STATIC_CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
});

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

// Push notifications
self.addEventListener('push', event => {
    console.log('Service Worker: Push received');
    
    const options = {
        body: event.data ? event.data.text() : 'New notification',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge.png',
        vibrate: [100, 50, 100],
        data: {
            dateOfArrival: Date.now(),
            primaryKey: 1
        }
    };
    
    event.waitUntil(
        self.registration.showNotification('Restaurant POS', options)
    );
});

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

// Periodic cache cleanup
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'CACHE_CLEANUP') {
        cleanupOldCacheEntries();
    }
});

function cleanupOldCacheEntries() {
    const MAX_AGE = 24 * 60 * 60 * 1000; // 24 hours
    
    caches.open(DATA_CACHE_NAME).then(cache => {
        cache.keys().then(requests => {
            requests.forEach(request => {
                if (request.url.includes('/api/')) {
                    cache.match(request).then(response => {
                        if (response) {
                            const date = response.headers.get('date');
                            if (date) {
                                const responseDate = new Date(date);
                                if (Date.now() - responseDate.getTime() > MAX_AGE) {
                                    cache.delete(request);
                                }
                            }
                        }
                    });
                }
            });
        });
    });
}