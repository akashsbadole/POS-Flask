/**
 * Performance Monitoring System for PWA
 * Tracks and reports on app performance, user interactions, and system health
 */
class PerformanceMonitor {
    constructor() {
        this.metrics = {
            navigation: {
                startTime: 0,
                loadTime: 0,
                renderTime: 0,
                firstContentfulPaint: 0,
                firstMeaningfulPaint: 0,
                largestContentfulPaint: 0
            },
            resources: {
                totalRequests: 0,
                totalSize: 0,
                cachedRequests: 0,
                failedRequests: 0,
                slowRequests: 0
            },
            user: {
                interactions: 0,
                errors: 0,
                sessionDuration: 0,
                pageViews: 0
            },
            system: {
                memoryUsage: 0,
                storageUsage: 0,
                connectionType: 'unknown',
                deviceInfo: this.getDeviceInfo()
            },
            pwa: {
                cacheHitRate: 0,
                syncStatus: 'idle',
                offlineTime: 0,
                installStatus: 'not-installed'
            }
        };
        
        this.thresholds = {
            slowRequest: 2000, // 2 seconds
            largeResource: 1024 * 1024, // 1MB
            memoryWarning: 0.8, // 80%
            storageWarning: 0.9 // 90%
        };
        
        this.observers = [];
        this.reportInterval = null;
        this.isTracking = false;
        
        this.init();
    }
    
    init() {
        try {
            console.log('Performance Monitor: Initializing...');
            
            // Start tracking
            this.startTracking();
            
            // Setup performance observers
            this.setupPerformanceObservers();
            
            // Setup user interaction tracking
            this.setupUserTracking();
            
            // Setup system monitoring
            this.setupSystemMonitoring();
            
            // Setup periodic reporting
            this.setupPeriodicReporting();
            
            // Setup error tracking
            this.setupErrorTracking();
            
            console.log('Performance Monitor: Initialized successfully');
        } catch (error) {
            console.error('Performance Monitor: Initialization failed', error);
        }
    }
    
    startTracking() {
        if (this.isTracking) return;
        
        this.isTracking = true;
        this.metrics.navigation.startTime = performance.now();
        this.metrics.user.sessionDuration = 0;
        this.metrics.user.pageViews = 1;
        
        // Track page load
        this.trackPageLoad();
    }
    
    setupPerformanceObservers() {
        // Navigation timing
        if ('PerformanceObserver' in window) {
            // Navigation timing observer
            const navigationObserver = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                entries.forEach(entry => {
                    if (entry.entryType === 'navigation') {
                        this.metrics.navigation.loadTime = entry.loadEventEnd - entry.fetchStart;
                        this.metrics.navigation.firstContentfulPaint = entry.firstContentfulPaint;
                        this.metrics.navigation.firstMeaningfulPaint = entry.firstMeaningfulPaint;
                        this.metrics.navigation.largestContentfulPaint = entry.largestContentfulPaint;
                    }
                });
            });
            
            navigationObserver.observe({ entryTypes: ['navigation'] });
            this.observers.push(navigationObserver);
            
