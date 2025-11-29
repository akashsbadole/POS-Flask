/**
 * PWA Security Manager
 * Comprehensive security implementation for Progressive Web App
 * Includes CSP management, secure storage, authentication, and threat detection
 */
class PWASecurityManager {
    constructor() {
        this.config = {
            // Content Security Policy
            csp: {
                'default-src': ["'self'"],
                'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "https://www.gstatic.com", "https://apis.google.com"],
                'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
                'font-src': ["'self'", "https://fonts.gstatic.com"],
                'img-src': ["'self'", "data:", "https:", "blob:"],
                'media-src': ["'self'", "blob:"],
                'connect-src': ["'self'", "https://api.push.apple.com", "https://fcm.googleapis.com"],
                'object-src': ["'none'"],
                'base-uri': ["'self'"],
                'form-action': ["'self'"],
                'frame-ancestors': ["'none'"],
                'upgrade-insecure-requests': []
            },
            
            // Security headers
            headers: {
                'X-Content-Type-Options': 'nosniff',
                'X-Frame-Options': 'DENY',
                'X-XSS-Protection': '1; mode=block',
                'Referrer-Policy': 'strict-origin-when-cross-origin',
                'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
                'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
            },
            
            // Rate limiting
            rateLimiting: {
                enabled: true,
                maxRequests: 100,
                windowMs: 60000,
                skipSuccessfulRequests: false
            },
            
            // Token management
            tokens: {
                accessTokenExpiry: 3600000, // 1 hour
                refreshTokenExpiry: 86400000, // 24 hours
                rotationEnabled: true
            },
            
            // Encryption
            encryption: {
                algorithm: 'AES-GCM',
                keyLength: 256,
                ivLength: 12
            }
        };
        
        this.securityState = {
            isAuthenticated: false,
            userRole: null,
            permissions: [],
            sessionId: null,
            csrfToken: null,
            lastActivity: Date.now(),
            securityLevel: 'standard'
        };
        
        this.threatDetectors = new Map();
        this.securityEvents = [];
        this.encryptionKeys = new Map();
        
        this.init();
    }
    
    async init() {
        console.log('PWA Security Manager: Initializing...');
        
        // Initialize security features
        await this.initializeCSP();
        await this.initializeSecureStorage();
        await this.initializeThreatDetection();
        await this.initializeAuthentication();
        await this.initializeSessionManagement();
        
        // Setup security monitoring
        this.setupSecurityMonitoring();
        
        // Initialize encryption
        await this.initializeEncryption();
        
        console.log('PWA Security Manager: Initialized');
    }
    
    async initializeCSP() {
        // Apply Content Security Policy
        const cspMeta = document.createElement('meta');
        cspMeta.httpEquiv = 'Content-Security-Policy';
        
        const cspDirectives = Object.entries(this.config.csp)
            .map(([directive, sources]) => `${directive} ${sources.join(' ')}`)
            .join('; ');
        
        cspMeta.content = cspDirectives;
        document.head.appendChild(cspMeta);
        
        // Monitor CSP violations
        document.addEventListener('securitypolicyviolation', (event) => {
            this.handleCSPViolation(event);
        });
        
        console.log('CSP initialized:', cspDirectives);
    }
    
    async initializeSecureStorage() {
        // Create secure storage wrapper for localStorage
        this.secureStorage = {
            async setItem(key, value, encrypt = true) {
                const item = {
                    value: encrypt ? await window.pwaSecurity.encrypt(JSON.stringify(value)) : JSON.stringify(value),
                    timestamp: Date.now(),
                    encrypted: encrypt
                };
                
                try {
                    localStorage.setItem(`secure_${key}`, JSON.stringify(item));
                    return true;
                } catch (error) {
                    console.error('Secure storage error:', error);
                    return false;
                }
            },
            
            async getItem(key, decrypt = true) {
                try {
                    const item = JSON.parse(localStorage.getItem(`secure_${key}`));
                    if (!item) return null;
                    
                    const value = decrypt && item.encrypted ? 
                        await window.pwaSecurity.decrypt(item.value) : 
                        item.value;
                    
                    return JSON.parse(value);
                } catch (error) {
                    console.error('Secure storage retrieval error:', error);
                    return null;
                }
            },
            
            removeItem(key) {
                localStorage.removeItem(`secure_${key}`);
            },
            
            clear() {
                Object.keys(localStorage)
                    .filter(key => key.startsWith('secure_'))
                    .forEach(key => localStorage.removeItem(key));
            }
        };
        
        console.log('Secure storage initialized');
    }
    
