document.addEventListener('alpine:init', () => {
    Alpine.data('layout', () => ({
        sidebarOpen: window.innerWidth >= 1024,
        notifications: [],
        cartCount: 0,
        isLoading: false,
        searchQuery: '',
        searchResults: [],
        
        init() {
            // Ensure notifications is initialized as array
            if (!Array.isArray(this.notifications)) {
                this.notifications = [];
            }
            
            // Initialize cart count from session
            this.updateCartCount();
            
            // Listen for cart updates
            this.$el.addEventListener('cartUpdated', () => {
                this.updateCartCount();
            });
            
            // Initialize HTMX event listeners
            this.initHtmxListeners();
            
            // Initialize real-time updates
            this.initRealTimeUpdates();

            // Listen for global notification events
            window.addEventListener('show-notification', (event) => {
                if (event.detail) {
                    this.addNotification(event.detail.message, event.detail.type);
                }
            });
            
            // Handle window resize for responsive sidebar
            window.addEventListener('resize', () => {
                this.handleResize();
            });
            
            // Initial resize check
            this.handleResize();
        },
        
        updateCartCount() {
            fetch('/api/cart/count', {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => {
                    // Check if response is actually JSON
                    const contentType = response.headers.get('content-type');
                    if (contentType && contentType.includes('application/json')) {
                        return response.json();
                    } else {
                        // If not JSON (likely HTML redirect to login), ignore or handle gracefully
                        return { count: 0 };
                    }
                })
                .then(data => {
                    this.cartCount = data.count || 0;
                })
                .catch(error => console.error('Error updating cart count:', error));
        },
        
        toggleSidebar() {
            this.sidebarOpen = !this.sidebarOpen;
        },
        
        handleResize() {
            if (window.innerWidth >= 1024) {
                this.sidebarOpen = true;
            } else {
                this.sidebarOpen = false;
            }
        },
        
        addNotification(message, type = 'info') {
            const id = Date.now();
            this.notifications.push({
                id: id,
                message: message,
                type: type,
                timestamp: new Date()
            });
            
            // Auto remove after 5 seconds
            setTimeout(() => {
                this.notifications = this.notifications.filter(n => n.id !== id);
            }, 5000);
        },
        
        initHtmxListeners() {
            // HTMX event listeners for better UX
            document.body.addEventListener('htmx:beforeRequest', (event) => {
                this.isLoading = true;
                // Only show loading notification for long requests to avoid flicker
                // this.addNotification('Loading...', 'info'); 
            });
            
            document.body.addEventListener('htmx:afterRequest', (event) => {
                this.isLoading = false;
            });
            
            document.body.addEventListener('htmx:responseError', (event) => {
                this.addNotification('Request failed', 'error');
                this.isLoading = false;
            });
            
            document.body.addEventListener('htmx:confirm', (event) => {
                if (!confirm('Are you sure you want to perform this action?')) {
                    event.preventDefault();
                }
            });
        },
        
        initRealTimeUpdates() {
            // Simulate real-time updates for orders, tables, etc.
            setInterval(() => {
                this.updateRealTimeData();
            }, 30000); // Update every 30 seconds
        },
        
        updateRealTimeData() {
            // Update cart count
            this.updateCartCount();
            
            // Update other real-time data based on current page
            if (window.location.pathname.includes('/kitchen')) {
                this.updateKitchenOrders();
            } else if (window.location.pathname.includes('/tables')) {
                this.updateTableStatus();
            }
        },
        
        updateKitchenOrders() {
            if (typeof htmx !== 'undefined') {
                const target = document.querySelector('#kitchen-orders');
                if (target) {
                    htmx.ajax('GET', '/api/kitchen/orders', {
                        target: '#kitchen-orders',
                        swap: 'innerHTML'
                    });
                }
            }
        },
        
        updateTableStatus() {
            if (typeof htmx !== 'undefined') {
                const target = document.querySelector('#tables-grid');
                if (target) {
                    htmx.ajax('GET', '/api/tables/status', {
                        target: '#tables-grid',
                        swap: 'innerHTML'
                    });
                }
            }
        },
        
        performSearch() {
            if (this.searchQuery.length < 2) {
                this.searchResults = [];
                return;
            }
            
            fetch(`/api/search?q=${encodeURIComponent(this.searchQuery)}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
                .then(response => response.json())
                .then(data => {
                    this.searchResults = data.results || [];
                })
                .catch(error => {
                    console.error('Search error:', error);
                    this.searchResults = [];
                });
        }
    }));
});
