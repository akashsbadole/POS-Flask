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
    console.log('Service Worker: Background sync triggered');
    
    if (event.tag === 'offline-mutations') {
        event.waitUntil(syncOfflineMutations());
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
        // Store mutation for later sync
        const mutation = {
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body: request.body,
            timestamp: Date.now()
        };
        
        // Store in IndexedDB for later sync
        storeOfflineMutation(mutation).then(() => {
            // Return immediate response for optimistic UI updates
            resolve(new Response(
                JSON.stringify({ 
                    success: true, 
                    offline: true, 
                    message: 'Action will be synced when online' 
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

// Store offline mutations in IndexedDB
function storeOfflineMutation(mutation) {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('offline-mutations', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const db = request.result;
            const transaction = db.transaction(['mutations'], 'readwrite');
            const store = transaction.objectStore('mutations');
            
            store.add(mutation);
            
            transaction.oncomplete = () => resolve();
            transaction.onerror = () => reject(transaction.error);
        };
        
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('mutations')) {
                db.createObjectStore('mutations', { keyPath: 'id', autoIncrement: true });
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
                
                // Sync each mutation
                const syncPromises = mutations.map(mutation => {
                    return fetch(mutation.url, {
                        method: mutation.method,
                        headers: mutation.headers,
                        body: mutation.body
                    }).then(response => {
                        if (response.ok) {
                            // Remove successful mutation from storage
                            store.delete(mutation.id);
                        }
                        return response;
                    }).catch(error => {
                        console.error('Failed to sync mutation:', error);
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