    async initializeThreatDetection() {
        // Initialize threat detectors
        this.threatDetectors.set('xss', new XSSDetector());
        this.threatDetectors.set('injection', new InjectionDetector());
        this.threatDetectors.set('bruteForce', new BruteForceDetector());
        this.threatDetectors.set('suspiciousActivity', new SuspiciousActivityDetector());
        
        // Monitor DOM for XSS attempts
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.threatDetectors.get('xss').analyzeNode(node);
                        }
                    });
                }
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('Threat detection initialized');
    }
    
    async initializeAuthentication() {
        // Check for existing authentication
        const authData = await this.secureStorage.getItem('auth');
        
        if (authData && authData.accessToken) {
            try {
                // Validate token
                const isValid = await this.validateToken(authData.accessToken);
                
                if (isValid) {
                    this.securityState.isAuthenticated = true;
                    this.securityState.userRole = authData.userRole;
                    this.securityState.permissions = authData.permissions;
                    this.securityState.sessionId = authData.sessionId;
                    
                    // Setup token refresh
                    this.setupTokenRefresh(authData);
                } else {
                    // Clear invalid authentication
                    await this.secureStorage.removeItem('auth');
                }
            } catch (error) {
                console.error('Authentication validation error:', error);
                await this.secureStorage.removeItem('auth');
            }
        }
        
        console.log('Authentication initialized');
    }
    
    async initializeSessionManagement() {
        // Generate CSRF token if not exists
        if (!this.securityState.csrfToken) {
            this.securityState.csrfToken = this.generateCSRFToken();
        }
        
        // Setup activity monitoring
        this.setupActivityMonitoring();
        
        // Setup session timeout
        this.setupSessionTimeout();
        
        console.log('Session management initialized');
    }
    
    async initializeEncryption() {
        // Generate encryption key
        const key = await this.generateEncryptionKey();
        this.encryptionKeys.set('default', key);
        
        console.log('Encryption initialized');
    }
    
    setupSecurityMonitoring() {
        // Monitor network requests
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const request = args[0];
            const options = args[1] || {};
            
            // Add security headers
            options.headers = {
                ...options.headers,
                'X-CSRF-Token': this.securityState.csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            };
            
            // Rate limiting check
            if (this.config.rateLimiting.enabled) {
                const isAllowed = await this.checkRateLimit(request);
                if (!isAllowed) {
                    throw new Error('Rate limit exceeded');
                }
            }
            
            try {
                const response = await originalFetch(request, options);
                
                // Check for security headers in response
                this.validateSecurityHeaders(response);
                
                return response;
            } catch (error) {
                this.logSecurityEvent('network_error', { error: error.message, url: request.url });
                throw error;
            }
        };
        
        // Monitor console for security warnings
        const originalError = console.error;
        console.error = (...args) => {
            originalError.apply(console, args);
            
            // Check for security-related errors
            const message = args.join(' ');
            if (message.includes('CSP') || message.includes('security') || message.includes('XSS')) {
                this.logSecurityEvent('console_warning', { message });
            }
        };
    }
    
    setupActivityMonitoring() {
        const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
        
        const updateActivity = () => {
            this.securityState.lastActivity = Date.now();
        };
        
        events.forEach(event => {
            document.addEventListener(event, updateActivity, { passive: true });
        });
        
        // Check activity periodically
        setInterval(() => {
            const inactiveTime = Date.now() - this.securityState.lastActivity;
            const maxInactiveTime = 30 * 60 * 1000; // 30 minutes
            
            if (inactiveTime > maxInactiveTime) {
                this.handleSessionTimeout();
            }
        }, 60000); // Check every minute
    }
    
    setupSessionTimeout() {
        // Auto-refresh tokens before expiry
        setInterval(async () => {
            if (this.securityState.isAuthenticated) {
                const authData = await this.secureStorage.getItem('auth');
                if (authData && authData.expiresAt) {
                    const timeUntilExpiry = authData.expiresAt - Date.now();
                    
                    // Refresh if less than 5 minutes remaining
                    if (timeUntilExpiry < 5 * 60 * 1000) {
                        await this.refreshAuthToken();
                    }
                }
            }
        }, 60000); // Check every minute
    }
    
    async setupTokenRefresh(authData) {
        if (!this.config.tokens.rotationEnabled) return;
        
        const refreshInterval = authData.expiresAt - Date.now() - (5 * 60 * 1000); // 5 minutes before expiry
        
        if (refreshInterval > 0) {
            setTimeout(async () => {
                await this.refreshAuthToken();
            }, refreshInterval);
        }
    }
    
    async generateEncryptionKey() {
        const keyMaterial = await crypto.subtle.generateKey(
            {
                name: this.config.encryption.algorithm,
                length: this.config.encryption.keyLength
            },
            true,
            ['encrypt', 'decrypt']
        );
        
        return keyMaterial;
    }
    
    async encrypt(data) {
        try {
            const key = this.encryptionKeys.get('default');
            const encoder = new TextEncoder();
            const dataBuffer = encoder.encode(data);
            
            const iv = crypto.getRandomValues(new Uint8Array(this.config.encryption.ivLength));
            
            const encryptedData = await crypto.subtle.encrypt(
                {
                    name: this.config.encryption.algorithm,
                    iv: iv
                },
                key,
                dataBuffer
            );
            
            // Combine IV and encrypted data
            const combined = new Uint8Array(iv.length + encryptedData.byteLength);
            combined.set(iv);
            combined.set(new Uint8Array(encryptedData), iv.length);
            
            // Convert to base64 for storage
            return btoa(String.fromCharCode(...combined));
        } catch (error) {
            console.error('Encryption error:', error);
            throw error;
        }
    }
    
    async decrypt(encryptedData) {
        try {
            const key = this.encryptionKeys.get('default');
            
            // Convert from base64
            const combined = new Uint8Array(
                atob(encryptedData).split('').map(char => char.charCodeAt(0))
            );
            
            // Extract IV and encrypted data
            const iv = combined.slice(0, this.config.encryption.ivLength);
            const data = combined.slice(this.config.encryption.ivLength);
            
            const decryptedData = await crypto.subtle.decrypt(
                {
                    name: this.config.encryption.algorithm,
                    iv: iv
                },
                key,
                data
            );
            
            const decoder = new TextDecoder();
            return decoder.decode(decryptedData);
        } catch (error) {
            console.error('Decryption error:', error);
            throw error;
        }
    }
    
    generateCSRFToken() {
        const array = new Uint8Array(32);
        crypto.getRandomValues(array);
        return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
    }
    
    async validateToken(token) {
        try {
            // Decode JWT token
            const payload = JSON.parse(atob(token.split('.')[1]));
            
            // Check expiry
            if (payload.exp && payload.exp < Date.now() / 1000) {
                return false;
            }
            
            // Verify token structure
            if (!payload.iss || !payload.sub || !payload.aud) {
                return false;
            }
            
            return true;
        } catch (error) {
            console.error('Token validation error:', error);
            return false;
        }
    }
    
    async refreshAuthToken() {
        try {
            const authData = await this.secureStorage.getItem('auth');
            
            if (!authData || !authData.refreshToken) {
                throw new Error('No refresh token available');
            }
            
            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.securityState.csrfToken
                },
                body: JSON.stringify({
                    refreshToken: authData.refreshToken
                })
            });
            
            if (!response.ok) {
                throw new Error('Token refresh failed');
            }
            
            const newAuthData = await response.json();
            
            // Update stored auth data
            await this.secureStorage.setItem('auth', newAuthData);
            
            // Update security state
            this.securityState.isAuthenticated = true;
            this.securityState.userRole = newAuthData.userRole;
            this.securityState.permissions = newAuthData.permissions;
            
            // Setup next refresh
            this.setupTokenRefresh(newAuthData);
            
            console.log('Auth token refreshed successfully');
        } catch (error) {
            console.error('Token refresh error:', error);
            
            // Clear invalid authentication
            await this.secureStorage.removeItem('auth');
            this.securityState.isAuthenticated = false;
            
            // Redirect to login
            window.location.href = '/login';
        }
    }
    
    async checkRateLimit(request) {
        const key = `rate_limit_${request.url}`;
        const now = Date.now();
        const windowStart = now - this.config.rateLimiting.windowMs;
        
        const requests = await this.secureStorage.getItem(key) || [];
        
        // Filter out old requests
        const validRequests = requests.filter(timestamp => timestamp > windowStart);
        
        if (validRequests.length >= this.config.rateLimiting.maxRequests) {
            this.logSecurityEvent('rate_limit_exceeded', { url: request.url, count: validRequests.length });
            return false;
        }
        
        // Add current request
        validRequests.push(now);
        await this.secureStorage.setItem(key, validRequests, false);
        
        return true;
    }
    
    validateSecurityHeaders(response) {
        const requiredHeaders = this.config.headers;
        
        Object.entries(requiredHeaders).forEach(([header, expectedValue]) => {
            const actualValue = response.headers.get(header);
            
            if (!actualValue) {
                this.logSecurityEvent('missing_security_header', { header, expected: expectedValue });
            } else if (expectedValue && actualValue !== expectedValue) {
                this.logSecurityEvent('incorrect_security_header', { 
                    header, 
                    expected: expectedValue, 
                    actual: actualValue 
                });
            }
        });
    }
    
    handleCSPViolation(event) {
        this.logSecurityEvent('csp_violation', {
            violatedDirective: event.violatedDirective,
            blockedURI: event.blockedURI,
            sourceFile: event.sourceFile,
            lineNumber: event.lineNumber,
            columnNumber: event.columnNumber
        });
        
        // Determine severity based on violation type
        const severity = this.getViolationSeverity(event.violatedDirective);
        
        if (severity === 'high') {
            // Take immediate action for high-severity violations
            this.handleHighSeverityViolation(event);
        }
    }
    
    getViolationSeverity(directive) {
        const highSeverityDirectives = ['script-src', 'object-src', 'base-uri'];
        const mediumSeverityDirectives = ['connect-src', 'style-src', 'img-src'];
        
        if (highSeverityDirectives.includes(directive)) return 'high';
        if (mediumSeverityDirectives.includes(directive)) return 'medium';
        return 'low';
    }
    
    handleHighSeverityViolation(event) {
        // Log detailed information
        console.error('High-severity CSP violation detected:', event);
        
        // Potentially block the action or redirect
        if (event.violatedDirective === 'script-src') {
            // Remove the violating script
            if (event.sourceFile) {
                const scripts = document.querySelectorAll(`script[src="${event.sourceFile}"]`);
                scripts.forEach(script => script.remove());
            }
        }
        
        // Show security warning to user
        this.showSecurityWarning('A security violation was detected and blocked.');
    }
    
    handleSessionTimeout() {
        this.logSecurityEvent('session_timeout', {
            lastActivity: this.securityState.lastActivity,
            inactiveTime: Date.now() - this.securityState.lastActivity
        });
        
        // Clear authentication
        this.secureStorage.removeItem('auth');
        this.securityState.isAuthenticated = false;
        
        // Show timeout message
        this.showSessionTimeoutMessage();
    }
    
    showSecurityWarning(message) {
        // Create security warning modal
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl max-w-md mx-4 p-6">
                <div class="flex items-center mb-4">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                    <h3 class="ml-3 text-lg font-medium text-gray-900">Security Warning</h3>
                </div>
                <p class="text-gray-600 mb-4">${message}</p>
                <div class="flex justify-end">
                    <button onclick="this.closest('.fixed').remove()" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        I Understand
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    showSessionTimeoutMessage() {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl max-w-md mx-4 p-6">
                <div class="flex items-center mb-4">
                    <div class="flex-shrink-0">
                        <svg class="h-6 w-6 text-yellow-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <h3 class="ml-3 text-lg font-medium text-gray-900">Session Expired</h3>
                </div>
                <p class="text-gray-600 mb-4">Your session has expired due to inactivity. Please log in again.</p>
                <div class="flex justify-end">
                    <button onclick="window.location.href='/login'" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                        Log In Again
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    }
    
    logSecurityEvent(type, details) {
        const event = {
            type,
            details,
            timestamp: Date.now(),
            sessionId: this.securityState.sessionId,
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        this.securityEvents.push(event);
        
        // Keep only last 100 events
        if (this.securityEvents.length > 100) {
            this.securityEvents.shift();
        }
        
        // Send to server if authenticated
        if (this.securityState.isAuthenticated) {
            this.sendSecurityEventToServer(event);
        }
        
        console.warn('Security event:', event);
    }
    
    async sendSecurityEventToServer(event) {
        try {
            await fetch('/api/security/events', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.securityState.csrfToken
                },
                body: JSON.stringify(event)
            });
        } catch (error) {
            console.error('Failed to send security event to server:', error);
        }
    }
    
    // Public API methods
    async login(credentials) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.securityState.csrfToken
                },
                body: JSON.stringify(credentials)
            });
            
            if (!response.ok) {
                throw new Error('Login failed');
            }
            
            const authData = await response.json();
            
            // Store authentication data
            await this.secureStorage.setItem('auth', authData);
            
            // Update security state
            this.securityState.isAuthenticated = true;
            this.securityState.userRole = authData.userRole;
            this.securityState.permissions = authData.permissions;
            this.securityState.sessionId = authData.sessionId;
            
            // Setup token refresh
            this.setupTokenRefresh(authData);
            
            return authData;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }
    
    async logout() {
        try {
            // Call logout endpoint
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'X-CSRF-Token': this.securityState.csrfToken
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear local authentication
            await this.secureStorage.removeItem('auth');
            this.securityState.isAuthenticated = false;
            this.securityState.userRole = null;
            this.securityState.permissions = [];
            
            // Redirect to login
            window.location.href = '/login';
        }
    }
    
    hasPermission(permission) {
        return this.securityState.permissions.includes(permission);
    }
    
    hasRole(role) {
        return this.securityState.userRole === role;
    }
    
    getSecurityLevel() {
        return this.securityState.securityLevel;
    }
    
    setSecurityLevel(level) {
        const validLevels = ['low', 'standard', 'high'];
        if (validLevels.includes(level)) {
            this.securityState.securityLevel = level;
            
            // Adjust security settings based on level
            this.adjustSecurityForLevel(level);
        }
    }
    
    adjustSecurityForLevel(level) {
        switch (level) {
            case 'low':
                this.config.rateLimiting.enabled = false;
                this.config.tokens.rotationEnabled = false;
                break;
            case 'standard':
                this.config.rateLimiting.enabled = true;
                this.config.tokens.rotationEnabled = true;
                break;
            case 'high':
                this.config.rateLimiting.enabled = true;
                this.config.rateLimiting.maxRequests = 50;
                this.config.tokens.rotationEnabled = true;
                this.config.tokens.accessTokenExpiry = 1800000; // 30 minutes
                break;
        }
    }
}

