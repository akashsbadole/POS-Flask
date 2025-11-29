/**
 * Reordering Utilities for Menu Management
 * Provides advanced reordering functionality with undo/redo, history tracking, and bulk operations
 */

class ReorderingUtils {
    constructor() {
        this.history = [];
        this.historyIndex = -1;
        this.maxHistorySize = 50;
        this.isReordering = false;
        this.lastSaveTime = null;
        this.autoSaveInterval = null;
        this.batchOperations = [];
        this.batchTimeout = null;
    }

    /**
     * Initialize reordering utilities
     */
    init() {
        this.setupEventListeners();
        this.startAutoSave();
        this.loadHistory();
    }

    /**
     * Setup event listeners for reordering operations
     */
    setupEventListeners() {
        // Listen for reorder events
        window.addEventListener('menu-reorder', this.handleReorderEvent.bind(this));
        window.addEventListener('category-reorder', this.handleCategoryReorderEvent.bind(this));
        
        // Listen for keyboard shortcuts
        document.addEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
        
        // Listen for page unload to save state
        window.addEventListener('beforeunload', this.saveState.bind(this));
    }

    /**
     * Handle menu item reorder events
     */
    handleReorderEvent(event) {
        const { element, oldIndex, newIndex, container } = event.detail;
        
        // Add to history
        this.addToHistory({
            type: 'menu-reorder',
            elementId: element.dataset.itemId,
            oldIndex,
            newIndex,
            categoryId: container.dataset.categoryId,
            timestamp: new Date()
        });
        
        // Update last save time
        this.updateLastSaveTime();
        
        // Show success notification
        this.showNotification('Item order updated', 'success');
    }

    /**
     * Handle category reorder events
     */
    handleCategoryReorderEvent(event) {
        const { element, oldIndex, newIndex } = event.detail;
        
        // Add to history
        this.addToHistory({
            type: 'category-reorder',
            elementId: element.dataset.categoryId,
            oldIndex,
            newIndex,
            timestamp: new Date()
        });
        
        // Update last save time
        this.updateLastSaveTime();
        
        // Show success notification
        this.showNotification('Category order updated', 'success');
    }

    /**
     * Add operation to history
     */
    addToHistory(operation) {
        // Remove any operations after current index
        this.history = this.history.slice(0, this.historyIndex + 1);
        
        // Add new operation
        this.history.push(operation);
        
        // Limit history size
        if (this.history.length > this.maxHistorySize) {
            this.history.shift();
        } else {
            this.historyIndex++;
        }
        
        this.saveHistory();
        this.updateUndoRedoState();
    }

    /**
     * Undo last operation
     */
    async undo() {
        if (this.historyIndex < 0) return;
        
        const operation = this.history[this.historyIndex];
        this.isReordering = true;
        
        try {
            if (operation.type === 'menu-reorder') {
                await this.undoMenuReorder(operation);
            } else if (operation.type === 'category-reorder') {
                await this.undoCategoryReorder(operation);
            }
            
            this.historyIndex--;
            this.updateUndoRedoState();
            this.showNotification('Undo successful', 'info');
        } catch (error) {
            console.error('Undo failed:', error);
            this.showNotification('Undo failed', 'error');
        } finally {
            this.isReordering = false;
        }
    }

    /**
     * Redo last undone operation
     */
    async redo() {
        if (this.historyIndex >= this.history.length - 1) return;
        
        this.historyIndex++;
        const operation = this.history[this.historyIndex];
        this.isReordering = true;
        
        try {
            if (operation.type === 'menu-reorder') {
                await this.redoMenuReorder(operation);
            } else if (operation.type === 'category-reorder') {
                await this.redoCategoryReorder(operation);
            }
            
            this.updateUndoRedoState();
            this.showNotification('Redo successful', 'info');
        } catch (error) {
            console.error('Redo failed:', error);
            this.showNotification('Redo failed', 'error');
        } finally {
            this.isReordering = false;
        }
    }

    /**
     * Undo menu reorder operation
     */
    async undoMenuReorder(operation) {
        const csrfToken = document.querySelector('[name=csrf_token]');
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }
        
