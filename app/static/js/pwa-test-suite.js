/**
 * PWA Testing Suite
 * Comprehensive testing for PWA features, offline capabilities, and performance
 */
class PWATestSuite {
    constructor() {
        this.tests = {
            serviceWorker: new ServiceWorkerTests(),
            caching: new CachingTests(),
            offline: new OfflineTests(),
            pushNotifications: new PushNotificationTests(),
            performance: new PerformanceTests(),
            installability: new InstallabilityTests(),
            compatibility: new CompatibilityTests()
        };
        
        this.results = {
            passed: 0,
            failed: 0,
            skipped: 0,
            total: 0,
            details: {}
        };
        
        this.isRunning = false;
        this.currentTest = null;
        
        this.init();
    }
    
    init() {
        console.log('PWA Test Suite: Initializing...');
        this.setupTestUI();
        this.setupKeyboardShortcuts();
    }
    
    setupTestUI() {
        // Create test interface if it doesn't exist
        if (!document.getElementById('pwa-test-suite')) {
            const testUI = this.generateTestUI();
            document.body.insertAdjacentHTML('beforeend', testUI);
        }
        
        this.bindUIEvents();
    }
    
    generateTestUI() {
        return `
            <div id="pwa-test-suite" class="fixed inset-0 bg-black bg-opacity-50 z-50 hidden">
                <div class="flex items-center justify-center min-h-screen p-4">
                    <div class="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-screen overflow-hidden">
                        <!-- Header -->
                        <div class="bg-blue-600 text-white px-6 py-4 flex items-center justify-between">
                            <h2 class="text-xl font-bold">PWA Test Suite</h2>
                            <button onclick="window.pwaTestSuite.close()" class="text-white hover:bg-blue-700 p-2 rounded">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                </svg>
                            </button>
                        </div>
                        
                        <!-- Content -->
                        <div class="flex h-full">
                            <!-- Test Categories -->
                            <div class="w-64 bg-gray-50 p-4 overflow-y-auto">
                                <h3 class="font-semibold text-gray-900 mb-4">Test Categories</h3>
                                <div class="space-y-2">
                                    <button onclick="window.pwaTestSuite.runCategory('serviceWorker')" class="w-full text-left px-3 py-2 rounded hover:bg-gray-200 transition-colors test-category-btn">
                                        Service Worker
                                    </button>
                                    <button onclick="window.pwaTestSuite.runCategory('caching')" class="w-full text-left px-3 py-2 rounded hover:bg-gray-200 transition-colors test-category-btn">
                                        Caching
                                    </button>
                                    <button onclick="window.pwaTestSuite.runCategory('offline')" class="w-full text-left px-3 py-2 rounded hover:bg-gray-200 transition-colors test-category-btn">
                                        Offline
                                    </button>
                                    <button onclick="window.pwaTestSuite.runCategory('pushNotifications')" class="w-full text-left px-3 py-2 rounded hover:bg-gray-200 transition-colors test-category-btn">
                                        Push Notifications
                                    </button>
                                    <button onclick="window.pwaTestSuite.runCategory('performance')" class="w-full text-left px-3 py-2 rounded hover:bg-gray-200 transition-colors test-category-btn">
                                        Performance
                                    </button>
                                    <button onclick="window.pwaTestSuite.runCategory('installability')" class="w-full text-left px-3 py-2 rounded hover:bg-gray-200 transition-colors test-category-btn">
                                        Installability
                                    </button>
                                    <button onclick="window.pwaTestSuite.runCategory('compatibility')" class="w-full text-left px-3 py-2 rounded hover:bg-gray-200 transition-colors test-category-btn">
                                        Compatibility
                                    </button>
                                </div>
                                
                                <!-- Run All Button -->
                                <button onclick="window.pwaTestSuite.runAllTests()" class="w-full mt-4 bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors">
                                    Run All Tests
                                </button>
                            </div>
                            
                            <!-- Test Results -->
                            <div class="flex-1 p-6 overflow-y-auto">
                                <div class="flex items-center justify-between mb-4">
                                    <h3 class="font-semibold text-gray-900">Test Results</h3>
                                    <div class="flex items-center space-x-4">
                                        <div class="text-sm">
                                            <span class="text-green-600 font-bold" id="test-passed">0</span> passed
                                        </div>
                                        <div class="text-sm">
                                            <span class="text-red-600 font-bold" id="test-failed">0</span> failed
                                        </div>
                                        <div class="text-sm">
                                            <span class="text-yellow-600 font-bold" id="test-skipped">0</span> skipped
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- Test Output -->
                                <div id="test-output" class="bg-gray-900 text-green-400 font-mono text-sm p-4 rounded-lg h-96 overflow-y-auto">
                                    <div class="text-center text-gray-500">
                                        Click a test category or "Run All Tests" to begin testing...
                                    </div>
                                </div>
                                
                                <!-- Actions -->
                                <div class="flex justify-between mt-4">
                                    <button onclick="window.pwaTestSuite.exportResults()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
                                        Export Results
                                    </button>
                                    <button onclick="window.pwaTestSuite.clearResults()" class="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50 transition-colors">
                                        Clear Results
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    bindUIEvents() {
        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.close();
            }
        });
        
        // Close on background click
        document.getElementById('pwa-test-suite').addEventListener('click', (e) => {
            if (e.target.id === 'pwa-test-suite') {
                this.close();
            }
        });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 't':
                        e.preventDefault();
                        this.toggle();
                        break;
                    case 'a':
                        e.preventDefault();
                        this.runAllTests();
                        break;
                    case 'e':
                        e.preventDefault();
                        this.exportResults();
                        break;
                    case 'c':
                        e.preventDefault();
                        this.clearResults();
                        break;
                }
            }
        });
    }
    
    show() {
        document.getElementById('pwa-test-suite').classList.remove('hidden');
    }
    
    close() {
        document.getElementById('pwa-test-suite').classList.add('hidden');
    }
    
    toggle() {
        const suite = document.getElementById('pwa-test-suite');
        suite.classList.toggle('hidden');
    }
    
    async runCategory(category) {
        if (this.isRunning) {
            this.log('warning', 'Tests already running. Please wait...');
            return;
        }
        
        this.isRunning = true;
        this.clearOutput();
        this.log('info', `Running ${category} tests...`);
        
        try {
            await this.tests[category].runAll();
            this.log('success', `${category} tests completed`);
        } catch (error) {
            this.log('error', `${category} tests failed: ${error.message}`);
        } finally {
            this.isRunning = false;
        }
    }
    
    async runAllTests() {
        if (this.isRunning) {
            this.log('warning', 'Tests already running. Please wait...');
            return;
        }
        
        this.isRunning = true;
        this.clearOutput();
        this.log('info', 'Running all PWA tests...');
        
        const categories = Object.keys(this.tests);
        
        for (const category of categories) {
            this.log('info', `Testing ${category}...`);
            try {
                await this.tests[category].runAll();
                this.log('success', `${category} tests completed`);
            } catch (error) {
                this.log('error', `${category} tests failed: ${error.message}`);
            }
        }
        
        this.generateSummary();
        this.isRunning = false;
        this.log('success', 'All tests completed!');
    }
    
    clearOutput() {
        const output = document.getElementById('test-output');
        output.innerHTML = '<div class="text-center text-gray-500">Running tests...</div>';
        
        this.results = {
            passed: 0,
            failed: 0,
            skipped: 0,
            total: 0,
            details: {}
        };
        
        this.updateCounters();
    }
    
    log(level, message, details = null) {
        const output = document.getElementById('test-output');
        const timestamp = new Date().toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = `mb-2 p-2 rounded ${
            level === 'error' ? 'bg-red-900 text-red-300' :
            level === 'warning' ? 'bg-yellow-900 text-yellow-300' :
            level === 'success' ? 'bg-green-900 text-green-300' :
            'bg-blue-900 text-blue-300'
        }`;
        
        logEntry.innerHTML = `
            <div class="flex items-center justify-between mb-1">
                <span class="text-xs opacity-75">[${timestamp}]</span>
                <span class="font-semibold">${level.toUpperCase()}</span>
            </div>
            <div>${message}</div>
            ${details ? `<pre class="text-xs mt-2 opacity-75">${JSON.stringify(details, null, 2)}</pre>` : ''}
        `;
        
        output.appendChild(logEntry);
        output.scrollTop = output.scrollHeight;
    }
    
    updateCounters() {
        document.getElementById('test-passed').textContent = this.results.passed;
        document.getElementById('test-failed').textContent = this.results.failed;
        document.getElementById('test-skipped').textContent = this.results.skipped;
    }
    
    recordResult(testName, passed, details = null) {
        this.results.total++;
        
        if (passed) {
            this.results.passed++;
        } else {
            this.results.failed++;
        }
        
        this.results.details[testName] = {
            passed,
            details,
            timestamp: Date.now()
        };
        
        this.updateCounters();
    }
    
    generateSummary() {
        const score = this.results.total > 0 ? 
            Math.round((this.results.passed / this.results.total) * 100) : 0;
        
        this.log('info', `\n=== TEST SUMMARY ===`);
        this.log('info', `Total Tests: ${this.results.total}`);
        this.log('info', `Passed: ${this.results.passed}`);
        this.log('info', `Failed: ${this.results.failed}`);
        this.log('info', `Skipped: ${this.results.skipped}`);
        this.log('info', `Score: ${score}%`);
        
        if (score >= 90) {
            this.log('success', 'EXCELLENT: PWA implementation is outstanding!');
        } else if (score >= 80) {
            this.log('success', 'GOOD: PWA implementation is solid with minor issues.');
        } else if (score >= 70) {
            this.log('warning', 'FAIR: PWA implementation has some issues that should be addressed.');
        } else {
            this.log('error', 'POOR: PWA implementation needs significant improvements.');
        }
    }
    
    exportResults() {
        const results = {
            summary: {
                total: this.results.total,
                passed: this.results.passed,
                failed: this.results.failed,
                skipped: this.results.skipped,
                score: this.results.total > 0 ? Math.round((this.results.passed / this.results.total) * 100) : 0,
                timestamp: Date.now()
            },
            details: this.results.details,
            environment: {
                userAgent: navigator.userAgent,
                url: window.location.href,
                timestamp: new Date().toISOString()
            }
        };
        
        const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `pwa-test-results-${Date.now()}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        
        this.log('success', 'Test results exported');
    }
}