// Threat Detector Classes
class XSSDetector {
    constructor() {
        this.dangerousPatterns = [
            /<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi,
            /javascript:/gi,
            /on\w+\s*=/gi,
            /<iframe\b[^>]*>/gi,
            /<object\b[^>]*>/gi,
            /<embed\b[^>]*>/gi
        ];
    }
    
    analyzeNode(node) {
        if (node.nodeType !== Node.ELEMENT_NODE) return;
        
        // Check attributes
        Array.from(node.attributes).forEach(attr => {
            this.checkValue(attr.value);
        });
        
        // Check text content
        if (node.textContent) {
            this.checkValue(node.textContent);
        }
    }
    
    checkValue(value) {
        this.dangerousPatterns.forEach(pattern => {
            if (pattern.test(value)) {
                window.pwaSecurity.logSecurityEvent('xss_attempt', {
                    value,
                    pattern: pattern.source
                });
            }
        });
    }
}

class InjectionDetector {
    constructor() {
        this.sqlPatterns = [
            new RegExp("('|(\\\')|(;)|(\\-\\-)|(\\s+(or|and)\\s+.*(=|like))", "gi"),
            new RegExp("(union\\s+select)", "gi"),
            new RegExp("(insert\\s+into)", "gi"),
            new RegExp("(delete\\s+from)", "gi"),
            new RegExp("(drop\\s+(table|database))", "gi")
        ];
    }
    
