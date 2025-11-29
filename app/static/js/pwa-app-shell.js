/**
 * PWA App Shell Architecture
 * Provides a native app-like experience with offline capabilities
 */
class PWAAppShell {
    constructor() {
        this.shellContainer = null;
        this.contentContainer = null;
        this.navigationContainer = null;
        this.currentRoute = null;
        this.isOnline = navigator.onLine;
        this.installPrompt = null;
        this.deferredPrompt = null;
        
        // App shell configuration
        this.config = {
            routes: {
                '/': 'dashboard',
                '/orders': 'orders',
                '/orders/new': 'new-order',
                '/menu': 'menu',
                '/kitchen': 'kitchen',
                '/inventory': 'inventory',
                '/reports': 'reports',
                '/settings': 'settings'
            },
            navigationItems: [
                { path: '/', icon: 'dashboard', label: 'Dashboard', badge: null },
                { path: '/orders/new', icon: 'add-shopping-cart', label: 'New Order', badge: null },
                { path: '/orders', icon: 'receipt', label: 'Orders', badge: 'pending' },
                { path: '/menu', icon: 'restaurant-menu', label: 'Menu', badge: null },
                { path: '/kitchen', icon: 'kitchen', label: 'Kitchen', badge: 'active' },
                { path: '/inventory', icon: 'inventory', label: 'Inventory', badge: 'low-stock' },
                { path: '/reports', icon: 'assessment', label: 'Reports', badge: null },
                { path: '/settings', icon: 'settings', label: 'Settings', badge: null }
            ],
            offlinePages: [
                '/offline.html',
                '/orders/new',
                '/menu',
                '/inventory'
            ]
        };
        
        // Performance monitoring
        this.performanceMetrics = {
            navigationStart: 0,
            contentLoadTime: 0,
            renderTime: 0,
            cacheHitRate: 0,
            totalRequests: 0,
            cachedRequests: 0
        };
        
        // Initialize the app shell
        this.init();
    }
    
    async init() {
        try {
            console.log('PWA App Shell: Initializing...');
            
            // Start performance monitoring
            this.startPerformanceMonitoring();
            
            // Create app shell structure
            await this.createAppShell();
            
            // Setup navigation
            this.setupNavigation();
            
            // Setup service worker communication
            this.setupServiceWorkerCommunication();
            
            // Setup online/offline detection
            this.setupConnectivityDetection();
            
            // Setup install prompt
            this.setupInstallPrompt();
            
            // Setup touch gestures for mobile
            this.setupTouchGestures();
            
            // Load initial route
            await this.loadRoute(window.location.pathname);
            
            // Setup periodic updates
            this.setupPeriodicUpdates();
            
            console.log('PWA App Shell: Initialization complete');
        } catch (error) {
            console.error('PWA App Shell: Initialization failed', error);
            this.showError('Failed to initialize app. Please refresh the page.');
        }
    }
    
    async createAppShell() {
        // Create shell container if it doesn't exist
        if (!document.getElementById('app-shell')) {
            const shellHTML = this.generateShellHTML();
            document.body.insertAdjacentHTML('afterbegin', shellHTML);
        }
        
        this.shellContainer = document.getElementById('app-shell');
        this.contentContainer = document.getElementById('app-content');
        this.navigationContainer = document.getElementById('app-navigation');
        
        // Add loading states
        this.setupLoadingStates();
        
        // Setup status indicators
        this.setupStatusIndicators();
    }
    
