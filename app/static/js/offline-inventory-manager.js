class OfflineInventoryManager {
    constructor() {
        this.offlineManager = null;
        this.inventoryItems = [];
        this.isOfflineMode = false;
        
        // Inventory configuration
        this.inventoryConfig = {
            lowStockThreshold: 10,
            defaultUnit: 'pcs',
            categories: ['Produce', 'Dairy', 'Meat', 'Grains', 'Beverages', 'Other']
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
            
            // Load inventory configuration
            await this.loadInventoryConfig();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Check network status
            this.updateNetworkStatus();
            
            // Load inventory items
            await this.loadInventoryItems();
            
            console.log('Offline Inventory Manager: Initialized');
        } catch (error) {
            console.error('Offline Inventory Manager: Initialization failed', error);
        }
    }
    
    setupEventListeners() {
        // Network status listeners
        window.addEventListener('online', () => {
            this.updateNetworkStatus();
            this.syncPendingInventoryChanges();
        });
        
        window.addEventListener('offline', () => {
            this.updateNetworkStatus();
        });
        
        // Form submission listeners
        document.addEventListener('submit', (event) => {
            if (event.target.matches('#inventory-form')) {
                event.preventDefault();
                this.handleInventorySubmit(event.target);
            }
            
            if (event.target.matches('#stock-adjustment-form')) {
                event.preventDefault();
                this.handleStockAdjustment(event.target);
            }
        });
        
        // Inventory action listeners
        document.addEventListener('click', (event) => {
            if (event.target.matches('.inventory-item-edit')) {
                this.editInventoryItem(event.target.dataset.itemId);
            }
            
            if (event.target.matches('.inventory-item-delete')) {
                this.deleteInventoryItem(event.target.dataset.itemId);
            }
            
            if (event.target.matches('.stock-adjust-btn')) {
                this.showStockAdjustment(event.target.dataset.itemId);
            }
            
            if (event.target.matches('.add-inventory-btn')) {
                this.showAddInventoryForm();
            }
        });
        
        // Search and filter listeners
        document.addEventListener('input', (event) => {
            if (event.target.matches('#inventory-search')) {
                this.filterInventory(event.target.value);
            }
        });
        
        document.addEventListener('change', (event) => {
            if (event.target.matches('#inventory-category-filter')) {
                this.filterInventoryByCategory(event.target.value);
            }
        });
    }
    
    updateNetworkStatus() {
        this.isOfflineMode = !navigator.onLine;
        
        // Update UI elements
        const statusIndicator = document.getElementById('inventory-network-status');
        if (statusIndicator) {
            statusIndicator.className = this.isOfflineMode 
                ? 'bg-red-500 text-white px-3 py-1 rounded-full text-sm'
                : 'bg-green-500 text-white px-3 py-1 rounded-full text-sm';
            statusIndicator.textContent = this.isOfflineMode ? 'Offline' : 'Online';
        }
        
        // Update inventory form
        const inventoryForm = document.getElementById('inventory-form');
        if (inventoryForm) {
            inventoryForm.classList.toggle('offline-mode', this.isOfflineMode);
        }
        
        // Show notification
        if (this.isOfflineMode) {
            this.showNotification('Working offline - inventory changes will sync when connection is restored', 'warning');
        } else {
            this.showNotification('Connection restored - syncing pending inventory changes', 'success');
        }
    }
    
    async loadInventoryConfig() {
        try {
            if (this.offlineManager) {
                const lowStockThreshold = await this.offlineManager.getSetting('low_stock_threshold', 10);
                const defaultUnit = await this.offlineManager.getSetting('default_unit', 'pcs');
                
                this.inventoryConfig.lowStockThreshold = lowStockThreshold;
                this.inventoryConfig.defaultUnit = defaultUnit;
            }
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to load inventory config', error);
        }
    }
    
    async loadInventoryItems() {
        try {
            if (this.offlineManager) {
                // Try to get from offline storage first
                const inventoryItems = await this.offlineManager.getInventoryItems();
                this.inventoryItems = inventoryItems;
                
                // Update UI
                this.updateInventoryUI();
                
                console.log(`Offline Inventory Manager: Loaded ${this.inventoryItems.length} inventory items`);
            }
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to load inventory items', error);
        }
    }
    
    async saveInventoryItem(itemData) {
        try {
            // Create inventory item with offline metadata
            const inventoryItem = {
                ...itemData,
                id: itemData.id || 'temp_' + Date.now(),
                current_stock: parseFloat(itemData.current_stock) || 0,
                unit_cost: parseFloat(itemData.unit_cost) || 0,
                minimum_stock: parseFloat(itemData.minimum_stock) || this.inventoryConfig.lowStockThreshold,
                unit: itemData.unit || this.inventoryConfig.defaultUnit,
                category: itemData.category || 'Other',
                created_at: Date.now(),
                updated_at: Date.now(),
                offline_created: Date.now(),
                sync_status: 'pending'
            };
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'inventory',
                    action: 'create',
                    data: inventoryItem,
                    priority: 'normal'
                });
                
                // Add to local inventory
                this.inventoryItems.push(inventoryItem);
                this.updateInventoryUI();
            }
            
            this.showNotification('Inventory item saved successfully', 'success');
            return inventoryItem;
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to save inventory item', error);
            this.showNotification('Failed to save inventory item', 'error');
            throw error;
        }
    }
    
    async updateInventoryItem(itemId, itemData) {
        try {
            // Find existing item
            const itemIndex = this.inventoryItems.findIndex(item => item.id == itemId);
            if (itemIndex === -1) {
                throw new Error('Inventory item not found');
            }
            
            // Update item data
            const updatedItem = {
                ...this.inventoryItems[itemIndex],
                ...itemData,
                updated_at: Date.now(),
                sync_status: 'pending'
            };
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'inventory',
                    action: 'update',
                    data: updatedItem,
                    priority: 'normal'
                });
                
                // Update local inventory
                this.inventoryItems[itemIndex] = updatedItem;
                this.updateInventoryUI();
            }
            
            this.showNotification('Inventory item updated successfully', 'success');
            return updatedItem;
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to update inventory item', error);
            this.showNotification('Failed to update inventory item', 'error');
            throw error;
        }
    }
    
    async deleteInventoryItem(itemId) {
        try {
            if (!confirm('Are you sure you want to delete this inventory item?')) {
                return;
            }
            
            // Find existing item
            const itemIndex = this.inventoryItems.findIndex(item => item.id == itemId);
            if (itemIndex === -1) {
                throw new Error('Inventory item not found');
            }
            
            const item = this.inventoryItems[itemIndex];
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'inventory',
                    action: 'delete',
                    data: { id: itemId },
                    priority: 'normal'
                });
                
                // Remove from local inventory
                this.inventoryItems.splice(itemIndex, 1);
                this.updateInventoryUI();
            }
            
            this.showNotification(`${item.name} deleted successfully`, 'success');
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to delete inventory item', error);
            this.showNotification('Failed to delete inventory item', 'error');
        }
    }
    
    async adjustStock(itemId, adjustment, reason = '') {
        try {
            // Find existing item
            const itemIndex = this.inventoryItems.findIndex(item => item.id == itemId);
            if (itemIndex === -1) {
                throw new Error('Inventory item not found');
            }
            
            const item = this.inventoryItems[itemIndex];
            const adjustmentAmount = parseFloat(adjustment) || 0;
            const newStock = item.current_stock + adjustmentAmount;
            
            if (newStock < 0) {
                throw new Error('Stock cannot be negative');
            }
            
            // Create adjustment record
            const adjustmentRecord = {
                ingredient_id: itemId,
                adjustment: adjustmentAmount,
                previous_stock: item.current_stock,
                new_stock: newStock,
                reason: reason,
                created_at: Date.now(),
                sync_status: 'pending'
            };
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'inventory',
                    action: 'adjust',
                    data: adjustmentRecord,
                    priority: 'high'
                });
                
                // Update local inventory
                this.inventoryItems[itemIndex].current_stock = newStock;
                this.inventoryItems[itemIndex].updated_at = Date.now();
                this.inventoryItems[itemIndex].sync_status = 'pending';
                this.updateInventoryUI();
            }
            
            this.showNotification(`Stock adjusted for ${item.name}: ${adjustmentAmount > 0 ? '+' : ''}${adjustmentAmount}`, 'success');
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to adjust stock', error);
            this.showNotification('Failed to adjust stock', 'error');
        }
    }
    
    handleInventorySubmit(form) {
        try {
            const formData = new FormData(form);
            const itemData = {
                name: formData.get('name'),
                description: formData.get('description'),
                unit: formData.get('unit'),
                current_stock: formData.get('current_stock'),
                unit_cost: formData.get('unit_cost'),
                minimum_stock: formData.get('minimum_stock'),
                category: formData.get('category')
            };
            
            // Check if editing or creating
            const itemId = form.dataset.itemId;
            if (itemId) {
                this.updateInventoryItem(itemId, itemData);
            } else {
                this.saveInventoryItem(itemData);
            }
            
            // Reset form
            form.reset();
            delete form.dataset.itemId;
            
            // Hide form
            this.hideInventoryForm();
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to handle inventory submit', error);
        }
    }
    
    handleStockAdjustment(form) {
        try {
            const formData = new FormData(form);
            const itemId = formData.get('item_id');
            const adjustment = formData.get('adjustment');
            const reason = formData.get('reason');
            
            this.adjustStock(itemId, adjustment, reason);
            
            // Reset form
            form.reset();
            
            // Hide form
            this.hideStockAdjustmentForm();
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to handle stock adjustment', error);
        }
    }
    
    editInventoryItem(itemId) {
        const item = this.inventoryItems.find(item => item.id == itemId);
        if (!item) return;
        
        // Show form with item data
        this.showInventoryForm(item);
    }
    
    showAddInventoryForm() {
        this.showInventoryForm();
    }
    
    showInventoryForm(item = null) {
        const formContainer = document.getElementById('inventory-form-container');
        if (!formContainer) return;
        
        const isEditing = !!item;
        
        formContainer.innerHTML = `
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                    <div class="p-6">
                        <h3 class="text-lg font-semibold mb-4">
                            ${isEditing ? 'Edit Inventory Item' : 'Add Inventory Item'}
                        </h3>
                        <form id="inventory-form" class="space-y-4" ${isEditing ? `data-item-id="${item.id}"` : ''}>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Name</label>
                                <input type="text" name="name" required
                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                       value="${item ? item.name : ''}">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                <textarea name="description" rows="3"
                                          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">${item ? item.description : ''}</textarea>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Category</label>
                                <select name="category"
                                        class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                    ${this.inventoryConfig.categories.map(cat => `
                                        <option value="${cat}" ${item && item.category === cat ? 'selected' : ''}>${cat}</option>
                                    `).join('')}
                                </select>
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Current Stock</label>
                                    <input type="number" name="current_stock" required step="0.01" min="0"
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                           value="${item ? item.current_stock : ''}">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Unit</label>
                                    <input type="text" name="unit" required
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                           value="${item ? item.unit : this.inventoryConfig.defaultUnit}">
                                </div>
                            </div>
                            <div class="grid grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Unit Cost</label>
                                    <input type="number" name="unit_cost" required step="0.01" min="0"
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                           value="${item ? item.unit_cost : ''}">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Minimum Stock</label>
                                    <input type="number" name="minimum_stock" required step="0.01" min="0"
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                           value="${item ? item.minimum_stock : this.inventoryConfig.lowStockThreshold}">
                                </div>
                            </div>
                            <div class="flex justify-end space-x-3 pt-4">
                                <button type="button" onclick="window.offlineInventoryManager.hideInventoryForm()"
                                        class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
                                    Cancel
                                </button>
                                <button type="submit"
                                        class="px-4 py-2 bg-blue-600 border border-transparent rounded-md text-white hover:bg-blue-700">
                                    ${isEditing ? 'Update' : 'Save'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }
    
    hideInventoryForm() {
        const formContainer = document.getElementById('inventory-form-container');
        if (formContainer) {
            formContainer.innerHTML = '';
        }
    }
    
    showStockAdjustment(itemId) {
        const item = this.inventoryItems.find(item => item.id == itemId);
        if (!item) return;
        
        const formContainer = document.getElementById('stock-adjustment-form-container');
        if (!formContainer) return;
        
        formContainer.innerHTML = `
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                    <div class="p-6">
                        <h3 class="text-lg font-semibold mb-4">Adjust Stock - ${item.name}</h3>
                        <form id="stock-adjustment-form" class="space-y-4">
                            <input type="hidden" name="item_id" value="${itemId}">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Current Stock</label>
                                <div class="px-3 py-2 bg-gray-100 border border-gray-300 rounded-md">
                                    ${item.current_stock} ${item.unit}
                                </div>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Adjustment</label>
                                <input type="number" name="adjustment" required step="0.01"
                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                       placeholder="Use positive for addition, negative for removal">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Reason</label>
                                <textarea name="reason" rows="3"
                                          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                          placeholder="Reason for adjustment (e.g., waste, delivery, correction)"></textarea>
                            </div>
                            <div class="flex justify-end space-x-3 pt-4">
                                <button type="button" onclick="window.offlineInventoryManager.hideStockAdjustmentForm()"
                                        class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">
                                    Cancel
                                </button>
                                <button type="submit"
                                        class="px-4 py-2 bg-blue-600 border border-transparent rounded-md text-white hover:bg-blue-700">
                                    Adjust Stock
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;
    }
    
    hideStockAdjustmentForm() {
        const formContainer = document.getElementById('stock-adjustment-form-container');
        if (formContainer) {
            formContainer.innerHTML = '';
        }
    }
    
    filterInventory(searchTerm) {
        const filteredItems = this.inventoryItems.filter(item => {
            const searchLower = searchTerm.toLowerCase();
            return item.name.toLowerCase().includes(searchLower) ||
                   item.description.toLowerCase().includes(searchLower) ||
                   item.category.toLowerCase().includes(searchLower);
        });
        
        this.updateInventoryUI(filteredItems);
    }
    
    filterInventoryByCategory(category) {
        const filteredItems = category 
            ? this.inventoryItems.filter(item => item.category === category)
            : this.inventoryItems;
        
        this.updateInventoryUI(filteredItems);
    }
    
    updateInventoryUI(items = this.inventoryItems) {
        const container = document.getElementById('inventory-list');
        if (!container) return;
        
        if (items.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8">No inventory items found</p>';
            return;
        }
        
        container.innerHTML = `
            <div class="bg-white shadow overflow-hidden rounded-md">
                <div class="divide-y divide-gray-200">
                    ${items.map(item => {
                        const isLowStock = item.current_stock <= item.minimum_stock;
                        const stockPercentage = (item.current_stock / item.minimum_stock) * 100;
                        
                        return `
                            <div class="p-4 hover:bg-gray-50">
                                <div class="flex items-center justify-between">
                                    <div class="flex-1">
                                        <div class="flex items-center">
                                            <h3 class="text-lg font-medium text-gray-900">${item.name}</h3>
                                            ${item.sync_status === 'pending' ? `
                                                <span class="ml-2 bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">Pending Sync</span>
                                            ` : ''}
                                        </div>
                                        <p class="text-sm text-gray-500">${item.description}</p>
                                        <div class="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                                            <span>Category: ${item.category}</span>
                                            <span>Unit: ${item.unit}</span>
                                            <span>Cost: $${item.unit_cost.toFixed(2)}</span>
                                        </div>
                                    </div>
                                    <div class="flex items-center space-x-2">
                                        <div class="text-right">
                                            <div class="text-lg font-medium ${isLowStock ? 'text-red-600' : 'text-gray-900'}">
                                                ${item.current_stock} ${item.unit}
                                            </div>
                                            <div class="text-sm text-gray-500">
                                                Min: ${item.minimum_stock} ${item.unit}
                                            </div>
                                        </div>
                                        <div class="flex space-x-1">
                                            <button class="stock-adjust-btn p-1 text-blue-600 hover:text-blue-800" 
                                                    data-item-id="${item.id}" title="Adjust Stock">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path>
                                                </svg>
                                            </button>
                                            <button class="inventory-item-edit p-1 text-green-600 hover:text-green-800" 
                                                    data-item-id="${item.id}" title="Edit">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                                </svg>
                                            </button>
                                            <button class="inventory-item-delete p-1 text-red-600 hover:text-red-800" 
                                                    data-item-id="${item.id}" title="Delete">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                ${isLowStock ? `
                                    <div class="mt-2 bg-red-50 border border-red-200 rounded-md p-2">
                                        <p class="text-sm text-red-800">
                                            ⚠️ Low stock alert: Current stock is at or below minimum level
                                        </p>
                                    </div>
                                ` : ''}
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }
    
    async syncPendingInventoryChanges() {
        if (!this.offlineManager || this.isOfflineMode) {
            return;
        }
        
        try {
            // Trigger sync through offline manager
            await this.offlineManager.syncPendingOperations();
            
            // Update inventory after sync
            await this.loadInventoryItems();
            
        } catch (error) {
            console.error('Offline Inventory Manager: Failed to sync pending changes', error);
        }
    }
    
    showNotification(message, type = 'info') {
        // Use global notification system if available
        if (window.RestaurantPOS && window.RestaurantPOS.showNotification) {
            window.RestaurantPOS.showNotification(message, type);
        } else {
            // Fallback to console and basic notification
            console.log(`Inventory Manager [${type}]: ${message}`);
            
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

// Initialize offline inventory manager
window.OfflineInventoryManager = OfflineInventoryManager;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.offlineInventoryManager = new OfflineInventoryManager();
    });
} else {
    window.offlineInventoryManager = new OfflineInventoryManager();
}