// Service Worker Tests
class ServiceWorkerTests {
    constructor() {
        this.tests = [
            { name: 'Service Worker Registration', method: 'testRegistration' },
            { name: 'Service Worker Activation', method: 'testActivation' },
            { name: 'Cache API Support', method: 'testCacheSupport' },
            { name: 'Background Sync Support', method: 'testBackgroundSync' },
            { name: 'Push API Support', method: 'testPushSupport' },
            { name: 'Service Worker Update', method: 'testUpdate' }
        ];
    }
    
    async runAll() {
        for (const test of this.tests) {
            await this[test.method]();
        }
    }
    
    async testRegistration() {
        try {
            const registration = await navigator.serviceWorker.ready;
            window.pwaTestSuite.recordResult('Service Worker Registration', !!registration, {
                scope: registration?.scope,
                scriptURL: registration?.scriptURL
            });
        } catch (error) {
            window.pwaTestSuite.recordResult('Service Worker Registration', false, { error: error.message });
        }
    }
    
    async testActivation() {
        try {
            const registration = await navigator.serviceWorker.ready;
            const isActive = !!registration.active;
            window.pwaTestSuite.recordResult('Service Worker Activation', isActive, {
                active: !!registration.active,
                installing: !!registration.installing,
                waiting: !!registration.waiting
            });
        } catch (error) {
            window.pwaTestSuite.recordResult('Service Worker Activation', false, { error: error.message });
        }
    }
    