    generateShellHTML() {
        return `
            <div id="app-shell" class="h-screen flex flex-col bg-gray-50">
                <!-- App Header -->
                <header id="app-header" class="bg-blue-600 text-white shadow-lg z-50">
                    <div class="flex items-center justify-between px-4 py-3">
                        <div class="flex items-center space-x-3">
                            <button id="menu-toggle" class="p-2 rounded-md hover:bg-blue-700 transition-colors">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
                                </svg>
                            </button>
                            <h1 class="text-xl font-bold">Restaurant POS</h1>
                        </div>
                        <div class="flex items-center space-x-3">
                            <!-- Connection Status -->
                            <div id="connection-status" class="flex items-center space-x-2">
                                <div id="status-indicator" class="w-2 h-2 rounded-full bg-green-400"></div>
                                <span id="status-text" class="text-sm">Online</span>
                            </div>
                            <!-- Sync Status -->
                            <div id="sync-status" class="hidden">
                                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            </div>
                            <!-- Notifications -->
                            <button id="notification-btn" class="p-2 rounded-md hover:bg-blue-700 transition-colors relative">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path>
                                </svg>
                                <span id="notification-badge" class="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center hidden">0</span>
                            </button>
                            <!-- User Menu -->
                            <button id="user-menu" class="p-2 rounded-md hover:bg-blue-700 transition-colors">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                                </svg>
                            </button>
                        </div>
                    </div>
                </header>
                
                <!-- Main Content Area -->
                <div class="flex flex-1 overflow-hidden">
                    <!-- Navigation Sidebar -->
                    <nav id="app-navigation" class="w-64 bg-white shadow-lg transform -translate-x-full transition-transform duration-300 ease-in-out fixed md:relative md:translate-x-0 z-40 h-full">
                        <div class="p-4">
                            <h2 class="text-lg font-semibold text-gray-800 mb-4">Navigation</h2>
                            <ul id="nav-list" class="space-y-2">
                                <!-- Navigation items will be generated by JavaScript -->
                            </ul>
                        </div>
                    </nav>
                    
                    <!-- Main Content -->
                    <main id="app-content" class="flex-1 overflow-y-auto">
                        <!-- Loading State -->
                        <div id="loading-overlay" class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
                            <div class="bg-white rounded-lg p-6 flex flex-col items-center space-y-4">
                                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                                <span class="text-gray-600">Loading...</span>
                            </div>
                        </div>
                        
                        <!-- Content will be loaded here -->
                        <div id="content-wrapper" class="hidden">
                            <!-- Dynamic content area -->
                        </div>
                    </main>
                </div>
                
                <!-- App Footer -->
                <footer id="app-footer" class="bg-gray-800 text-white p-4">
                    <div class="flex justify-between items-center">
                        <div class="text-sm">
                            © 2024 Restaurant POS. Version <span id="app-version">1.0.0</span>
                        </div>
                        <div class="flex items-center space-x-4 text-sm">
                            <button id="storage-info" class="hover:text-gray-300">Storage</button>
                            <button id="cache-info" class="hover:text-gray-300">Cache</button>
                            <button id="sync-now" class="hover:text-gray-300">Sync Now</button>
                        </div>
                    </div>
                </footer>
                
                <!-- Offline Overlay -->
                <div id="offline-overlay" class="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center hidden">
                    <div class="bg-white rounded-lg p-8 max-w-md mx-4">
                        <div class="text-center">
                            <svg class="w-16 h-16 mx-auto mb-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0"></path>
                            </svg>
                            <h3 class="text-xl font-semibold mb-2">You're offline</h3>
                            <p class="text-gray-600 mb-4">Some features may be limited until you reconnect.</p>
                            <button id="retry-connection" class="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors">
                                Retry Connection
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Install Prompt -->
                <div id="install-prompt" class="fixed bottom-4 right-4 bg-white rounded-lg shadow-xl p-4 max-w-sm hidden z-50">
                    <div class="flex items-center space-x-3">
                        <div class="flex-shrink-0">
                            <img src="/static/images/icon-192x192.png" alt="App Icon" class="w-12 h-12">
                        </div>
                        <div class="flex-1">
                            <h4 class="font-semibold">Install Restaurant POS</h4>
                            <p class="text-sm text-gray-600">Install our app for a better experience</p>
                        </div>
                        <button id="install-dismiss" class="text-gray-400 hover:text-gray-600">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                            </svg>
                        </button>
                        <button id="install-button" class="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors text-sm">
                            Install
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    setupNavigation() {
        const navList = document.getElementById('nav-list');
        
        // Generate navigation items
        this.config.navigationItems.forEach(item => {
            const li = document.createElement('li');
            li.className = 'nav-item';
            
            const a = document.createElement('a');
            a.href = item.path;
            a.className = 'flex items-center space-x-3 px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100 transition-colors nav-link';
            a.dataset.route = item.path;
            
            // Icon
            const icon = document.createElement('span');
            icon.className = 'material-icons';
            icon.textContent = this.getIconForNav(item.icon);
            
            // Label
            const label = document.createElement('span');
            label.textContent = item.label;
            
            // Badge (if applicable)
            if (item.badge) {
                const badge = document.createElement('span');
                badge.className = 'nav-badge bg-red-500 text-white text-xs rounded-full px-2 py-1 ml-auto';
                badge.textContent = '0';
                badge.dataset.badgeType = item.badge;
                a.appendChild(badge);
            }
            
            a.appendChild(icon);
            a.appendChild(label);
            li.appendChild(a);
            navList.appendChild(li);
            
            // Add click handler
            a.addEventListener('click', (e) => {
                e.preventDefault();
                this.navigateTo(item.path);
            });
        });
        
        // Setup menu toggle
        const menuToggle = document.getElementById('menu-toggle');
        const navigation = document.getElementById('app-navigation');
        
        menuToggle.addEventListener('click', () => {
            navigation.classList.toggle('-translate-x-full');
        });
        
        // Close navigation when clicking outside
        document.addEventListener('click', (e) => {
            if (!navigation.contains(e.target) && !menuToggle.contains(e.target)) {
                navigation.classList.add('-translate-x-full');
            }
        });
    }
    
    getIconForNav(iconName) {
        const icons = {
            'dashboard': '📊',
            'add-shopping-cart': '🛒',
            'receipt': '🧾',
            'restaurant-menu': '🍽',
            'kitchen': '👨‍🍳',
            'inventory': '📦',
            'assessment': '📈',
            'settings': '⚙️'
        };
        return icons[iconName] || '📱';
    }
    
    async navigateTo(path) {
        if (path === this.currentRoute) return;
        
        // Update URL
        history.pushState({}, '', path);
        
        // Load route
        await this.loadRoute(path);
        
        // Close mobile navigation
        const navigation = document.getElementById('app-navigation');
        navigation.classList.add('-translate-x-full');
    }
    
    async loadRoute(path) {
        this.currentRoute = path;
        this.showLoading();
        
        try {
            // Record navigation start time
            this.performanceMetrics.navigationStart = performance.now();
            
            // Hide loading overlay with a minimum delay for better UX
            setTimeout(() => {
                this.hideLoading();
            }, 300);
            
            // Update active navigation state
            this.updateActiveNavigation(path);
            
            // Load content based on route
            await this.loadContent(path);
            
            // Record performance metrics
            this.recordNavigationMetrics();
            
        } catch (error) {
            console.error('PWA App Shell: Failed to load route', path, error);
            this.hideLoading();
            this.showError(`Failed to load ${path}. Please try again.`);
        }
    }
    
    updateActiveNavigation(path) {
        // Remove active class from all nav links
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.remove('bg-blue-100', 'text-blue-600', 'font-medium');
            link.classList.add('text-gray-700');
        });
        
        // Add active class to current nav link
        const activeLink = document.querySelector(`[data-route="${path}"]`);
        if (activeLink) {
            activeLink.classList.remove('text-gray-700');
            activeLink.classList.add('bg-blue-100', 'text-blue-600', 'font-medium');
        }
    }
    
    async loadContent(path) {
        const contentWrapper = document.getElementById('content-wrapper');
        
        // Check if we have a cached version
        const cachedContent = this.getCachedContent(path);
        if (cachedContent) {
            contentWrapper.innerHTML = cachedContent;
            this.performanceMetrics.cachedRequests++;
            return;
        }
        
        // Load content from server or offline fallback
        try {
            const response = await fetch(path);
            if (response.ok) {
                const html = await response.text();
                contentWrapper.innerHTML = html;
                this.cacheContent(path, html);
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.warn('PWA App Shell: Network request failed, trying offline fallback', error);
            
            // Try offline fallback
            const offlineContent = this.getOfflineContent(path);
            if (offlineContent) {
                contentWrapper.innerHTML = offlineContent;
                this.showOfflineWarning();
            } else {
                throw new Error('No offline content available');
            }
        }
        
        this.performanceMetrics.totalRequests++;
    }
    
    getCachedContent(path) {
        return localStorage.getItem(`pwa-cache-${path}`);
    }
    
    cacheContent(path, content) {
        try {
            localStorage.setItem(`pwa-cache-${path}`, content);
        } catch (error) {
            console.warn('PWA App Shell: Failed to cache content', error);
        }
    }
    
    getOfflineContent(path) {
        // Provide basic offline content for critical pages
        const offlineContent = {
            '/orders/new': this.generateOfflineOrderForm(),
            '/menu': this.generateOfflineMenu(),
            '/inventory': this.generateOfflineInventory()
        };
        
        return offlineContent[path] || null;
    }
    
    generateOfflineOrderForm() {
        return `
            <div class="p-6">
                <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                    <h3 class="text-yellow-800 font-semibold mb-2">⚠️ Offline Mode</h3>
                    <p class="text-yellow-700">You're currently offline. Orders will be saved locally and synced when you reconnect.</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-2xl font-bold mb-6">New Order</h2>
                    <form id="offline-order-form" class="space-y-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Table Number</label>
                            <input type="number" name="table_id" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Items</label>
                            <div id="order-items" class="space-y-2">
                                <div class="flex space-x-2">
                                    <input type="text" placeholder="Item name" class="flex-1 px-3 py-2 border border-gray-300 rounded-md">
                                    <input type="number" placeholder="Quantity" class="w-24 px-3 py-2 border border-gray-300 rounded-md">
                                    <input type="number" placeholder="Price" class="w-24 px-3 py-2 border border-gray-300 rounded-md">
                                    <button type="button" onclick="removeOrderItem(this)" class="px-3 py-2 bg-red-500 text-white rounded-md hover:bg-red-600">Remove</button>
                                </div>
                            </div>
                            <button type="button" onclick="addOrderItem()" class="mt-2 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600">Add Item</button>
                        </div>
                        <div class="flex justify-end space-x-3">
                            <button type="button" onclick="clearOfflineOrder()" class="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50">Clear</button>
                            <button type="submit" class="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">Save Order</button>
                        </div>
                    </form>
                </div>
            </div>
        `;
    }
    
    generateOfflineMenu() {
        return `
            <div class="p-6">
                <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                    <h3 class="text-yellow-800 font-semibold mb-2">⚠️ Offline Mode</h3>
                    <p class="text-yellow-700">Showing cached menu data. Some items may not be current.</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-2xl font-bold mb-6">Menu</h2>
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        <div class="border rounded-lg p-4">
                            <h3 class="font-semibold mb-2">Sample Item 1</h3>
                            <p class="text-gray-600 mb-2">Description of item</p>
                            <p class="text-xl font-bold text-blue-600">$9.99</p>
                        </div>
                        <!-- More items would be loaded from cache -->
                    </div>
                </div>
            </div>
        `;
    }
    
    generateOfflineInventory() {
        return `
            <div class="p-6">
                <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                    <h3 class="text-yellow-800 font-semibold mb-2">⚠️ Offline Mode</h3>
                    <p class="text-yellow-700">Showing cached inventory data. Stock levels may not be current.</p>
                </div>
                <div class="bg-white rounded-lg shadow p-6">
                    <h2 class="text-2xl font-bold mb-6">Inventory</h2>
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Item</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stock</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                <tr>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Sample Item</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">50</td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">In Stock</span>
                                    </td>
                                </tr>
                                <!-- More items would be loaded from cache -->
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    setupLoadingStates() {
        // Custom loading states for different content types
        this.loadingStates = {
            default: '<div class="flex items-center justify-center py-12"><div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div></div>',
            orders: '<div class="text-center py-12"><div class="animate-pulse">Loading orders...</div></div>',
            menu: '<div class="text-center py-12"><div class="animate-pulse">Loading menu...</div></div>',
            inventory: '<div class="text-center py-12"><div class="animate-pulse">Loading inventory...</div></div>'
        };
    }
    
    showLoading(type = 'default') {
        const loadingOverlay = document.getElementById('loading-overlay');
        const contentWrapper = document.getElementById('content-wrapper');
        
        if (this.loadingStates[type]) {
            contentWrapper.innerHTML = this.loadingStates[type];
        }
        
        loadingOverlay.classList.remove('hidden');
    }
    
    hideLoading() {
        const loadingOverlay = document.getElementById('loading-overlay');
        const contentWrapper = document.getElementById('content-wrapper');
        
        loadingOverlay.classList.add('hidden');
        contentWrapper.classList.remove('hidden');
    }
    
    showOfflineWarning() {
        const warning = document.createElement('div');
        warning.className = 'fixed top-20 left-4 right-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4 z-40';
        warning.innerHTML = `
            <div class="flex items-center space-x-3">
                <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                </svg>
                <div>
                    <h4 class="font-semibold text-yellow-800">Offline Mode</h4>
                    <p class="text-yellow-700 text-sm">You're viewing cached content. Some features may be limited.</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="text-yellow-600 hover:text-yellow-800">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        document.body.appendChild(warning);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (warning.parentElement) {
                warning.remove();
            }
        }, 5000);
    }
    
    showError(message) {
        const error = document.createElement('div');
        error.className = 'fixed top-20 left-4 right-4 bg-red-50 border border-red-200 rounded-lg p-4 z-40';
        error.innerHTML = `
            <div class="flex items-center space-x-3">
                <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div>
                    <h4 class="font-semibold text-red-800">Error</h4>
                    <p class="text-red-700 text-sm">${message}</p>
                </div>
                <button onclick="this.parentElement.parentElement.remove()" class="text-red-600 hover:text-red-800">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        document.body.appendChild(error);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (error.parentElement) {
                error.remove();
            }
        }, 10000);
    }
    
    setupStatusIndicators() {
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        const syncStatus = document.getElementById('sync-status');
        
        this.updateConnectionStatus = (isOnline) => {
            if (isOnline) {
                statusIndicator.className = 'w-2 h-2 rounded-full bg-green-400';
                statusText.textContent = 'Online';
                syncStatus.classList.add('hidden');
            } else {
                statusIndicator.className = 'w-2 h-2 rounded-full bg-red-400';
                statusText.textContent = 'Offline';
                syncStatus.classList.remove('hidden');
            }
        };
        
        // Initialize status
        this.updateConnectionStatus(this.isOnline);
    }
    
    setupConnectivityDetection() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.updateConnectionStatus(true);
            this.hideOfflineOverlay();
            this.syncWhenOnline();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
            this.updateConnectionStatus(false);
            this.showOfflineOverlay();
        });
        
        // Check initial connection status
        if (!this.isOnline) {
            this.showOfflineOverlay();
        }
    }
    
    showOfflineOverlay() {
        const overlay = document.getElementById('offline-overlay');
        overlay.classList.remove('hidden');
    }
    
    hideOfflineOverlay() {
        const overlay = document.getElementById('offline-overlay');
        overlay.classList.add('hidden');
    }
    
    setupInstallPrompt() {
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            this.deferredPrompt = e;
            this.showInstallPrompt();
        });
        
        // Handle install button clicks
        const installButton = document.getElementById('install-button');
        const installDismiss = document.getElementById('install-dismiss');
        const installPrompt = document.getElementById('install-prompt');
        
        if (installButton) {
            installButton.addEventListener('click', async () => {
                if (this.deferredPrompt) {
                    this.deferredPrompt.prompt();
                    const { outcome } = await this.deferredPrompt.userChoice;
                    console.log(`PWA App Shell: Install prompt ${outcome}`);
                    this.deferredPrompt = null;
                    installPrompt.classList.add('hidden');
                }
            });
        }
        
        if (installDismiss) {
            installDismiss.addEventListener('click', () => {
                installPrompt.classList.add('hidden');
            });
        }
    }
    
    showInstallPrompt() {
        const installPrompt = document.getElementById('install-prompt');
        if (installPrompt) {
            installPrompt.classList.remove('hidden');
        }
    }
    
    setupServiceWorkerCommunication() {
        // Listen for messages from service worker
        navigator.serviceWorker.addEventListener('message', (event) => {
            const { type, data } = event.data;
            
            switch (type) {
                case 'STORAGE_UPDATE':
                    this.handleStorageUpdate(data);
                    break;
                case 'PERFORMANCE_REPORT':
                    this.handlePerformanceReport(data);
                    break;
                case 'SYNC_STATUS_UPDATE':
                    this.handleSyncStatusUpdate(data);
                    break;
                default:
                    console.log('PWA App Shell: Unknown message type', type, data);
            }
        });
    }
    
    handleStorageUpdate(data) {
        console.log('PWA App Shell: Storage update', data);
        // Update storage UI if visible
        const storageInfo = document.getElementById('storage-info');
        if (storageInfo) {
            storageInfo.textContent = `Storage: ${data.percentage.toFixed(1)}%`;
        }
    }
    
    handlePerformanceReport(data) {
        console.log('PWA App Shell: Performance report', data);
        // Could display performance metrics to user
    }
    
    handleSyncStatusUpdate(data) {
        console.log('PWA App Shell: Sync status update', data);
        // Update sync indicators
        this.updateSyncBadges(data);
    }
    
    updateSyncBadges(syncData) {
        // Update navigation badges with sync data
        document.querySelectorAll('.nav-badge').forEach(badge => {
            const badgeType = badge.dataset.badgeType;
            let count = 0;
            
            switch (badgeType) {
                case 'pending':
                    count = syncData.pendingOrders || 0;
                    break;
                case 'active':
                    count = syncData.activeOrders || 0;
                    break;
                case 'low-stock':
                    count = syncData.lowStockItems || 0;
                    break;
            }
            
            badge.textContent = count;
            badge.classList.toggle('hidden', count === 0);
        });
        
        // Update notification badge
        const notificationBadge = document.getElementById('notification-badge');
        if (notificationBadge && syncData.unreadNotifications) {
            notificationBadge.textContent = syncData.unreadNotifications;
            notificationBadge.classList.toggle('hidden', syncData.unreadNotifications === 0);
        }
    }
    
    setupTouchGestures() {
        let touchStartX = 0;
        let touchStartY = 0;
        
        document.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        });
        
        document.addEventListener('touchend', (e) => {
            const touchEndX = e.changedTouches[0].screenX;
            const touchEndY = e.changedTouches[0].screenY;
            
            const deltaX = touchEndX - touchStartX;
            const deltaY = touchEndY - touchStartY;
            
            // Handle swipe gestures
            if (Math.abs(deltaX) > Math.abs(deltaY)) {
                // Horizontal swipe
                if (deltaX > 50) {
                    // Swipe right - open navigation
                    this.openNavigation();
                } else if (deltaX < -50) {
                    // Swipe left - close navigation
                    this.closeNavigation();
                }
            }
        });
    }
    
    openNavigation() {
        const navigation = document.getElementById('app-navigation');
        navigation.classList.remove('-translate-x-full');
    }
    
    closeNavigation() {
        const navigation = document.getElementById('app-navigation');
        navigation.classList.add('-translate-x-full');
    }
    
    startPerformanceMonitoring() {
        // Monitor navigation performance
        window.addEventListener('load', () => {
            this.performanceMetrics.contentLoadTime = performance.now();
        });
        
        // Monitor cache performance
        if ('PerformanceObserver' in window) {
            const observer = new PerformanceObserver((list) => {
                list.getEntries().forEach((entry) => {
                    if (entry.transferSize > 0) {
                        this.performanceMetrics.totalRequests++;
                        if (entry.transferSize === 0) {
                            this.performanceMetrics.cachedRequests++;
                        }
                    }
                });
            });
            
            observer.observe({ entryTypes: ['resource'] });
        }
    }
    
    recordNavigationMetrics() {
        const navigationTime = performance.now() - this.performanceMetrics.navigationStart;
        this.performanceMetrics.renderTime = navigationTime;
        
        // Calculate cache hit rate
        if (this.performanceMetrics.totalRequests > 0) {
            this.performanceMetrics.cacheHitRate = 
                (this.performanceMetrics.cachedRequests / this.performanceMetrics.totalRequests) * 100;
        }
        
        console.log('PWA App Shell: Navigation metrics', {
            route: this.currentRoute,
            navigationTime,
            cacheHitRate: this.performanceMetrics.cacheHitRate
        });
    }
    
    setupPeriodicUpdates() {
        // Update badges every 30 seconds
        setInterval(() => {
            this.updateBadges();
        }, 30000);
        
        // Sync data every 5 minutes
        setInterval(() => {
            if (this.isOnline) {
                this.syncData();
            }
        }, 5 * 60 * 1000);
    }
    
    async updateBadges() {
        try {
            // Fetch latest counts from API
            const response = await fetch('/api/badges');
            if (response.ok) {
                const data = await response.json();
                this.updateSyncBadges(data);
            }
        } catch (error) {
            console.warn('PWA App Shell: Failed to update badges', error);
        }
    }
    
    async syncData() {
        try {
            // Show sync status
            const syncStatus = document.getElementById('sync-status');
            syncStatus.classList.remove('hidden');
            
            // Trigger service worker sync
            if ('serviceWorker' in navigator) {
                const registration = await navigator.serviceWorker.ready;
                await registration.sync.register('sync-all');
            }
            
            // Hide sync status after delay
            setTimeout(() => {
                syncStatus.classList.add('hidden');
            }, 3000);
        } catch (error) {
            console.error('PWA App Shell: Failed to sync data', error);
        }
    }
    
    syncWhenOnline() {
        if (this.isOnline) {
            this.syncData();
        }
    }
}

