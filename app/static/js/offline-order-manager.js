class OfflineOrderManager {
    constructor() {
        this.offlineManager = null;
        this.currentOrder = null;
        this.orderHistory = [];
        this.isOfflineMode = false;
        
        // Order configuration
        this.orderConfig = {
            taxRate: 0.08, // 8% tax
            currencySymbol: '$',
            receiptTemplate: 'default'
        };
        
        // Initialize when DOM is ready
        this.init();
    }
    
    async init() {
        try {
            // Wait for offline manager to be available
            if (window.offlineManager) {
                this.offlineManager = window.offlineManager;
            } else {
                // Wait for offline manager to initialize
                window.addEventListener('offline-manager-ready', () => {
                    this.offlineManager = window.offlineManager;
                    this.setupEventListeners();
                });
            }
            
            // Load order configuration
            await this.loadOrderConfig();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Check network status
            this.updateNetworkStatus();
            
            // Load any pending orders
            await this.loadPendingOrders();
            
            console.log('Offline Order Manager: Initialized');
        } catch (error) {
            console.error('Offline Order Manager: Initialization failed', error);
        }
    }
    
    setupEventListeners() {
        // Network status listeners
        window.addEventListener('online', () => {
            this.updateNetworkStatus();
            this.syncPendingOrders();
        });
        
        window.addEventListener('offline', () => {
            this.updateNetworkStatus();
        });
        
        // Form submission listeners
        document.addEventListener('submit', (event) => {
            if (event.target.matches('#order-form')) {
                event.preventDefault();
                this.handleOrderSubmit(event.target);
            }
        });
        
        // Item selection listeners
        document.addEventListener('click', (event) => {
            if (event.target.matches('.menu-item-btn')) {
                this.addMenuItem(event.target.dataset);
            }
            
            if (event.target.matches('.cart-item-remove')) {
                this.removeFromCart(event.target.dataset.itemId);
            }
            
            if (event.target.matches('.cart-item-quantity')) {
                this.updateQuantity(event.target.dataset.itemId, event.target.value);
            }
        });
        
        // Order action listeners
        document.addEventListener('click', (event) => {
            if (event.target.matches('#new-order-btn')) {
                this.startNewOrder();
            }
            
            if (event.target.matches('#save-order-btn')) {
                this.saveCurrentOrder();
            }
            
            if (event.target.matches('#complete-order-btn')) {
                this.completeOrder();
            }
            
            if (event.target.matches('#cancel-order-btn')) {
                this.cancelOrder();
            }
            
            if (event.target.matches('#print-receipt-btn')) {
                this.printReceipt();
            }
        });
    }
    
    updateNetworkStatus() {
        this.isOfflineMode = !navigator.onLine;
        
        // Update UI elements
        const statusIndicator = document.getElementById('network-status');
        if (statusIndicator) {
            statusIndicator.className = this.isOfflineMode 
                ? 'bg-red-500 text-white px-3 py-1 rounded-full text-sm'
                : 'bg-green-500 text-white px-3 py-1 rounded-full text-sm';
            statusIndicator.textContent = this.isOfflineMode ? 'Offline' : 'Online';
        }
        
        // Update order form
        const orderForm = document.getElementById('order-form');
        if (orderForm) {
            orderForm.classList.toggle('offline-mode', this.isOfflineMode);
        }
        
        // Show notification
        if (this.isOfflineMode) {
            this.showNotification('Working offline - orders will sync when connection is restored', 'warning');
        } else {
            this.showNotification('Connection restored - syncing pending orders', 'success');
        }
    }
    
    async loadOrderConfig() {
        try {
            if (this.offlineManager) {
                const taxRate = await this.offlineManager.getSetting('tax_rate', 0.08);
                const currencySymbol = await this.offlineManager.getSetting('currency_symbol', '$');
                
                this.orderConfig.taxRate = taxRate;
                this.orderConfig.currencySymbol = currencySymbol;
            }
        } catch (error) {
            console.error('Offline Order Manager: Failed to load order config', error);
        }
    }
    
    async loadPendingOrders() {
        try {
            if (this.offlineManager) {
                const orders = await this.offlineManager.getOrders();
                this.orderHistory = orders.filter(order => order.sync_status === 'pending');
                
                // Update UI with pending orders
                this.updatePendingOrdersUI();
                
                console.log(`Offline Order Manager: Loaded ${this.orderHistory.length} pending orders`);
            }
        } catch (error) {
            console.error('Offline Order Manager: Failed to load pending orders', error);
        }
    }
    
    startNewOrder() {
        this.currentOrder = {
            id: 'temp_' + Date.now(),
            table_id: null,
            items: [],
            subtotal: 0,
            tax_amount: 0,
            total: 0,
            status: 'new',
            created_at: Date.now(),
            offline_created: Date.now(),
            sync_status: 'pending'
        };
        
        this.updateOrderUI();
        this.showNotification('New order started', 'info');
    }
    
    async addMenuItem(itemData) {
        if (!this.currentOrder) {
            this.startNewOrder();
        }
        
        try {
            // Get menu item details
            let menuItem;
            if (this.offlineManager) {
                const menuItems = await this.offlineManager.getMenuItems();
                menuItem = menuItems.find(item => item.id == itemData.menuItemId);
            }
            
            if (!menuItem) {
                // Use provided data if menu item not found
                menuItem = {
                    id: itemData.menuItemId,
                    name: itemData.name || 'Unknown Item',
                    price: parseFloat(itemData.price) || 0
                };
            }
            
            // Check if item already in order
            const existingItem = this.currentOrder.items.find(item => item.menu_item_id === menuItem.id);
            
            if (existingItem) {
                existingItem.quantity += 1;
                existingItem.total_price = existingItem.quantity * menuItem.price;
            } else {
                this.currentOrder.items.push({
                    menu_item_id: menuItem.id,
                    name: menuItem.name,
                    price: menuItem.price,
                    quantity: 1,
                    total_price: menuItem.price,
                    special_instructions: ''
                });
            }
            
            // Recalculate totals
            this.calculateOrderTotals();
            
            // Update UI
            this.updateOrderUI();
            this.updateCartUI();
            
            this.showNotification(`${menuItem.name} added to order`, 'success');
        } catch (error) {
            console.error('Offline Order Manager: Failed to add menu item', error);
            this.showNotification('Failed to add item to order', 'error');
        }
    }
    
    removeFromCart(itemId) {
        if (!this.currentOrder) return;
        
        const itemIndex = this.currentOrder.items.findIndex(item => item.menu_item_id == itemId);
        if (itemIndex !== -1) {
            const itemName = this.currentOrder.items[itemIndex].name;
            this.currentOrder.items.splice(itemIndex, 1);
            
            this.calculateOrderTotals();
            this.updateOrderUI();
            this.updateCartUI();
            
            this.showNotification(`${itemName} removed from order`, 'info');
        }
    }
    
    updateQuantity(itemId, quantity) {
        if (!this.currentOrder) return;
        
        const item = this.currentOrder.items.find(item => item.menu_item_id == itemId);
        if (item) {
            item.quantity = parseInt(quantity) || 1;
            item.total_price = item.quantity * item.price;
            
            this.calculateOrderTotals();
            this.updateOrderUI();
            this.updateCartUI();
        }
    }
    
    calculateOrderTotals() {
        if (!this.currentOrder) return;
        
        // Calculate subtotal
        this.currentOrder.subtotal = this.currentOrder.items.reduce(
            (sum, item) => sum + item.total_price, 0
        );
        
        // Calculate tax
        this.currentOrder.tax_amount = this.currentOrder.subtotal * this.orderConfig.taxRate;
        
        // Calculate total
        this.currentOrder.total = this.currentOrder.subtotal + this.currentOrder.tax_amount;
    }
    
    async handleOrderSubmit(form) {
        if (!this.currentOrder) {
            this.showNotification('No order to save', 'error');
            return;
        }
        
        try {
            // Get form data
            const formData = new FormData(form);
            this.currentOrder.table_id = formData.get('table_id');
            this.currentOrder.customer_name = formData.get('customer_name');
            this.currentOrder.customer_phone = formData.get('customer_phone');
            this.currentOrder.notes = formData.get('notes');
            
            // Save order
            await this.saveCurrentOrder();
            
        } catch (error) {
            console.error('Offline Order Manager: Failed to handle order submit', error);
            this.showNotification('Failed to save order', 'error');
        }
    }
    
    async saveCurrentOrder() {
        if (!this.currentOrder) {
            this.showNotification('No order to save', 'error');
            return;
        }
        
        try {
            // Validate order
            if (this.currentOrder.items.length === 0) {
                this.showNotification('Order must have at least one item', 'error');
                return;
            }
            
            // Set status
            this.currentOrder.status = 'saved';
            this.currentOrder.saved_at = Date.now();
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.saveOrder(this.currentOrder);
            }
            
            // Add to history
            this.orderHistory.push({...this.currentOrder});
            
            // Update UI
            this.updatePendingOrdersUI();
            this.showNotification('Order saved successfully', 'success');
            
            // Start new order
            this.startNewOrder();
            
        } catch (error) {
            console.error('Offline Order Manager: Failed to save order', error);
            this.showNotification('Failed to save order', 'error');
        }
    }
    
    async completeOrder() {
        if (!this.currentOrder) {
            this.showNotification('No order to complete', 'error');
            return;
        }
        
        try {
            // Validate order
            if (this.currentOrder.items.length === 0) {
                this.showNotification('Order must have at least one item', 'error');
                return;
            }
            
            // Set status
            this.currentOrder.status = 'completed';
            this.currentOrder.completed_at = Date.now();
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.saveOrder(this.currentOrder);
            }
            
            // Add to history
            this.orderHistory.push({...this.currentOrder});
            
            // Update UI
            this.updatePendingOrdersUI();
            this.showNotification('Order completed successfully', 'success');
            
            // Print receipt if available
            if (window.printReceipt) {
                window.printReceipt(this.currentOrder);
            }
            
            // Start new order
            this.startNewOrder();
            
        } catch (error) {
            console.error('Offline Order Manager: Failed to complete order', error);
            this.showNotification('Failed to complete order', 'error');
        }
    }
    
    cancelOrder() {
        if (!this.currentOrder) {
            this.showNotification('No order to cancel', 'error');
            return;
        }
        
        if (confirm('Are you sure you want to cancel this order?')) {
            this.currentOrder = null;
            this.updateOrderUI();
            this.updateCartUI();
            this.showNotification('Order cancelled', 'info');
        }
    }
    
    async syncPendingOrders() {
        if (!this.offlineManager || this.isOfflineMode) {
            return;
        }
        
        try {
            // Trigger sync through offline manager
            await this.offlineManager.syncPendingOperations();
            
            // Update pending orders after sync
            await this.loadPendingOrders();
            
        } catch (error) {
            console.error('Offline Order Manager: Failed to sync pending orders', error);
        }
    }
    
    updateOrderUI() {
        // Update order summary
        const orderSummary = document.getElementById('order-summary');
        if (orderSummary && this.currentOrder) {
            orderSummary.innerHTML = `
                <div class="bg-white rounded-lg shadow p-6">
                    <h3 class="text-lg font-semibold mb-4">Order Summary</h3>
                    <div class="space-y-2">
                        <div class="flex justify-between">
                            <span>Subtotal:</span>
                            <span>${this.orderConfig.currencySymbol}${this.currentOrder.subtotal.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between">
                            <span>Tax (${(this.orderConfig.taxRate * 100).toFixed(0)}%):</span>
                            <span>${this.orderConfig.currencySymbol}${this.currentOrder.tax_amount.toFixed(2)}</span>
                        </div>
                        <div class="flex justify-between font-bold text-lg border-t pt-2">
                            <span>Total:</span>
                            <span>${this.orderConfig.currencySymbol}${this.currentOrder.total.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Update action buttons
        const actionButtons = document.getElementById('order-actions');
        if (actionButtons) {
            const hasItems = this.currentOrder && this.currentOrder.items.length > 0;
            actionButtons.innerHTML = `
                <button id="save-order-btn" class="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md mr-2 ${!hasItems ? 'opacity-50 cursor-not-allowed' : ''}" ${!hasItems ? 'disabled' : ''}>
                    Save Order
                </button>
                <button id="complete-order-btn" class="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-md mr-2 ${!hasItems ? 'opacity-50 cursor-not-allowed' : ''}" ${!hasItems ? 'disabled' : ''}>
                    Complete Order
                </button>
                <button id="cancel-order-btn" class="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-md">
                    Cancel Order
                </button>
            `;
        }
    }
    
    updateCartUI() {
        const cartContainer = document.getElementById('cart-container');
        if (cartContainer && this.currentOrder) {
            if (this.currentOrder.items.length === 0) {
                cartContainer.innerHTML = '<p class="text-gray-500 text-center py-4">No items in cart</p>';
            } else {
                cartContainer.innerHTML = `
                    <div class="bg-white rounded-lg shadow">
                        <div class="p-4 border-b">
                            <h3 class="font-semibold">Current Order</h3>
                        </div>
                        <div class="divide-y">
                            ${this.currentOrder.items.map(item => `
                                <div class="p-4 flex justify-between items-center">
                                    <div>
                                        <h4 class="font-medium">${item.name}</h4>
                                        <p class="text-gray-600">${this.orderConfig.currencySymbol}${item.price.toFixed(2)} x ${item.quantity}</p>
                                    </div>
                                    <div class="flex items-center space-x-2">
                                        <input type="number" class="cart-item-quantity w-16 px-2 py-1 border rounded" 
                                               data-item-id="${item.menu_item_id}" value="${item.quantity}" min="1">
                                        <span class="font-medium">${this.orderConfig.currencySymbol}${item.total_price.toFixed(2)}</span>
                                        <button class="cart-item-remove text-red-600 hover:text-red-800" data-item-id="${item.menu_item_id}">
                                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
        }
    }
    
    updatePendingOrdersUI() {
        const pendingOrdersContainer = document.getElementById('pending-orders');
        if (pendingOrdersContainer) {
            if (this.orderHistory.length === 0) {
                pendingOrdersContainer.innerHTML = '<p class="text-gray-500 text-center py-4">No pending orders</p>';
            } else {
                pendingOrdersContainer.innerHTML = `
                    <div class="bg-white rounded-lg shadow">
                        <div class="p-4 border-b">
                            <h3 class="font-semibold">Pending Orders (${this.orderHistory.length})</h3>
                        </div>
                        <div class="divide-y max-h-96 overflow-y-auto">
                            ${this.orderHistory.map(order => `
                                <div class="p-4 hover:bg-gray-50">
                                    <div class="flex justify-between items-start">
                                        <div>
                                            <h4 class="font-medium">Order #${order.id}</h4>
                                            <p class="text-sm text-gray-600">
                                                ${new Date(order.created_at).toLocaleString()}
                                            </p>
                                            <p class="text-sm">
                                                ${order.items.length} items • ${this.orderConfig.currencySymbol}${order.total.toFixed(2)}
                                            </p>
                                        </div>
                                        <div class="flex items-center space-x-1">
                                            ${order.sync_status === 'pending' ? `
                                                <span class="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">Pending Sync</span>
                                            ` : ''}
                                            ${order.status === 'completed' ? `
                                                <span class="bg-green-100 text-green-800 text-xs px-2 py-1 rounded">Completed</span>
                                            ` : ''}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }
        }
    }
    
    showNotification(message, type = 'info') {
        // Use global notification system if available
        if (window.RestaurantPOS && window.RestaurantPOS.showNotification) {
            window.RestaurantPOS.showNotification(message, type);
        } else {
            // Fallback to console and basic notification
            console.log(`Order Manager [${type}]: ${message}`);
            
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
}

// Initialize offline order manager
window.OfflineOrderManager = OfflineOrderManager;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.offlineOrderManager = new OfflineOrderManager();
    });
} else {
    window.offlineOrderManager = new OfflineOrderManager();
}