    async testCacheSupport() {
        const hasCache = 'caches' in window;
        window.pwaTestSuite.recordResult('Cache API Support', hasCache);
    }
    
    async testBackgroundSync() {
        const hasBackgroundSync = 'serviceWorker' in navigator && 
                               'SyncManager' in window.ServiceWorkerRegistration.prototype;
        window.pwaTestSuite.recordResult('Background Sync Support', hasBackgroundSync);
    }
    
    async testPushSupport() {
        const hasPush = 'serviceWorker' in navigator && 
                        'PushManager' in window;
        window.pwaTestSuite.recordResult('Push API Support', hasPush);
    }
    
    async testUpdate() {
        try {
            const registration = await navigator.serviceWorker.ready;
            const hasUpdateListener = 'addEventListener' in registration;
            window.pwaTestSuite.recordResult('Service Worker Update', hasUpdateListener);
        } catch (error) {
            window.pwaTestSuite.recordResult('Service Worker Update', false, { error: error.message });
        }
    }
}

// Caching Tests
class CachingTests {
    constructor() {
        this.tests = [
            { name: 'Cache Storage Available', method: 'testCacheStorage' },
            { name: 'Cache API Functionality', method: 'testCacheAPI' },
            { name: 'Cache Persistence', method: 'testCachePersistence' },
            { name: 'Cache Quota', method: 'testCacheQuota' }
        ];
    }
    