// Global functions for offline order form
window.addOrderItem = function() {
    const container = document.getElementById('order-items');
    const newItem = document.createElement('div');
    newItem.className = 'flex space-x-2';
    newItem.innerHTML = `
        <input type="text" placeholder="Item name" class="flex-1 px-3 py-2 border border-gray-300 rounded-md">
        <input type="number" placeholder="Quantity" class="w-24 px-3 py-2 border border-gray-300 rounded-md">
        <input type="number" placeholder="Price" class="w-24 px-3 py-2 border border-gray-300 rounded-md">
        <button type="button" onclick="removeOrderItem(this)" class="px-3 py-2 bg-red-500 text-white rounded-md hover:bg-red-600">Remove</button>
    `;
    container.appendChild(newItem);
};

window.removeOrderItem = function(button) {
    button.parentElement.remove();
};

window.clearOfflineOrder = function() {
    document.getElementById('offline-order-form').reset();
    const container = document.getElementById('order-items');
    container.innerHTML = `
        <div class="flex space-x-2">
            <input type="text" placeholder="Item name" class="flex-1 px-3 py-2 border border-gray-300 rounded-md">
            <input type="number" placeholder="Quantity" class="w-24 px-3 py-2 border border-gray-300 rounded-md">
            <input type="number" placeholder="Price" class="w-24 px-3 py-2 border border-gray-300 rounded-md">
            <button type="button" onclick="removeOrderItem(this)" class="px-3 py-2 bg-red-500 text-white rounded-md hover:bg-red-600">Remove</button>
        </div>
    `;
};

// Initialize app shell when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.pwaAppShell = new PWAAppShell();
});

// Handle browser back/forward buttons
window.addEventListener('popstate', () => {
    if (window.pwaAppShell) {
        window.pwaAppShell.loadRoute(window.location.pathname);
    }
});