/**
 * Authentication Manager for Restaurant POS
 * Handles login state persistence using localStorage and cookies
 */

class AuthManager {
    constructor() {
        this.storageKey = 'restaurant-pos-auth';
        this.userKey = 'restaurant-pos-user';
        this.sessionCheckInterval = null;
        this.init();
    }

    /**
     * Initialize the authentication manager
     */
    init() {
        console.log('Auth Manager initializing...');
        
        // Check authentication status on page load
        this.checkAuthStatus();
        
        // Setup periodic session validation
        this.setupSessionCheck();
        
        // Listen for authentication events
        this.setupEventListeners();
        
        console.log('Auth Manager initialized');
    }

    /**
     * Check current authentication status
     */
    async checkAuthStatus() {
        try {
            // Check if user is authenticated on server
            const response = await fetch('/auth/status');
            
            if (response.ok) {
                const data = await response.json();
                
                if (data.authenticated && data.user) {
                    // User is authenticated, update local storage
                    this.setAuthData(data.user, data.remember || false);
                    this.updateUI(data.user);
                } else {
                    // User is not authenticated, clear local data
                    this.clearAuthData();
                }
            } else {
                // Server error, assume not authenticated
                this.clearAuthData();
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
            // On network error, try to use cached data
            const cachedUser = this.getCachedUser();
            if (cachedUser) {
                this.updateUI(cachedUser);
            }
        }
    }

    /**
     * Setup periodic session validation
     */
    setupSessionCheck() {
        // Check session every 5 minutes
        this.sessionCheckInterval = setInterval(() => {
            this.checkAuthStatus();
        }, 5 * 60 * 1000);
    }

    /**
     * Setup event listeners for authentication events
     */
    setupEventListeners() {
        // Listen for successful login events
        window.addEventListener('login-success', (event) => {
            const { user, remember } = event.detail;
            this.setAuthData(user, remember);
            this.updateUI(user);
        });

        // Listen for logout events
        window.addEventListener('logout', () => {
            this.clearAuthData();
            this.updateUI(null);
        });

        // Listen for visibility change to check auth when tab becomes active
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                this.checkAuthStatus();
            }
        });
    }

    /**
     * Set authentication data in localStorage
     */
    setAuthData(user, remember = false) {
        const authData = {
            user: user,
            remember: remember,
            timestamp: Date.now()
        };

        if (remember) {
            // Store in localStorage for persistent sessions
            localStorage.setItem(this.storageKey, JSON.stringify(authData));
            localStorage.setItem(this.userKey, JSON.stringify(user));
        } else {
            // Store in sessionStorage for temporary sessions
            sessionStorage.setItem(this.storageKey, JSON.stringify(authData));
            sessionStorage.setItem(this.userKey, JSON.stringify(user));
        }
    }

    /**
     * Get cached user data
     */
    getCachedUser() {
        try {
            // Try localStorage first (persistent sessions)
            let userData = localStorage.getItem(this.userKey);
            if (!userData) {
                // Fall back to sessionStorage (temporary sessions)
                userData = sessionStorage.getItem(this.userKey);
            }
            
            return userData ? JSON.parse(userData) : null;
        } catch (error) {
            console.error('Error getting cached user:', error);
            return null;
        }
    }

    /**
     * Clear authentication data
     */
    clearAuthData() {
        localStorage.removeItem(this.storageKey);
        localStorage.removeItem(this.userKey);
        sessionStorage.removeItem(this.storageKey);
        sessionStorage.removeItem(this.userKey);
    }

    /**
     * Update UI based on authentication state
     */
    updateUI(user) {
        if (user) {
            // User is authenticated - use centralized manager with immediate update
            if (window.bodyClassManager) {
                window.bodyClassManager.addImmediateClass('user-authenticated');
                window.bodyClassManager.removeImmediateClass('user-not-authenticated');
            } else {
                // Fallback to direct manipulation - NO TRANSITIONS
                document.body.classList.add('user-authenticated');
                document.body.classList.remove('user-not-authenticated');
            }
            
            // Update user info in UI if elements exist
            const userNameElements = document.querySelectorAll('[data-user-name]');
            userNameElements.forEach(el => {
                el.textContent = user.name;
            });

            const userRoleElements = document.querySelectorAll('[data-user-role]');
            userRoleElements.forEach(el => {
                el.textContent = user.role;
            });

            // Dispatch event for other components
            window.dispatchEvent(new CustomEvent('user-authenticated', {
                detail: { user }
            }));
        } else {
            // User is not authenticated - use centralized manager with immediate update
            if (window.bodyClassManager) {
                window.bodyClassManager.addImmediateClass('user-not-authenticated');
                window.bodyClassManager.removeImmediateClass('user-authenticated');
            } else {
                // Fallback to direct manipulation - NO TRANSITIONS
                document.body.classList.add('user-not-authenticated');
                document.body.classList.remove('user-authenticated');
            }
            
            // Dispatch event for other components
            window.dispatchEvent(new CustomEvent('user-not-authenticated'));
        }
    }

    /**
     * Handle login form submission
     */
    async handleLogin(form, htmx = false) {
        try {
            const formData = new FormData(form);
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;

            // Show loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Logging in...';

            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const contentType = response.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                    // JSON response (API endpoint)
                    const data = await response.json();
                    
                    if (data.success) {
                        // Dispatch login success event
                        window.dispatchEvent(new CustomEvent('login-success', {
                            detail: {
                                user: data.user,
                                remember: formData.get('remember') === 'on'
                            }
                        }));
                        
                        // Redirect if needed
                        if (data.redirect) {
                            console.log('Redirecting to:', data.redirect);
                            window.location.href = data.redirect;
                        }
                    } else {
                        this.showLoginError(data.message || 'Login failed');
                    }
                } else {
                    // HTML response (HTMX or regular form)
                    if (htmx) {
                        // HTMX will handle the response
                        return;
                    } else {
                        // Regular form submission, check if redirected
                        const redirectUrl = response.url;
                        if (redirectUrl && redirectUrl !== form.action) {
                            window.location.href = redirectUrl;
                        }
                    }
                }
            } else {
                const errorData = await response.json().catch(() => ({}));
                this.showLoginError(errorData.message || 'Login failed');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showLoginError('Network error. Please try again.');
        } finally {
            // Restore button state
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    /**
     * Handle PIN login
     */
    async handlePinLogin(form, htmx = false) {
        try {
            const formData = new FormData(form);
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;

            // Show loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Authenticating...';

            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                const contentType = response.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                    const data = await response.json();
                    
                    if (data.success) {
                        window.dispatchEvent(new CustomEvent('login-success', {
                            detail: {
                                user: data.user,
                                remember: false // PIN login doesn't remember
                            }
                        }));
                        
                        if (data.redirect) {
                            window.location.href = data.redirect;
                        }
                    } else {
                        this.showPinError(data.message || 'Invalid PIN');
                    }
                } else {
                    if (htmx) {
                        return;
                    } else {
                        const redirectUrl = response.url;
                        if (redirectUrl && redirectUrl !== form.action) {
                            window.location.href = redirectUrl;
                        }
                    }
                }
            } else {
                const errorData = await response.json().catch(() => ({}));
                this.showPinError(errorData.message || 'Invalid PIN');
            }
        } catch (error) {
            console.error('PIN login error:', error);
            this.showPinError('Network error. Please try again.');
        } finally {
            const submitButton = form.querySelector('button[type="submit"]');
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        }
    }

    /**
     * Show login error message
     */
    showLoginError(message) {
        const errorContainer = document.querySelector('#login-form-container .error-message') ||
                             document.querySelector('#login-form-container [role="alert"]');
        
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                errorContainer.style.display = 'none';
            }, 5000);
        } else {
            // Fallback to app notification
            if (window.RestaurantPOS) {
                window.RestaurantPOS.showNotification(message, 'error');
            }
        }
    }

    /**
     * Show PIN error message
     */
    showPinError(message) {
        const errorContainer = document.querySelector('#pin-form-container .error-message') ||
                             document.querySelector('#pin-form-container [role="alert"]');
        
        if (errorContainer) {
            errorContainer.textContent = message;
            errorContainer.style.display = 'block';
            
            setTimeout(() => {
                errorContainer.style.display = 'none';
            }, 5000);
        } else {
            if (window.RestaurantPOS) {
                window.RestaurantPOS.showNotification(message, 'error');
            }
        }
    }

    /**
     * Handle logout
     */
    async handleLogout() {
        try {
            // Clear local auth data immediately
            this.clearAuthData();
            this.updateUI(null);
            
            // Make a simple GET request to logout endpoint
            const response = await fetch('/auth/logout', {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // Always redirect to login page regardless of response
            window.location.href = '/auth/login';
        } catch (error) {
            console.error('Logout error:', error);
            // Still redirect to login page even on error
            window.location.href = '/auth/login';
        }
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return this.getCachedUser() !== null;
    }

    /**
     * Get current user
     */
    getCurrentUser() {
        return this.getCachedUser();
    }

    /**
     * Cleanup resources
     */
    destroy() {
        if (this.sessionCheckInterval) {
            clearInterval(this.sessionCheckInterval);
        }
    }
}

// Initialize auth manager when DOM is ready
let authManager;

document.addEventListener('DOMContentLoaded', () => {
    authManager = new AuthManager();
    
    // Make auth manager available globally
    window.authManager = authManager;
    
    // Setup form handlers
    const loginForm = document.querySelector('#login-form-container form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            authManager.handleLogin(loginForm, true);
        });
    }
    
    const pinForm = document.querySelector('#pin-form-container form');
    if (pinForm) {
        pinForm.addEventListener('submit', (e) => {
            e.preventDefault();
            authManager.handlePinLogin(pinForm, true);
        });
    }
    
    // Setup logout handlers
    const logoutLinks = document.querySelectorAll('a[href*="logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            authManager.handleLogout();
        });
    });
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AuthManager;
}