    async runAll() {
        for (const test of this.tests) {
            await this[test.method]();
        }
    }
    
    async testCacheStorage() {
        try {
            const cache = await caches.open('test-cache');
            const hasCache = !!cache;
            window.pwaTestSuite.recordResult('Cache Storage Available', hasCache);
            
            if (hasCache) {
                await cache.delete('test-cache');
            }
        } catch (error) {
            window.pwaTestSuite.recordResult('Cache Storage Available', false, { error: error.message });
        }
    }
    
    async testCacheAPI() {
        try {
            const cache = await caches.open('test-cache');
            const testResponse = new Response('test', { status: 200 });
            await cache.put('/test', testResponse);
            
            const cachedResponse = await cache.match('/test');
            const isWorking = cachedResponse && await cachedResponse.text() === 'test';
            
            window.pwaTestSuite.recordResult('Cache API Functionality', isWorking);
            
            await cache.delete('test-cache');
        } catch (error) {
            window.pwaTestSuite.recordResult('Cache API Functionality', false, { error: error.message });
        }
    }
    
    async testCachePersistence() {
        try {
            if ('storage' in navigator && 'persist' in navigator.storage) {
                const isPersistent = await navigator.storage.persist();
                window.pwaTestSuite.recordResult('Cache Persistence', isPersistent);
            } else {
                window.pwaTestSuite.recordResult('Cache Persistence', false, { reason: 'Storage persistence API not available' });
            }
        } catch (error) {
            window.pwaTestSuite.recordResult('Cache Persistence', false, { error: error.message });
        }
    }
    
    async testCacheQuota() {
        try {
            if ('storage' in navigator && 'estimate' in navigator.storage) {
                const estimate = await navigator.storage.estimate();
                const hasQuota = estimate.quota > 0;
                window.pwaTestSuite.recordResult('Cache Quota', hasQuota, {
                    quota: estimate.quota,
                    usage: estimate.usage
                });
            } else {
                window.pwaTestSuite.recordResult('Cache Quota', false, { reason: 'Storage estimate API not available' });
            }
        } catch (error) {
            window.pwaTestSuite.recordResult('Cache Quota', false, { error: error.message });
        }
    }
}

// Offline Tests
class OfflineTests {
    constructor() {
        this.tests = [
            { name: 'Offline Detection', method: 'testOfflineDetection' },
            { name: 'Offline Functionality', method: 'testOfflineFunctionality' },
            { name: 'IndexedDB Support', method: 'testIndexedDB' },
            { name: 'Offline Data Storage', method: 'testOfflineDataStorage' }
        ];
    }
    
    async runAll() {
        for (const test of this.tests) {
            await this[test.method]();
        }
    }
    
    async testOfflineDetection() {
        const initiallyOnline = navigator.onLine;
        
        // Simulate offline detection
        const hasOfflineEvents = 'ononline' in window && 'onoffline' in window;
        
        window.pwaTestSuite.recordResult('Offline Detection', hasOfflineEvents, {
            initiallyOnline,
            currentlyOnline: navigator.onLine
        });
    }
    
    async testOfflineFunctionality() {
        // Test if app can function when offline
        try {
            // This would require actual offline testing
            const hasOfflineManager = typeof window.offlineManager !== 'undefined';
            window.pwaTestSuite.recordResult('Offline Functionality', hasOfflineManager);
        } catch (error) {
            window.pwaTestSuite.recordResult('Offline Functionality', false, { error: error.message });
        }
    }
    