            // Resource timing observer
            const resourceObserver = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                entries.forEach(entry => {
                    this.trackResourceLoad(entry);
                });
            });
            
            resourceObserver.observe({ entryTypes: ['resource'] });
            this.observers.push(resourceObserver);
            
            // Paint timing observer
            const paintObserver = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                entries.forEach(entry => {
                    if (entry.name === 'first-contentful-paint') {
                        this.metrics.navigation.firstContentfulPaint = entry.startTime;
                    }
                    if (entry.name === 'first-meaningful-paint') {
                        this.metrics.navigation.firstMeaningfulPaint = entry.startTime;
                    }
                    if (entry.name === 'largest-contentful-paint') {
                        this.metrics.navigation.largestContentfulPaint = entry.startTime;
                    }
                });
            });
            
            paintObserver.observe({ entryTypes: ['paint'] });
            this.observers.push(paintObserver);
        }
    }
    
    trackPageLoad() {
        // Track when page is fully loaded
        window.addEventListener('load', () => {
            this.metrics.navigation.renderTime = performance.now() - this.metrics.navigation.startTime;
            
            // Calculate navigation metrics
            this.calculateNavigationMetrics();
        });
        
        // Track when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                const domReadyTime = performance.now() - this.metrics.navigation.startTime;
                console.log(`Performance Monitor: DOM ready in ${domReadyTime.toFixed(2)}ms`);
            });
        }
    }
    
    calculateNavigationMetrics() {
        const nav = performance.getEntriesByType('navigation')[0];
        if (nav) {
            this.metrics.navigation = {
                ...this.metrics.navigation,
                dnsLookup: nav.domainLookupEnd - nav.domainLookupStart,
                tcpConnect: nav.connectEnd - nav.connectStart,
                serverResponse: nav.responseEnd - nav.requestStart,
                domProcessing: nav.domContentLoadedEventStart - nav.responseEnd,
                pageLoad: nav.loadEventEnd - nav.domContentLoadedEventStart
            };
        }
    }
    
    trackResourceLoad(entry) {
        this.metrics.resources.totalRequests++;
        
        if (entry.transferSize) {
            this.metrics.resources.totalSize += entry.transferSize;
        }
        
        // Check if resource was cached
        if (entry.transferSize === 0 && entry.decodedBodySize > 0) {
            this.metrics.resources.cachedRequests++;
        }
        
        // Check for slow requests
        if (entry.duration > this.thresholds.slowRequest) {
            this.metrics.resources.slowRequests++;
            console.warn(`Performance Monitor: Slow resource detected`, {
                url: entry.name,
                duration: entry.duration,
                size: entry.transferSize
            });
        }
        
        // Check for large resources
        if (entry.transferSize > this.thresholds.largeResource) {
            console.warn(`Performance Monitor: Large resource detected`, {
                url: entry.name,
                size: entry.transferSize
            });
        }
    }
    
    setupUserTracking() {
        // Track user interactions
        let interactionTimeout;
        
        document.addEventListener('click', () => {
            this.metrics.user.interactions++;
            clearTimeout(interactionTimeout);
            
            interactionTimeout = setTimeout(() => {
                this.trackUserEngagement();
            }, 1000);
        });
        
        // Track scroll depth
        let maxScrollDepth = 0;
        window.addEventListener('scroll', () => {
            const scrollDepth = Math.round(
                (window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100
            );
            maxScrollDepth = Math.max(maxScrollDepth, scrollDepth);
        });
        
        // Track session duration
        this.metrics.user.sessionDuration = Date.now();
        
        // Track page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page hidden - pause session tracking
                this.trackPageView(false);
            } else {
                // Page visible - resume session tracking
                this.trackPageView(true);
            }
        });
    }
    
    trackUserEngagement() {
        // Send engagement metrics
        this.sendMetrics({
            type: 'user_engagement',
            data: {
                interactions: this.metrics.user.interactions,
                sessionDuration: Date.now() - this.metrics.user.sessionDuration,
                pageViews: this.metrics.user.pageViews
            }
        });
    }
    
    trackPageView(isNewView = true) {
        if (isNewView) {
            this.metrics.user.pageViews++;
        }
    }
    
    setupSystemMonitoring() {
        // Monitor memory usage
        this.monitorMemoryUsage();
        
        // Monitor storage usage
        this.monitorStorageUsage();
        
        // Monitor connection quality
        this.monitorConnectionQuality();
        
        // Monitor battery level (if available)
        this.monitorBatteryLevel();
    }
    
    monitorMemoryUsage() {
        if ('memory' in performance) {
            const memoryInfo = performance.memory;
            this.metrics.system.memoryUsage = memoryInfo.usedJSHeapSize / memoryInfo.jsHeapSizeLimit;
            
            // Check memory threshold
            if (this.metrics.system.memoryUsage > this.thresholds.memoryWarning) {
                console.warn(`Performance Monitor: High memory usage: ${(this.metrics.system.memoryUsage * 100).toFixed(1)}%`);
                this.triggerMemoryOptimization();
            }
        }
    }
    
    monitorStorageUsage() {
        if ('storage' in navigator && 'estimate' in navigator.storage) {
            navigator.storage.estimate().then(estimate => {
                this.metrics.system.storageUsage = estimate.usage / estimate.quota;
                
                // Check storage threshold
                if (this.metrics.system.storageUsage > this.thresholds.storageWarning) {
                    console.warn(`Performance Monitor: High storage usage: ${(this.metrics.system.storageUsage * 100).toFixed(1)}%`);
                    this.triggerStorageCleanup();
                }
            });
        }
    }
    
    monitorConnectionQuality() {
        if ('connection' in navigator) {
            const connection = navigator.connection;
            this.metrics.system.connectionType = connection.effectiveType || 'unknown';
            
            // Monitor connection changes
            connection.addEventListener('change', () => {
                this.metrics.system.connectionType = connection.effectiveType;
                this.trackConnectionQuality();
            });
            
            this.trackConnectionQuality();
        }
    }
    
    trackConnectionQuality() {
        const connection = navigator.connection;
        
        this.sendMetrics({
            type: 'connection_quality',
            data: {
                type: connection.effectiveType,
                downlink: connection.downlink,
                rtt: connection.rtt,
                saveData: connection.saveData
            }
        });
    }
    
    monitorBatteryLevel() {
        if ('getBattery' in navigator) {
            navigator.getBattery().then(battery => {
                const trackBatteryLevel = () => {
                    this.sendMetrics({
                        type: 'battery_level',
                        data: {
                            level: battery.level,
                            charging: battery.charging
                        }
                    });
                };
                
                trackBatteryLevel();
                
                battery.addEventListener('levelchange', trackBatteryLevel);
                battery.addEventListener('chargingchange', trackBatteryLevel);
            });
        }
    }
    
    setupErrorTracking() {
        // Track JavaScript errors
        window.addEventListener('error', (event) => {
            this.metrics.user.errors++;
            
            this.sendMetrics({
                type: 'javascript_error',
                data: {
                    message: event.message,
                    filename: event.filename,
                    lineno: event.lineno,
                    colno: event.colno,
                    stack: event.error ? event.error.stack : null
                }
            });
        });
        
        // Track unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            this.metrics.user.errors++;
            
            this.sendMetrics({
                type: 'promise_rejection',
                data: {
                    reason: event.reason,
                    promise: event.promise
                }
            });
        });
        
        // Track resource loading errors
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.metrics.resources.failedRequests++;
                
                this.sendMetrics({
                    type: 'resource_error',
                    data: {
                        element: event.target.tagName,
                        source: event.target.src || event.target.href,
                        type: event.target.type
                    }
                });
            }
        }, true);
    }
    
    setupPeriodicReporting() {
        // Send metrics every 30 seconds
        this.reportInterval = setInterval(() => {
            this.calculateCurrentMetrics();
            this.sendPeriodicReport();
        }, 30000);
    }
    
    calculateCurrentMetrics() {
        // Calculate cache hit rate
        if (this.metrics.resources.totalRequests > 0) {
            this.metrics.pwa.cacheHitRate = 
                (this.metrics.resources.cachedRequests / this.metrics.resources.totalRequests) * 100;
        }
        
        // Update session duration
        this.metrics.user.sessionDuration = Date.now() - this.metrics.user.sessionDuration;
    }
    
    sendPeriodicReport() {
        this.sendMetrics({
            type: 'periodic_report',
            data: {
                navigation: this.metrics.navigation,
                resources: {
                    total: this.metrics.resources.totalRequests,
                    cached: this.metrics.resources.cachedRequests,
                    failed: this.metrics.resources.failedRequests,
                    slow: this.metrics.resources.slowRequests,
                    cacheHitRate: this.metrics.pwa.cacheHitRate
                },
                user: {
                    interactions: this.metrics.user.interactions,
                    errors: this.metrics.user.errors,
                    sessionDuration: this.metrics.user.sessionDuration,
                    pageViews: this.metrics.user.pageViews
                },
                system: {
                    memoryUsage: this.metrics.system.memoryUsage,
                    storageUsage: this.metrics.system.storageUsage,
                    connectionType: this.metrics.system.connectionType
                },
                pwa: {
                    cacheHitRate: this.metrics.pwa.cacheHitRate,
                    syncStatus: this.metrics.pwa.syncStatus,
                    offlineTime: this.metrics.pwa.offlineTime,
                    installStatus: this.metrics.pwa.installStatus
                }
            }
        });
    }
    
    async sendMetrics(data) {
        try {
            // Only send if online
            if (navigator.onLine) {
                const response = await fetch('/api/analytics/performance', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        ...data,
                        timestamp: Date.now(),
                        url: window.location.href,
                        userAgent: navigator.userAgent
                    })
                });
                
                if (!response.ok) {
                    console.warn('Performance Monitor: Failed to send metrics', response.status);
                }
            } else {
                // Queue metrics for later sending if offline
                this.queueMetricsForLater(data);
            }
        } catch (error) {
            console.error('Performance Monitor: Failed to send metrics', error);
            this.queueMetricsForLater(data);
        }
    }
    
    queueMetricsForLater(data) {
        try {
            const queuedMetrics = JSON.parse(localStorage.getItem('queued-metrics') || '[]');
            queuedMetrics.push({
                ...data,
                queuedAt: Date.now()
            });
            
            // Keep only last 50 entries
            if (queuedMetrics.length > 50) {
                queuedMetrics.splice(0, queuedMetrics.length - 50);
            }
            
            localStorage.setItem('queued-metrics', JSON.stringify(queuedMetrics));
        } catch (error) {
            console.warn('Performance Monitor: Failed to queue metrics', error);
        }
    }
    
    async sendQueuedMetrics() {
        if (!navigator.onLine) return;
        
        try {
            const queuedMetrics = JSON.parse(localStorage.getItem('queued-metrics') || '[]');
            
            if (queuedMetrics.length > 0) {
                const response = await fetch('/api/analytics/performance/batch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        metrics: queuedMetrics
                    })
                });
                
                if (response.ok) {
                    localStorage.removeItem('queued-metrics');
                    console.log(`Performance Monitor: Sent ${queuedMetrics.length} queued metrics`);
                }
            }
        } catch (error) {
            console.error('Performance Monitor: Failed to send queued metrics', error);
        }
    }
    
    triggerMemoryOptimization() {
        // Send signal to service worker for memory optimization
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then(registration => {
                registration.active.postMessage({
                    type: 'MEMORY_OPTIMIZATION',
                    data: {
                        usage: this.metrics.system.memoryUsage
                    }
                });
            });
        }
    }
    
    triggerStorageCleanup() {
        // Send signal to service worker for storage cleanup
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.ready.then(registration => {
                registration.active.postMessage({
                    type: 'STORAGE_CLEANUP'
                });
            });
        }
    }
    
    getDeviceInfo() {
        return {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            screen: {
                width: screen.width,
                height: screen.height,
                colorDepth: screen.colorDepth,
                pixelDepth: screen.pixelDepth
            },
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            deviceMemory: navigator.deviceMemory,
            hardwareConcurrency: navigator.hardwareConcurrency,
            connection: navigator.connection ? {
                effectiveType: navigator.connection.effectiveType,
                downlink: navigator.connection.downlink,
                rtt: navigator.connection.rtt
            } : null
        };
    }
    
    // Public methods
    getMetrics() {
        this.calculateCurrentMetrics();
        return this.metrics;
    }
    
    getPerformanceScore() {
        let score = 100;
        
        // Deduct points for poor performance
        if (this.metrics.navigation.loadTime > 3000) score -= 20;
        if (this.metrics.resources.slowRequests > 5) score -= 15;
        if (this.metrics.pwa.cacheHitRate < 50) score -= 10;
        if (this.metrics.system.memoryUsage > 0.8) score -= 15;
        if (this.metrics.system.storageUsage > 0.9) score -= 10;
        if (this.metrics.user.errors > 0) score -= 20;
        
        return Math.max(0, score);
    }
    
    generatePerformanceReport() {
        const score = this.getPerformanceScore();
        const grade = score >= 90 ? 'A' : score >= 80 ? 'B' : score >= 70 ? 'C' : score >= 60 ? 'D' : 'F';
        
        return {
            score: score,
            grade: grade,
            metrics: this.metrics,
            recommendations: this.generateRecommendations(score),
            timestamp: Date.now()
        };
    }
    
    generateRecommendations(score) {
        const recommendations = [];
        
        if (this.metrics.navigation.loadTime > 3000) {
            recommendations.push({
                type: 'performance',
                priority: 'high',
                message: 'Page load time is slow. Consider optimizing images and scripts.',
                impact: 'user_experience'
            });
        }
        
        if (this.metrics.pwa.cacheHitRate < 50) {
            recommendations.push({
                type: 'caching',
                priority: 'medium',
                message: 'Cache hit rate is low. Review caching strategy.',
                impact: 'bandwidth'
            });
        }
        
        if (this.metrics.system.memoryUsage > 0.8) {
            recommendations.push({
                type: 'memory',
                priority: 'high',
                message: 'High memory usage detected. Consider memory optimization.',
                impact: 'stability'
            });
        }
        
        if (this.metrics.resources.failedRequests > 3) {
            recommendations.push({
                type: 'reliability',
                priority: 'high',
                message: 'Multiple resource failures detected. Check network connectivity.',
                impact: 'functionality'
            });
        }
        
        return recommendations;
    }
    
    cleanup() {
        // Disconnect all observers
        this.observers.forEach(observer => {
            observer.disconnect();
        });
        
        // Clear reporting interval
        if (this.reportInterval) {
            clearInterval(this.reportInterval);
        }
        
        // Send final metrics
        this.sendPeriodicReport();
        
        console.log('Performance Monitor: Cleaned up');
    }
}

// Initialize performance monitor
window.performanceMonitor = null;

document.addEventListener('DOMContentLoaded', () => {
    window.performanceMonitor = new PerformanceMonitor();
    
    // Expose global functions
    window.getPerformanceMetrics = () => window.performanceMonitor.getMetrics();
    window.getPerformanceScore = () => window.performanceMonitor.getPerformanceScore();
    window.generatePerformanceReport = () => window.performanceMonitor.generatePerformanceReport();
});

// Send queued metrics when coming online
window.addEventListener('online', () => {
    if (window.performanceMonitor) {
        window.performanceMonitor.sendQueuedMetrics();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.performanceMonitor) {
        window.performanceMonitor.cleanup();
    }
});