        const response = await fetch('/api/menu/reorder-items', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken.value
            },
            body: JSON.stringify({
                items: [{
                    id: operation.elementId,
                    display_order: operation.oldIndex
                }],
                category_id: operation.categoryId
            })
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 302) {
                throw new Error('Authentication required. Please log in again.');
            }
            throw new Error(`Failed to undo menu reorder: ${response.status} ${response.statusText}`);
        }
        
        // Update UI
        this.updateMenuItemOrder(operation.elementId, operation.oldIndex);
    }

    /**
     * Redo menu reorder operation
     */
    async redoMenuReorder(operation) {
        const csrfToken = document.querySelector('[name=csrf_token]');
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }
        
        const response = await fetch('/api/menu/reorder-items', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken.value
            },
            body: JSON.stringify({
                items: [{
                    id: operation.elementId,
                    display_order: operation.newIndex
                }],
                category_id: operation.categoryId
            })
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 302) {
                throw new Error('Authentication required. Please log in again.');
            }
            throw new Error(`Failed to redo menu reorder: ${response.status} ${response.statusText}`);
        }
        
        // Update UI
        this.updateMenuItemOrder(operation.elementId, operation.newIndex);
    }

    /**
     * Undo category reorder operation
     */
    async undoCategoryReorder(operation) {
        const csrfToken = document.querySelector('[name=csrf_token]');
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }
        
        const response = await fetch('/api/menu/reorder-categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken.value
            },
            body: JSON.stringify({
                categories: [{
                    id: operation.elementId,
                    display_order: operation.oldIndex
                }]
            })
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 302) {
                throw new Error('Authentication required. Please log in again.');
            }
            throw new Error(`Failed to undo category reorder: ${response.status} ${response.statusText}`);
        }
        
        // Update UI
        this.updateCategoryOrder(operation.elementId, operation.oldIndex);
    }

    /**
     * Redo category reorder operation
     */
    async redoCategoryReorder(operation) {
        const csrfToken = document.querySelector('[name=csrf_token]');
        if (!csrfToken) {
            throw new Error('CSRF token not found');
        }
        
        const response = await fetch('/api/menu/reorder-categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken.value
            },
            body: JSON.stringify({
                categories: [{
                    id: operation.elementId,
                    display_order: operation.newIndex
                }]
            })
        });
        
        if (!response.ok) {
            if (response.status === 401 || response.status === 302) {
                throw new Error('Authentication required. Please log in again.');
            }
            throw new Error(`Failed to redo category reorder: ${response.status} ${response.statusText}`);
        }
        
        // Update UI
        this.updateCategoryOrder(operation.elementId, operation.newIndex);
    }

    /**
     * Update menu item order in UI
     */
    updateMenuItemOrder(itemId, newOrder) {
        const item = document.querySelector(`[data-item-id="${itemId}"]`);
        if (item) {
            const orderIndicator = item.querySelector('[data-order-indicator]');
            if (orderIndicator) {
                orderIndicator.textContent = newOrder + 1;
                orderIndicator.classList.add('updated');
                setTimeout(() => orderIndicator.classList.remove('updated'), 600);
            }
        }
    }

    /**
     * Update category order in UI
     */
    updateCategoryOrder(categoryId, newOrder) {
        const category = document.querySelector(`[data-category-id="${categoryId}"]`);
        if (category) {
            const orderIndicator = category.querySelector('[data-order-indicator]');
            if (orderIndicator) {
                orderIndicator.textContent = newOrder + 1;
                orderIndicator.classList.add('updated');
                setTimeout(() => orderIndicator.classList.remove('updated'), 600);
            }
        }
    }

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts(event) {
        // Ctrl+Z for undo
        if (event.ctrlKey && event.key === 'z' && !event.shiftKey) {
            event.preventDefault();
            this.undo();
        }
        
        // Ctrl+Shift+Z or Ctrl+Y for redo
        if ((event.ctrlKey && event.shiftKey && event.key === 'Z') || 
            (event.ctrlKey && event.key === 'y')) {
            event.preventDefault();
            this.redo();
        }
        
        // Ctrl+S for save
        if (event.ctrlKey && event.key === 's') {
            event.preventDefault();
            this.saveCurrentOrder();
        }
    }

    /**
     * Update undo/redo button states
     */
    updateUndoRedoState() {
        const undoButton = document.querySelector('[data-action="undo"]');
        const redoButton = document.querySelector('[data-action="redo"]');
        
        if (undoButton) {
            undoButton.disabled = this.historyIndex < 0;
            undoButton.classList.toggle('opacity-50', this.historyIndex < 0);
        }
        
        if (redoButton) {
            redoButton.disabled = this.historyIndex >= this.history.length - 1;
            redoButton.classList.toggle('opacity-50', this.historyIndex >= this.history.length - 1);
        }
    }

    /**
     * Save current order
     */
    async saveCurrentOrder() {
        this.isReordering = true;
        
        try {
            // Get all menu items and their current order
            const menuItems = document.querySelectorAll('.menu-item-card');
            const itemsData = Array.from(menuItems).map((item, index) => ({
                id: item.dataset.itemId,
                display_order: index
            }));
            
            // Get all categories and their current order
            const categories = document.querySelectorAll('.category-item');
            const categoriesData = Array.from(categories).map((category, index) => ({
                id: category.dataset.categoryId,
                display_order: index
            }));
            
            // Get CSRF token once
            const csrfToken = document.querySelector('[name=csrf_token]');
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }
            
            // Save both
            await Promise.all([
                fetch('/api/menu/reorder-items', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken.value
                    },
                    body: JSON.stringify({ items: itemsData })
                }).catch(error => {
                    console.error('Failed to save menu items order:', error);
                    this.showNotification('Failed to save menu items order', 'error');
                }),
                fetch('/api/menu/reorder-categories', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken.value
                    },
                    body: JSON.stringify({ categories: categoriesData })
                }).catch(error => {
                    console.error('Failed to save categories order:', error);
                    this.showNotification('Failed to save categories order', 'error');
                })
            ]);
            
            this.updateLastSaveTime();
            this.showNotification('Order saved successfully', 'success');
        } catch (error) {
            console.error('Save failed:', error);
            this.showNotification('Failed to save order', 'error');
        } finally {
            this.isReordering = false;
        }
    }

    /**
     * Reset to alphabetical order
     */
    async resetToAlphabetical(categoryId = null) {
        this.isReordering = true;
        
        try {
            const csrfToken = document.querySelector('[name=csrf_token]');
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }
            
            const response = await fetch('/api/menu/bulk-reorder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken.value
                },
                body: JSON.stringify({
                    operation: 'reset_alphabetical',
                    category_id: categoryId
                })
            });
            
            if (response.ok) {
                this.showNotification('Reset to alphabetical order', 'success');
                // Reload page to show updated order
                setTimeout(() => window.location.reload(), 500);
            } else {
                if (response.status === 401 || response.status === 302) {
                    this.showNotification('Authentication required. Please log in again.', 'error');
                } else {
                    throw new Error(`Failed to reset order: ${response.status} ${response.statusText}`);
                }
            }
        } catch (error) {
            console.error('Reset failed:', error);
            this.showNotification('Failed to reset order', 'error');
        } finally {
            this.isReordering = false;
        }
    }

    /**
     * Sort by price
     */
    async sortByPrice(categoryId = null, ascending = true) {
        this.isReordering = true;
        
        try {
            const csrfToken = document.querySelector('[name=csrf_token]');
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }
            
            const response = await fetch('/api/menu/bulk-reorder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken.value
                },
                body: JSON.stringify({
                    operation: 'sort_by_price',
                    category_id: categoryId,
                    ascending
                })
            });
            
            if (response.ok) {
                this.showNotification(`Sorted by price (${ascending ? 'low to high' : 'high to low'})`, 'success');
                // Reload page to show updated order
                setTimeout(() => window.location.reload(), 500);
            } else {
                if (response.status === 401 || response.status === 302) {
                    this.showNotification('Authentication required. Please log in again.', 'error');
                } else {
                    throw new Error(`Failed to sort by price: ${response.status} ${response.statusText}`);
                }
            }
        } catch (error) {
            console.error('Sort failed:', error);
            this.showNotification('Failed to sort by price', 'error');
        } finally {
            this.isReordering = false;
        }
    }

    /**
     * Export current order
     */
    exportOrder() {
        const menuItems = document.querySelectorAll('.menu-item-card');
        const categories = document.querySelectorAll('.category-item');
        
        const exportData = {
            timestamp: new Date().toISOString(),
            categories: Array.from(categories).map((category, index) => ({
                id: category.dataset.categoryId,
                name: category.querySelector('h3')?.textContent,
                order: index
            })),
            items: Array.from(menuItems).map((item, index) => ({
                id: item.dataset.itemId,
                name: item.querySelector('h3')?.textContent,
                price: item.querySelector('.text-blue-600')?.textContent,
                category: item.closest('[data-category-id]')?.dataset.categoryId,
                order: index
            }))
        };
        
        // Create and download JSON file
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `menu-order-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification('Order exported successfully', 'success');
    }

    /**
     * Update last save time
     */
    updateLastSaveTime() {
        this.lastSaveTime = new Date();
        
        // Update UI elements showing last save time
        const lastSaveElements = document.querySelectorAll('[data-last-saved]');
        lastSaveElements.forEach(element => {
            element.textContent = this.lastSaveTime.toLocaleTimeString();
        });
    }

    /**
     * Start auto-save
     */
    startAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            if (!this.isReordering) {
                this.saveCurrentOrder();
            }
        }, 60000); // Auto-save every minute
    }

    /**
     * Save history to localStorage
     */
    saveHistory() {
        try {
            localStorage.setItem('menu-reorder-history', JSON.stringify(this.history));
            localStorage.setItem('menu-reorder-index', this.historyIndex.toString());
        } catch (error) {
            console.error('Failed to save history:', error);
        }
    }

    /**
     * Load history from localStorage
     */
    loadHistory() {
        try {
            const history = localStorage.getItem('menu-reorder-history');
            const index = localStorage.getItem('menu-reorder-index');
            
            if (history) {
                this.history = JSON.parse(history);
                this.historyIndex = index ? parseInt(index) : -1;
                this.updateUndoRedoState();
            }
        } catch (error) {
            console.error('Failed to load history:', error);
        }
    }

    /**
     * Save state before page unload
     */
    saveState() {
        this.saveHistory();
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        window.dispatchEvent(new CustomEvent('showNotification', {
            detail: { message, type }
        }));
    }

    /**
     * Destroy reordering utilities
     */
    destroy() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        window.removeEventListener('menu-reorder', this.handleReorderEvent.bind(this));
        window.removeEventListener('category-reorder', this.handleCategoryReorderEvent.bind(this));
        document.removeEventListener('keydown', this.handleKeyboardShortcuts.bind(this));
        window.removeEventListener('beforeunload', this.saveState.bind(this));
    }
}

// Initialize reordering utilities when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.reorderingUtils = new ReorderingUtils();
    window.reorderingUtils.init();
});

// Make available globally
window.ReorderingUtils = ReorderingUtils;