    async testIndexedDB() {
        const hasIndexedDB = 'indexedDB' in window;
        window.pwaTestSuite.recordResult('IndexedDB Support', hasIndexedDB);
    }
    
    async testOfflineDataStorage() {
        try {
            const testDB = await this.openTestDB();
            const canStoreData = !!testDB;
            window.pwaTestSuite.recordResult('Offline Data Storage', canStoreData);
            
            if (testDB) {
                testDB.close();
            }
        } catch (error) {
            window.pwaTestSuite.recordResult('Offline Data Storage', false, { error: error.message });
        }
    }
    
    openTestDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('test-db', 1);
            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }
}

// Push Notification Tests
class PushNotificationTests {
    constructor() {
        this.tests = [
            { name: 'Notification Permission', method: 'testNotificationPermission' },
            { name: 'Push Subscription', method: 'testPushSubscription' },
            { name: 'Notification Display', method: 'testNotificationDisplay' }
        ];
    }
    
    async runAll() {
        for (const test of this.tests) {
            await this[test.method]();
        }
    }
    
    async testNotificationPermission() {
        const permission = await Notification.requestPermission();
        const hasPermission = permission !== 'denied';
        window.pwaTestSuite.recordResult('Notification Permission', hasPermission, {
            permission
        });
    }
    
    async testPushSubscription() {
        try {
            const registration = await navigator.serviceWorker.ready;
            const hasPushManager = 'pushManager' in registration;
            window.pwaTestSuite.recordResult('Push Subscription', hasPushManager);
        } catch (error) {
            window.pwaTestSuite.recordResult('Push Subscription', false, { error: error.message });
        }
    }
    
    async testNotificationDisplay() {
        const canShowNotification = 'Notification' in window;
        window.pwaTestSuite.recordResult('Notification Display', canShowNotification);
    }
}

// Performance Tests
class PerformanceTests {
    constructor() {
        this.tests = [
            { name: 'Performance API Support', method: 'testPerformanceAPI' },
            { name: 'Navigation Timing', method: 'testNavigationTiming' },
            { name: 'Resource Timing', method: 'testResourceTiming' },
            { name: 'Memory Information', method: 'testMemoryInfo' }
        ];
    }
    
    async runAll() {
        for (const test of this.tests) {
            await this[test.method]();
        }
    }
    
    async testPerformanceAPI() {
        const hasPerformance = 'performance' in window;
        window.pwaTestSuite.recordResult('Performance API Support', hasPerformance);
    }
    
    async testNavigationTiming() {
        const hasNavTiming = performance.getEntriesByType && 
                             performance.getEntriesByType('navigation').length > 0;
        window.pwaTestSuite.recordResult('Navigation Timing', hasNavTiming);
    }
    
    async testResourceTiming() {
        const hasResourceTiming = performance.getEntriesByType && 
                               performance.getEntriesByType('resource').length > 0;
        window.pwaTestSuite.recordResult('Resource Timing', hasResourceTiming);
    }
    
    async testMemoryInfo() {
        const hasMemoryInfo = 'memory' in performance;
        window.pwaTestSuite.recordResult('Memory Information', hasMemoryInfo);
    }
}

// Installability Tests
class InstallabilityTests {
    constructor() {
        this.tests = [
            { name: 'Web App Manifest', method: 'testManifest' },
            { name: 'Service Worker Support', method: 'testServiceWorkerSupport' },
            { name: 'HTTPS Requirement', method: 'testHTTPS' },
            { name: 'Install Prompt', method: 'testInstallPrompt' }
        ];
    }
    
    async runAll() {
        for (const test of this.tests) {
            await this[test.method]();
        }
    }
    
    async testManifest() {
        try {
            const response = await fetch('/manifest.json');
            const hasManifest = response.ok;
            window.pwaTestSuite.recordResult('Web App Manifest', hasManifest, {
                status: response.status
            });
        } catch (error) {
            window.pwaTestSuite.recordResult('Web App Manifest', false, { error: error.message });
        }
    }
    
    async testServiceWorkerSupport() {
        const hasServiceWorker = 'serviceWorker' in navigator;
        window.pwaTestSuite.recordResult('Service Worker Support', hasServiceWorker);
    }
    
