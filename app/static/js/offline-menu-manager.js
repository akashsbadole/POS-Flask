class OfflineMenuManager {
    constructor() {
        this.offlineManager = null;
        this.menuItems = [];
        this.categories = [];
        this.isOfflineMode = false;
        
        // Menu configuration
        this.menuConfig = {
            defaultCategory: 'Main Course',
            currencySymbol: '$',
            imageUploadEnabled: true,
            maxImageSize: 5 * 1024 * 1024 // 5MB
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
            
            // Load menu configuration
            await this.loadMenuConfig();
            
            // Setup event listeners
            this.setupEventListeners();
            
            // Check network status
            this.updateNetworkStatus();
            
            // Load menu items and categories
            await this.loadMenuData();
            
            console.log('Offline Menu Manager: Initialized');
        } catch (error) {
            console.error('Offline Menu Manager: Initialization failed', error);
        }
    }
    
    setupEventListeners() {
        // Network status listeners
        window.addEventListener('online', () => {
            this.updateNetworkStatus();
            this.syncPendingMenuChanges();
        });
        
        window.addEventListener('offline', () => {
            this.updateNetworkStatus();
        });
        
        // Form submission listeners
        document.addEventListener('submit', (event) => {
            if (event.target.matches('#menu-item-form')) {
                event.preventDefault();
                this.handleMenuItemSubmit(event.target);
            }
            
            if (event.target.matches('#category-form')) {
                event.preventDefault();
                this.handleCategorySubmit(event.target);
            }
        });
        
        // Menu action listeners
        document.addEventListener('click', (event) => {
            if (event.target.matches('.menu-item-edit')) {
                this.editMenuItem(event.target.dataset.itemId);
            }
            
            if (event.target.matches('.menu-item-delete')) {
                this.deleteMenuItem(event.target.dataset.itemId);
            }
            
            if (event.target.matches('.menu-item-toggle')) {
                this.toggleMenuItemAvailability(event.target.dataset.itemId);
            }
            
            if (event.target.matches('.add-menu-item-btn')) {
                this.showAddMenuItemForm();
            }
            
            if (event.target.matches('.add-category-btn')) {
                this.showAddCategoryForm();
            }
            
            if (event.target.matches('.category-edit')) {
                this.editCategory(event.target.dataset.categoryId);
            }
            
            if (event.target.matches('.category-delete')) {
                this.deleteCategory(event.target.dataset.categoryId);
            }
        });
        
        // Search and filter listeners
        document.addEventListener('input', (event) => {
            if (event.target.matches('#menu-search')) {
                this.filterMenuItems(event.target.value);
            }
        });
        
        document.addEventListener('change', (event) => {
            if (event.target.matches('#category-filter')) {
                this.filterMenuItemsByCategory(event.target.value);
            }
            
            if (event.target.matches('#availability-filter')) {
                this.filterMenuItemsByAvailability(event.target.value);
            }
        });
        
        // Image upload listener
        document.addEventListener('change', (event) => {
            if (event.target.matches('#menu-item-image')) {
                this.handleImageUpload(event.target.files[0]);
            }
        });
    }
    
    updateNetworkStatus() {
        this.isOfflineMode = !navigator.onLine;
        
        // Update UI elements
        const statusIndicator = document.getElementById('menu-network-status');
        if (statusIndicator) {
            statusIndicator.className = this.isOfflineMode 
                ? 'bg-red-500 text-white px-3 py-1 rounded-full text-sm'
                : 'bg-green-500 text-white px-3 py-1 rounded-full text-sm';
            statusIndicator.textContent = this.isOfflineMode ? 'Offline' : 'Online';
        }
        
        // Update menu forms
        const menuForms = document.querySelectorAll('#menu-item-form, #category-form');
        menuForms.forEach(form => {
            form.classList.toggle('offline-mode', this.isOfflineMode);
        });
        
        // Show notification
        if (this.isOfflineMode) {
            this.showNotification('Working offline - menu changes will sync when connection is restored', 'warning');
        } else {
            this.showNotification('Connection restored - syncing pending menu changes', 'success');
        }
    }
    
    async loadMenuConfig() {
        try {
            if (this.offlineManager) {
                const defaultCategory = await this.offlineManager.getSetting('default_category', 'Main Course');
                const currencySymbol = await this.offlineManager.getSetting('currency_symbol', '$');
                
                this.menuConfig.defaultCategory = defaultCategory;
                this.menuConfig.currencySymbol = currencySymbol;
            }
        } catch (error) {
            console.error('Offline Menu Manager: Failed to load menu config', error);
        }
    }
    
    async loadMenuData() {
        try {
            if (this.offlineManager) {
                // Try to get from offline storage first
                const menuItems = await this.offlineManager.getMenuItems();
                this.menuItems = menuItems;
                
                // Extract categories from menu items
                this.categories = [...new Set(menuItems.map(item => item.category).filter(Boolean))];
                
                // Update UI
                this.updateMenuUI();
                this.updateCategoriesUI();
                
                console.log(`Offline Menu Manager: Loaded ${this.menuItems.length} menu items and ${this.categories.length} categories`);
            }
        } catch (error) {
            console.error('Offline Menu Manager: Failed to load menu data', error);
        }
    }
    
    async saveMenuItem(itemData) {
        try {
            // Create menu item with offline metadata
            const menuItem = {
                ...itemData,
                id: itemData.id || 'temp_' + Date.now(),
                price: parseFloat(itemData.price) || 0,
                category: itemData.category || this.menuConfig.defaultCategory,
                is_available: itemData.is_available !== undefined ? itemData.is_available : true,
                preparation_time: parseInt(itemData.preparation_time) || 15,
                created_at: Date.now(),
                updated_at: Date.now(),
                offline_created: Date.now(),
                sync_status: 'pending'
            };
            
            // Handle image if provided
            if (itemData.imageData) {
                menuItem.image_data = itemData.imageData;
                menuItem.image_name = itemData.imageName;
            }
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'menu',
                    action: 'create',
                    data: menuItem,
                    priority: 'normal'
                });
                
                // Add to local menu
                this.menuItems.push(menuItem);
                
                // Update categories if new
                if (!this.categories.includes(menuItem.category)) {
                    this.categories.push(menuItem.category);
                    this.updateCategoriesUI();
                }
                
                this.updateMenuUI();
            }
            
            this.showNotification('Menu item saved successfully', 'success');
            return menuItem;
        } catch (error) {
            console.error('Offline Menu Manager: Failed to save menu item', error);
            this.showNotification('Failed to save menu item', 'error');
            throw error;
        }
    }
    
    async updateMenuItem(itemId, itemData) {
        try {
            // Find existing item
            const itemIndex = this.menuItems.findIndex(item => item.id == itemId);
            if (itemIndex === -1) {
                throw new Error('Menu item not found');
            }
            
            // Update item data
            const updatedItem = {
                ...this.menuItems[itemIndex],
                ...itemData,
                price: parseFloat(itemData.price) || this.menuItems[itemIndex].price,
                updated_at: Date.now(),
                sync_status: 'pending'
            };
            
            // Handle image if provided
            if (itemData.imageData) {
                updatedItem.image_data = itemData.imageData;
                updatedItem.image_name = itemData.imageName;
            }
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'menu',
                    action: 'update',
                    data: updatedItem,
                    priority: 'normal'
                });
                
                // Update local menu
                this.menuItems[itemIndex] = updatedItem;
                
                // Update categories if changed
                if (!this.categories.includes(updatedItem.category)) {
                    this.categories.push(updatedItem.category);
                    this.updateCategoriesUI();
                }
                
                this.updateMenuUI();
            }
            
            this.showNotification('Menu item updated successfully', 'success');
            return updatedItem;
        } catch (error) {
            console.error('Offline Menu Manager: Failed to update menu item', error);
            this.showNotification('Failed to update menu item', 'error');
            throw error;
        }
    }
    
    async deleteMenuItem(itemId) {
        try {
            if (!confirm('Are you sure you want to delete this menu item?')) {
                return;
            }
            
            // Find existing item
            const itemIndex = this.menuItems.findIndex(item => item.id == itemId);
            if (itemIndex === -1) {
                throw new Error('Menu item not found');
            }
            
            const item = this.menuItems[itemIndex];
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'menu',
                    action: 'delete',
                    data: { id: itemId },
                    priority: 'normal'
                });
                
                // Remove from local menu
                this.menuItems.splice(itemIndex, 1);
                this.updateMenuUI();
            }
            
            this.showNotification(`${item.name} deleted successfully`, 'success');
        } catch (error) {
            console.error('Offline Menu Manager: Failed to delete menu item', error);
            this.showNotification('Failed to delete menu item', 'error');
        }
    }
    
    async toggleMenuItemAvailability(itemId) {
        try {
            // Find existing item
            const itemIndex = this.menuItems.findIndex(item => item.id == itemId);
            if (itemIndex === -1) {
                throw new Error('Menu item not found');
            }
            
            const item = this.menuItems[itemIndex];
            const newAvailability = !item.is_available;
            
            // Update item
            const updatedItem = {
                ...item,
                is_available: newAvailability,
                updated_at: Date.now(),
                sync_status: 'pending'
            };
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'menu',
                    action: 'update',
                    data: updatedItem,
                    priority: 'high'
                });
                
                // Update local menu
                this.menuItems[itemIndex] = updatedItem;
                this.updateMenuUI();
            }
            
            this.showNotification(`${item.name} is now ${newAvailability ? 'available' : 'unavailable'}`, 'success');
        } catch (error) {
            console.error('Offline Menu Manager: Failed to toggle menu item availability', error);
            this.showNotification('Failed to update menu item availability', 'error');
        }
    }
    
    async saveCategory(categoryData) {
        try {
            // Create category with offline metadata
            const category = {
                ...categoryData,
                id: categoryData.id || 'temp_' + Date.now(),
                created_at: Date.now(),
                updated_at: Date.now(),
                offline_created: Date.now(),
                sync_status: 'pending'
            };
            
            // Save to offline storage
            if (this.offlineManager) {
                await this.offlineManager.addToSyncQueue({
                    type: 'category',
                    action: 'create',
                    data: category,
                    priority: 'normal'
                });
                
                // Add to local categories
                this.categories.push(category);
                this.updateCategoriesUI();
            }
            
            this.showNotification('Category saved successfully', 'success');
            return category;
        } catch (error) {
            console.error('Offline Menu Manager: Failed to save category', error);
            this.showNotification('Failed to save category', 'error');
            throw error;
        }
    }
    
    handleMenuItemSubmit(form) {
        try {
            const formData = new FormData(form);
            const itemData = {
                name: formData.get('name'),
                description: formData.get('description'),
                price: formData.get('price'),
                category: formData.get('category'),
                is_available: formData.get('is_available') === 'on',
                preparation_time: formData.get('preparation_time')
            };
            
            // Add image data if available
            const imageInput = document.getElementById('menu-item-image-preview');
            if (imageInput && imageInput.dataset.imageData) {
                itemData.imageData = imageInput.dataset.imageData;
                itemData.imageName = imageInput.dataset.imageName;
            }
            
            // Check if editing or creating
            const itemId = form.dataset.itemId;
            if (itemId) {
                this.updateMenuItem(itemId, itemData);
            } else {
                this.saveMenuItem(itemData);
            }
            
            // Reset form
            form.reset();
            delete form.dataset.itemId;
            
            // Clear image preview
            this.clearImagePreview();
            
            // Hide form
            this.hideMenuItemForm();
        } catch (error) {
            console.error('Offline Menu Manager: Failed to handle menu item submit', error);
        }
    }
    
    handleCategorySubmit(form) {
        try {
            const formData = new FormData(form);
            const categoryData = {
                name: formData.get('name'),
                description: formData.get('description')
            };
            
            this.saveCategory(categoryData);
            
            // Reset form
            form.reset();
            
            // Hide form
            this.hideCategoryForm();
        } catch (error) {
            console.error('Offline Menu Manager: Failed to handle category submit', error);
        }
    }
    
    handleImageUpload(file) {
        if (!file) return;
        
        // Check file size
        if (file.size > this.menuConfig.maxImageSize) {
            this.showNotification('Image file is too large (max 5MB)', 'error');
            return;
        }
        
        // Check file type
        if (!file.type.startsWith('image/')) {
            this.showNotification('Please select a valid image file', 'error');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = (event) => {
            const imageData = event.target.result;
            this.showImagePreview(imageData, file.name);
        };
        reader.readAsDataURL(file);
    }
    
    showImagePreview(imageData, imageName) {
        const previewContainer = document.getElementById('menu-item-image-preview');
        if (!previewContainer) return;
        
        previewContainer.innerHTML = `
            <div class="mt-2">
                <img src="${imageData}" alt="${imageName}" class="h-32 w-32 object-cover rounded-lg">
                <p class="text-sm text-gray-600 mt-1">${imageName}</p>
            </div>
        `;
        
        // Store image data for form submission
        previewContainer.dataset.imageData = imageData;
        previewContainer.dataset.imageName = imageName;
    }
    
    clearImagePreview() {
        const previewContainer = document.getElementById('menu-item-image-preview');
        if (previewContainer) {
            previewContainer.innerHTML = '';
            delete previewContainer.dataset.imageData;
            delete previewContainer.dataset.imageName;
        }
    }
    
    editMenuItem(itemId) {
        const item = this.menuItems.find(item => item.id == itemId);
        if (!item) return;
        
        // Show form with item data
        this.showMenuItemForm(item);
    }
    
    showAddMenuItemForm() {
        this.showMenuItemForm();
    }
    
    showMenuItemForm(item = null) {
        const formContainer = document.getElementById('menu-item-form-container');
        if (!formContainer) return;
        
        const isEditing = !!item;
        
        formContainer.innerHTML = `
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">
                    <div class="p-6">
                        <h3 class="text-lg font-semibold mb-4">
                            ${isEditing ? 'Edit Menu Item' : 'Add Menu Item'}
                        </h3>
                        <form id="menu-item-form" class="space-y-4" ${isEditing ? `data-item-id="${item.id}"` : ''}>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Name</label>
                                    <input type="text" name="name" required
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                           value="${item ? item.name : ''}">
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Price</label>
                                    <div class="relative">
                                        <span class="absolute left-3 top-2 text-gray-500">${this.menuConfig.currencySymbol}</span>
                                        <input type="number" name="price" required step="0.01" min="0"
                                               class="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                               value="${item ? item.price : ''}">
                                    </div>
                                </div>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                <textarea name="description" rows="3"
                                          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">${item ? item.description : ''}</textarea>
                            </div>
                            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Category</label>
                                    <select name="category"
                                            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                        <option value="">Select Category</option>
                                        ${this.categories.map(cat => `
                                            <option value="${cat}" ${item && item.category === cat ? 'selected' : ''}>${cat}</option>
                                        `).join('')}
                                        <option value="${this.menuConfig.defaultCategory}" ${!item || !this.categories.includes(item.category) ? 'selected' : ''}>${this.menuConfig.defaultCategory}</option>
                                    </select>
                                </div>
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1">Preparation Time (minutes)</label>
                                    <input type="number" name="preparation_time" required min="1"
                                           class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                           value="${item ? item.preparation_time : ''}">
                                </div>
                            </div>
                            <div class="flex items-center">
                                <input type="checkbox" name="is_available" id="is-available"
                                       class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                       ${item && item.is_available ? 'checked' : ''}>
                                <label for="is-available" class="ml-2 block text-sm text-gray-700">
                                    Available for ordering
                                </label>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Image</label>
                                <input type="file" id="menu-item-image" accept="image/*"
                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                <div id="menu-item-image-preview"></div>
                            </div>
                            <div class="flex justify-end space-x-3 pt-4">
                                <button type="button" onclick="window.offlineMenuManager.hideMenuItemForm()"
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
        
        // Show image preview if editing
        if (item && item.image_data) {
            this.showImagePreview(item.image_data, item.image_name || 'Current image');
        }
    }
    
    hideMenuItemForm() {
        const formContainer = document.getElementById('menu-item-form-container');
        if (formContainer) {
            formContainer.innerHTML = '';
        }
        this.clearImagePreview();
    }
    
    showAddCategoryForm() {
        this.showCategoryForm();
    }
    
    showCategoryForm(category = null) {
        const formContainer = document.getElementById('category-form-container');
        if (!formContainer) return;
        
        const isEditing = !!category;
        
        formContainer.innerHTML = `
            <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div class="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
                    <div class="p-6">
                        <h3 class="text-lg font-semibold mb-4">
                            ${isEditing ? 'Edit Category' : 'Add Category'}
                        </h3>
                        <form id="category-form" class="space-y-4" ${isEditing ? `data-category-id="${category.id}"` : ''}>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Name</label>
                                <input type="text" name="name" required
                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                                       value="${category ? category.name : ''}">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-1">Description</label>
                                <textarea name="description" rows="3"
                                          class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">${category ? category.description : ''}</textarea>
                            </div>
                            <div class="flex justify-end space-x-3 pt-4">
                                <button type="button" onclick="window.offlineMenuManager.hideCategoryForm()"
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
    
    hideCategoryForm() {
        const formContainer = document.getElementById('category-form-container');
        if (formContainer) {
            formContainer.innerHTML = '';
        }
    }
    
    filterMenuItems(searchTerm) {
        const filteredItems = this.menuItems.filter(item => {
            const searchLower = searchTerm.toLowerCase();
            return item.name.toLowerCase().includes(searchLower) ||
                   item.description.toLowerCase().includes(searchLower) ||
                   item.category.toLowerCase().includes(searchLower);
        });
        
        this.updateMenuUI(filteredItems);
    }
    
    filterMenuItemsByCategory(category) {
        const filteredItems = category 
            ? this.menuItems.filter(item => item.category === category)
            : this.menuItems;
        
        this.updateMenuUI(filteredItems);
    }
    
    filterMenuItemsByAvailability(availability) {
        const filteredItems = availability === 'available'
            ? this.menuItems.filter(item => item.is_available)
            : availability === 'unavailable'
            ? this.menuItems.filter(item => !item.is_available)
            : this.menuItems;
        
        this.updateMenuUI(filteredItems);
    }
    
    updateMenuUI(items = this.menuItems) {
        const container = document.getElementById('menu-items-list');
        if (!container) return;
        
        if (items.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8">No menu items found</p>';
            return;
        }
        
        // Group items by category
        const itemsByCategory = {};
        items.forEach(item => {
            if (!itemsByCategory[item.category]) {
                itemsByCategory[item.category] = [];
            }
            itemsByCategory[item.category].push(item);
        });
        
        container.innerHTML = `
            <div class="space-y-6">
                ${Object.entries(itemsByCategory).map(([category, categoryItems]) => `
                    <div class="bg-white shadow overflow-hidden rounded-md">
                        <div class="px-4 py-3 border-b border-gray-200 bg-gray-50">
                            <h3 class="text-lg font-medium text-gray-900">${category}</h3>
                            <p class="text-sm text-gray-500">${categoryItems.length} items</p>
                        </div>
                        <div class="divide-y divide-gray-200">
                            ${categoryItems.map(item => `
                                <div class="p-4 hover:bg-gray-50">
                                    <div class="flex items-center justify-between">
                                        <div class="flex-1">
                                            <div class="flex items-center">
                                                <h4 class="text-lg font-medium text-gray-900">${item.name}</h4>
                                                ${item.sync_status === 'pending' ? `
                                                    <span class="ml-2 bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded">Pending Sync</span>
                                                ` : ''}
                                                ${!item.is_available ? `
                                                    <span class="ml-2 bg-red-100 text-red-800 text-xs px-2 py-1 rounded">Unavailable</span>
                                                ` : ''}
                                            </div>
                                            <p class="text-sm text-gray-500 mt-1">${item.description}</p>
                                            <div class="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                                                <span>Prep time: ${item.preparation_time} min</span>
                                                <span>Price: ${this.menuConfig.currencySymbol}${item.price.toFixed(2)}</span>
                                            </div>
                                        </div>
                                        <div class="flex items-center space-x-2">
                                            ${item.image_data ? `
                                                <img src="${item.image_data}" alt="${item.name}" class="h-16 w-16 object-cover rounded">
                                            ` : ''}
                                            <div class="flex space-x-1">
                                                <button class="menu-item-toggle p-1 ${item.is_available ? 'text-green-600 hover:text-green-800' : 'text-red-600 hover:text-red-800'}" 
                                                        data-item-id="${item.id}" title="${item.is_available ? 'Make unavailable' : 'Make available'}">
                                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        ${item.is_available ? 
                                                            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 0018.364 5.636m-12.728 12.728L12 21m0-12l-6.364 6.364M12 3v6"></path>' :
                                                            '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 00-12.728 0M12 21v-6m0-6l6.364 6.364M12 3v6"></path>'
                                                        }
                                                    </svg>
                                                </button>
                                                <button class="menu-item-edit p-1 text-blue-600 hover:text-blue-800" 
                                                        data-item-id="${item.id}" title="Edit">
                                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828L8.586-8.586z"></path>
                                                    </svg>
                                                </button>
                                                <button class="menu-item-delete p-1 text-red-600 hover:text-red-800" 
                                                        data-item-id="${item.id}" title="Delete">
                                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                                    </svg>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    updateCategoriesUI() {
        const container = document.getElementById('categories-list');
        if (!container) return;
        
        if (this.categories.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-4">No categories found</p>';
            return;
        }
        
        container.innerHTML = `
            <div class="bg-white shadow overflow-hidden rounded-md">
                <div class="divide-y divide-gray-200">
                    ${this.categories.map(category => `
                        <div class="p-4 hover:bg-gray-50 flex items-center justify-between">
                            <div>
                                <h4 class="text-lg font-medium text-gray-900">${category}</h4>
                            </div>
                            <div class="flex space-x-1">
                                <button class="category-edit p-1 text-blue-600 hover:text-blue-800" 
                                        data-category-id="${category}" title="Edit">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828L8.586-8.586z"></path>
                                    </svg>
                                </button>
                                <button class="category-delete p-1 text-red-600 hover:text-red-800" 
                                        data-category-id="${category}" title="Delete">
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
    
    async syncPendingMenuChanges() {
        if (!this.offlineManager || this.isOfflineMode) {
            return;
        }
        
        try {
            // Trigger sync through offline manager
            await this.offlineManager.syncPendingOperations();
            
            // Update menu after sync
            await this.loadMenuData();
            
        } catch (error) {
            console.error('Offline Menu Manager: Failed to sync pending changes', error);
        }
    }
    
    showNotification(message, type = 'info') {
        // Use global notification system if available
        if (window.RestaurantPOS && window.RestaurantPOS.showNotification) {
            window.RestaurantPOS.showNotification(message, type);
        } else {
            // Fallback to console and basic notification
            console.log(`Menu Manager [${type}]: ${message}`);
            
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

// Initialize offline menu manager
window.OfflineMenuManager = OfflineMenuManager;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.offlineMenuManager = new OfflineMenuManager();
    });
} else {
    window.offlineMenuManager = new OfflineMenuManager();
}