    analyzeInput(input) {
        this.sqlPatterns.forEach(pattern => {
            if (pattern.test(input)) {
                window.pwaSecurity.logSecurityEvent('sql_injection_attempt', {
                    input,
                    pattern: pattern.source
                });
            }
        });
    }
}

class BruteForceDetector {
    constructor() {
        this.attempts = new Map();
        this.maxAttempts = 5;
        this.lockoutDuration = 15 * 60 * 1000; // 15 minutes
    }
    
    recordAttempt(identifier) {
        const now = Date.now();
        const attempts = this.attempts.get(identifier) || [];
        
        // Filter out old attempts
        const validAttempts = attempts.filter(timestamp => 
            now - timestamp < this.lockoutDuration
        );
        
        validAttempts.push(now);
        this.attempts.set(identifier, validAttempts);
        
        if (validAttempts.length >= this.maxAttempts) {
            window.pwaSecurity.logSecurityEvent('brute_force_detected', {
                identifier,
                attempts: validAttempts.length
            });
            
            return true; // Lockout recommended
        }
        
        return false;
    }
}

class SuspiciousActivityDetector {
    constructor() {
        this.baselineMetrics = {
            requestsPerMinute: 10,
            uniqueEndpoints: 5,
            averageResponseTime: 500
        };
        
        this.currentMetrics = {
            requests: [],
            endpoints: new Set(),
            responseTimes: []
        };
    }
    