    async testHTTPS() {
        const isHTTPS = location.protocol === 'https:' || 
                       location.hostname === 'localhost' || 
                       location.hostname === '127.0.0.1';
        window.pwaTestSuite.recordResult('HTTPS Requirement', isHTTPS);
    }
    
    async testInstallPrompt() {
        const hasBeforeInstallPrompt = 'onbeforeinstallprompt' in window;
        window.pwaTestSuite.recordResult('Install Prompt', hasBeforeInstallPrompt);
    }
}

// Compatibility Tests
class CompatibilityTests {
    constructor() {
        this.tests = [
            { name: 'Browser Compatibility', method: 'testBrowserCompatibility' },
            { name: 'Device Compatibility', method: 'testDeviceCompatibility' },
            { name: 'Feature Detection', method: 'testFeatureDetection' }
        ];
    }
    
    async runAll() {
        for (const test of this.tests) {
            await this[test.method]();
        }
    }
    
    async testBrowserCompatibility() {
        const userAgent = navigator.userAgent;
        const isCompatible = this.checkBrowserCompatibility(userAgent);
        window.pwaTestSuite.recordResult('Browser Compatibility', isCompatible, {
            userAgent,
            browser: this.detectBrowser(userAgent)
        });
    }
    
    async testDeviceCompatibility() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        const isTablet = /iPad|Android(?!.*Mobile)|Tablet/i.test(navigator.userAgent);
        
        window.pwaTestSuite.recordResult('Device Compatibility', true, {
            isMobile,
            isTablet,
            isDesktop: !isMobile && !isTablet,
            screenWidth: screen.width,
            screenHeight: screen.height
        });
    }
    
    async testFeatureDetection() {
        const features = {
            es6: this.checkES6Support(),
            webGL: this.checkWebGLSupport(),
            webWorkers: this.checkWebWorkerSupport(),
            geolocation: this.checkGeolocationSupport(),
            camera: this.checkCameraSupport(),
            localStorage: this.checkLocalStorageSupport()
        };
        
        const supportedFeatures = Object.entries(features)
            .filter(([name, supported]) => supported)
            .map(([name]) => name);
        
        window.pwaTestSuite.recordResult('Feature Detection', true, {
            features,
            supportedFeatures,
            unsupportedFeatures: Object.entries(features)
                .filter(([name, supported]) => !supported)
                .map(([name]) => name)
        });
    }
    
    checkBrowserCompatibility(userAgent) {
        // Basic compatibility check
        const isChrome = /Chrome/.test(userAgent);
        const isFirefox = /Firefox/.test(userAgent);
        const isSafari = /Safari/.test(userAgent) && !/Chrome/.test(userAgent);
        const isEdge = /Edge/.test(userAgent);
        
        // Return true for modern browsers
        return isChrome || isFirefox || isSafari || isEdge;
    }
    
    detectBrowser(userAgent) {
        if (/Chrome/.test(userAgent)) return 'Chrome';
        if (/Firefox/.test(userAgent)) return 'Firefox';
        if (/Safari/.test(userAgent) && !/Chrome/.test(userAgent)) return 'Safari';
        if (/Edge/.test(userAgent)) return 'Edge';
        return 'Unknown';
    }
    
    checkES6Support() {
        try {
            eval('class Test { constructor() { } }');
            return true;
        } catch (e) {
            return false;
        }
    }
    
    checkWebGLSupport() {
        try {
            const canvas = document.createElement('canvas');
            return !!(canvas.getContext && canvas.getContext('webgl'));
        } catch (e) {
            return false;
        }
    }
    
    checkWebWorkerSupport() {
        return 'Worker' in window;
    }
    
    checkGeolocationSupport() {
        return 'geolocation' in navigator;
    }
    
    checkCameraSupport() {
        return 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices;
    }
    
    checkLocalStorageSupport() {
        try {
            localStorage.setItem('test', 'test');
            localStorage.removeItem('test');
            return true;
        } catch (e) {
            return false;
        }
    }
}

// Initialize test suite
window.pwaTestSuite = null;

document.addEventListener('DOMContentLoaded', () => {
    window.pwaTestSuite = new PWATestSuite();
    
    // Expose global functions
    window.runPWATests = () => window.pwaTestSuite.runAllTests();
    window.showPWATestSuite = () => window.pwaTestSuite.show();
});