    recordRequest(url, responseTime) {
        const now = Date.now();
        
        this.currentMetrics.requests.push(now);
        this.currentMetrics.endpoints.add(url);
        this.currentMetrics.responseTimes.push(responseTime);
        
        // Keep only last minute of data
        const oneMinuteAgo = now - 60000;
        this.currentMetrics.requests = this.currentMetrics.requests.filter(
            timestamp => timestamp > oneMinuteAgo
        );
        
        // Check for suspicious activity
        this.analyzeActivity();
    }
    
    analyzeActivity() {
        const requestsPerMinute = this.currentMetrics.requests.length;
        const uniqueEndpoints = this.currentMetrics.endpoints.size;
        const avgResponseTime = this.currentMetrics.responseTimes.reduce((a, b) => a + b, 0) / 
                                this.currentMetrics.responseTimes.length;
        
        // Check for anomalies
        if (requestsPerMinute > this.baselineMetrics.requestsPerMinute * 3) {
            window.pwaSecurity.logSecurityEvent('high_request_rate', {
                current: requestsPerMinute,
                baseline: this.baselineMetrics.requestsPerMinute
            });
        }
        
        if (uniqueEndpoints > this.baselineMetrics.uniqueEndpoints * 2) {
            window.pwaSecurity.logSecurityEvent('unusual_endpoint_access', {
                current: uniqueEndpoints,
                baseline: this.baselineMetrics.uniqueEndpoints
            });
        }
    }
}

// Initialize security manager
window.pwaSecurity = null;

document.addEventListener('DOMContentLoaded', () => {
    window.pwaSecurity = new PWASecurityManager();
    
    // Expose global functions
    window.pwaLogin = (credentials) => window.pwaSecurity.login(credentials);
    window.pwaLogout = () => window.pwaSecurity.logout();
});