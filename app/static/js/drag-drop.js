/**
 * Reusable Drag and Drop Component for Menu Reordering
 * Supports touch devices, keyboard navigation, and smooth animations
 */

class DragDropManager {
    constructor(options = {}) {
        this.options = {
            containerSelector: options.containerSelector || '.drag-container',
            itemSelector: options.itemSelector || '.drag-item',
            handleSelector: options.handleSelector || '.drag-handle',
            dropZoneSelector: options.dropZoneSelector || '.drop-zone',
            draggableClass: options.draggableClass || 'draggable',
            draggingClass: options.draggingClass || 'dragging',
            dropZoneActiveClass: options.dropZoneActiveClass || 'drop-zone-active',
            placeholderClass: options.placeholderClass || 'drag-placeholder',
            animationDuration: options.animationDuration || 200,
            onDragStart: options.onDragStart || (() => {}),
            onDragEnd: options.onDragEnd || (() => {}),
            onDrop: options.onDrop || (() => {}),
            onReorder: options.onReorder || (() => {}),
            ...options
        };

        this.draggedElement = null;
        this.placeholder = null;
        this.originalIndex = -1;
        this.touchOffset = { x: 0, y: 0 };
        this.isTouchDevice = 'ontouchstart' in window;
        this.keyboardNavigation = false;
        this.focusedIndex = -1;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupKeyboardNavigation();
        this.setupTouchSupport();
    }

    setupEventListeners() {
        document.addEventListener('mousedown', this.handleMouseDown.bind(this));
        document.addEventListener('mousemove', this.handleMouseMove.bind(this));
        document.addEventListener('mouseup', this.handleMouseUp.bind(this));
        
        // Touch events
        document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this.handleTouchEnd.bind(this));

        // Keyboard events
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
        document.addEventListener('focus', this.handleFocus.bind(this), true);
    }

    setupKeyboardNavigation() {
        // Enable keyboard navigation for accessibility
        this.keyboardNavigation = true;
    }

    setupTouchSupport() {
        // Add touch-specific styles if needed
        if (this.isTouchDevice) {
            if (window.bodyClassManager) {
                window.bodyClassManager.addImmediateClass('touch-device');
            } else {
                // Fallback to direct manipulation
                document.body.classList.add('touch-device');
            }
        }
    }

    handleMouseDown(e) {
        if (this.isTouchDevice) return; // Let touch events handle on touch devices
        
        const handle = e.target.closest(this.options.handleSelector);
        if (!handle) return;

        e.preventDefault();
        this.startDrag(e.target.closest(this.options.itemSelector), e.clientX, e.clientY);
    }

    handleMouseMove(e) {
        if (!this.draggedElement) return;
        
        e.preventDefault();
        this.updateDragPosition(e.clientX, e.clientY);
    }

    handleMouseUp(e) {
        if (!this.draggedElement) return;
        
        e.preventDefault();
        this.endDrag();
    }

    handleTouchStart(e) {
        const handle = e.target.closest(this.options.handleSelector);
        if (!handle) return;

        e.preventDefault();
        const touch = e.touches[0];
        const item = e.target.closest(this.options.itemSelector);
        
        this.touchOffset.x = touch.clientX - item.getBoundingClientRect().left;
        this.touchOffset.y = touch.clientY - item.getBoundingClientRect().top;
        
        this.startDrag(item, touch.clientX, touch.clientY);
    }

    handleTouchMove(e) {
        if (!this.draggedElement) return;
        
        e.preventDefault();
        const touch = e.touches[0];
        this.updateDragPosition(touch.clientX, touch.clientY);
    }

    handleTouchEnd(e) {
        if (!this.draggedElement) return;
        
        e.preventDefault();
        this.endDrag();
    }

    handleKeyDown(e) {
        if (!this.keyboardNavigation || this.focusedIndex === -1) return;

        const container = document.querySelector(this.options.containerSelector);
        const items = Array.from(container.querySelectorAll(this.options.itemSelector));
        
        switch (e.key) {
            case 'ArrowUp':
                e.preventDefault();
                this.moveFocus(-1, items);
                break;
            case 'ArrowDown':
                e.preventDefault();
                this.moveFocus(1, items);
                break;
            case ' ':
            case 'Enter':
                e.preventDefault();
                if (this.focusedIndex >= 0 && this.focusedIndex < items.length) {
                    this.startKeyboardDrag(items[this.focusedIndex]);
                }
                break;
            case 'Escape':
                e.preventDefault();
                this.cancelKeyboardDrag();
                break;
        }
    }

    handleFocus(e) {
        const item = e.target.closest(this.options.itemSelector);
        if (item) {
            const container = item.closest(this.options.containerSelector);
            const items = Array.from(container.querySelectorAll(this.options.itemSelector));
            this.focusedIndex = items.indexOf(item);
        }
    }

    startDrag(element, clientX, clientY) {
        if (!element || element.classList.contains(this.options.draggingClass)) return;

        this.draggedElement = element;
        this.originalIndex = this.getElementIndex(element);
        
        // Create placeholder
        this.placeholder = this.createPlaceholder(element);
        element.parentNode.insertBefore(this.placeholder, element);
        
        // Setup dragged element
        element.classList.add(this.options.draggingClass);
        element.style.position = 'fixed';
        element.style.zIndex = '1000';
        element.style.width = `${element.offsetWidth}px`;
        element.style.height = `${element.offsetHeight}px`;
        element.style.pointerEvents = 'none';
        
        // Add to body for proper positioning
        document.body.appendChild(element);
        
        this.updateDragPosition(clientX, clientY);
        
        // Call callback
        this.options.onDragStart(element, this.originalIndex);
        
        // Show notification
        this.showNotification('Dragging item. Move to desired position and release.', 'info');
    }

    updateDragPosition(clientX, clientY) {
        if (!this.draggedElement) return;

        // Update dragged element position
        this.draggedElement.style.left = `${clientX - this.touchOffset.x}px`;
        this.draggedElement.style.top = `${clientY - this.touchOffset.y}px`;

        // Find drop target
        const dropTarget = this.getDropTarget(clientX, clientY);
        this.updateDropZone(dropTarget);
    }

    getDropTarget(clientX, clientY) {
        const containers = document.querySelectorAll(this.options.containerSelector);
        
        for (const container of containers) {
            const rect = container.getBoundingClientRect();
            if (clientX >= rect.left && clientX <= rect.right && 
                clientY >= rect.top && clientY <= rect.bottom) {
                
                const items = Array.from(container.querySelectorAll(this.options.itemSelector));
                
                for (let i = 0; i < items.length; i++) {
                    const item = items[i];
                    if (item === this.draggedElement || item.classList.contains(this.options.draggingClass)) continue;
                    
                    const itemRect = item.getBoundingClientRect();
                    const midpoint = itemRect.top + itemRect.height / 2;
                    
                    if (clientY < midpoint) {
                        return { container, item, position: 'before', index: i };
                    }
                }
                
                return { container, item: null, position: 'after', index: items.length };
            }
        }
        
        return null;
    }

    updateDropZone(dropTarget) {
        // Remove all active drop zones
        document.querySelectorAll(`.${this.options.dropZoneActiveClass}`).forEach(el => {
            el.classList.remove(this.options.dropZoneActiveClass);
        });

        if (dropTarget) {
            if (dropTarget.item) {
                dropTarget.item.classList.add(this.options.dropZoneActiveClass);
            } else {
                dropTarget.container.classList.add(this.options.dropZoneActiveClass);
            }
        }
    }

    endDrag() {
        if (!this.draggedElement) return;

        const dropTarget = this.getDropTarget(
            parseInt(this.draggedElement.style.left) + this.touchOffset.x,
            parseInt(this.draggedElement.style.top) + this.touchOffset.y
        );

        if (dropTarget) {
            this.performReorder(dropTarget);
        } else {
            // Return to original position
            this.placeholder.parentNode.insertBefore(this.draggedElement, this.placeholder);
        }

        this.cleanup();
    }

    performReorder(dropTarget) {
        const newIndex = dropTarget.index;
        
        if (newIndex !== this.originalIndex) {
            // Insert at new position
            const container = dropTarget.container;
            const items = Array.from(container.querySelectorAll(this.options.itemSelector));
            
            if (dropTarget.position === 'before' && dropTarget.item) {
                container.insertBefore(this.draggedElement, dropTarget.item);
            } else if (dropTarget.position === 'after') {
                container.appendChild(this.draggedElement);
            }
            
            // Update display orders
            this.updateDisplayOrders(container);
            
            // Call reorder callback
            this.options.onReorder(this.draggedElement, this.originalIndex, newIndex, container);
            
            this.showNotification('Item order updated successfully', 'success');
        } else {
            // Return to original position
            this.placeholder.parentNode.insertBefore(this.draggedElement, this.placeholder);
        }
    }

    updateDisplayOrders(container) {
        const items = Array.from(container.querySelectorAll(this.options.itemSelector));
        items.forEach((item, index) => {
            const orderInput = item.querySelector('[data-display-order]');
            if (orderInput) {
                orderInput.value = index;
                orderInput.dataset.displayOrder = index;
            }
            
            // Update visual order indicator
            const orderIndicator = item.querySelector('[data-order-indicator]');
            if (orderIndicator) {
                orderIndicator.textContent = index + 1;
            }
        });
    }

    createPlaceholder(element) {
        const placeholder = document.createElement('div');
        placeholder.className = this.options.placeholderClass;
        placeholder.style.width = `${element.offsetWidth}px`;
        placeholder.style.height = `${element.offsetHeight}px`;
        placeholder.style.opacity = '0.5';
        placeholder.style.border = '2px dashed #3B82F6';
        placeholder.style.borderRadius = '0.5rem';
        placeholder.innerHTML = '<div class="flex items-center justify-center h-full text-blue-500"><i class="fas fa-arrows-alt"></i></div>';
        return placeholder;
    }

    cleanup() {
        if (this.draggedElement) {
            this.draggedElement.classList.remove(this.options.draggingClass);
            this.draggedElement.style.position = '';
            this.draggedElement.style.zIndex = '';
            this.draggedElement.style.width = '';
            this.draggedElement.style.height = '';
            this.draggedElement.style.left = '';
            this.draggedElement.style.top = '';
            this.draggedElement.style.pointerEvents = '';
        }

        if (this.placeholder) {
            this.placeholder.remove();
        }

        // Remove active drop zones
        document.querySelectorAll(`.${this.options.dropZoneActiveClass}`).forEach(el => {
            el.classList.remove(this.options.dropZoneActiveClass);
        });

        this.options.onDragEnd(this.draggedElement);
        
        this.draggedElement = null;
        this.placeholder = null;
        this.originalIndex = -1;
    }

    // Keyboard navigation methods
    moveFocus(direction, items) {
        this.focusedIndex = Math.max(0, Math.min(items.length - 1, this.focusedIndex + direction));
        items[this.focusedIndex].focus();
    }

    startKeyboardDrag(element) {
        this.startDrag(element, element.getBoundingClientRect().left, element.getBoundingClientRect().top);
        this.keyboardNavigation = true;
    }

    cancelKeyboardDrag() {
        if (this.draggedElement) {
            this.cleanup();
        }
    }

    getElementIndex(element) {
        const container = element.closest(this.options.containerSelector);
        const items = Array.from(container.querySelectorAll(this.options.itemSelector));
        return items.indexOf(element);
    }

    showNotification(message, type = 'info') {
        // Dispatch event for global notification system
        window.dispatchEvent(new CustomEvent('showNotification', {
            detail: { message, type }
        }));
    }

    // Public methods
    destroy() {
        document.removeEventListener('mousedown', this.handleMouseDown.bind(this));
        document.removeEventListener('mousemove', this.handleMouseMove.bind(this));
        document.removeEventListener('mouseup', this.handleMouseUp.bind(this));
        document.removeEventListener('touchstart', this.handleTouchStart.bind(this));
        document.removeEventListener('touchmove', this.handleTouchMove.bind(this));
        document.removeEventListener('touchend', this.handleTouchEnd.bind(this));
        document.removeEventListener('keydown', this.handleKeyDown.bind(this));
        document.removeEventListener('focus', this.handleFocus.bind(this), true);
        
        this.cleanup();
    }
}

// Utility function to initialize drag-drop on menu items
window.MenuDragDrop = {
    instances: [],
    
    init: function(options = {}) {
        const defaultOptions = {
            containerSelector: '.menu-items-container',
            itemSelector: '.menu-item-card',
            handleSelector: '.drag-handle',
            onReorder: (element, oldIndex, newIndex, container) => {
                // Save reorder to server
                this.saveReorder(element.dataset.itemId, oldIndex, newIndex, container);
            }
        };
        
        const instance = new DragDropManager({ ...defaultOptions, ...options });
        this.instances.push(instance);
        return instance;
    },
    
    initCategories: function(options = {}) {
        const defaultOptions = {
            containerSelector: '.categories-container',
            itemSelector: '.category-item',
            handleSelector: '.drag-handle',
            onReorder: (element, oldIndex, newIndex, container) => {
                // Save category reorder to server
                this.saveCategoryReorder(element.dataset.categoryId, oldIndex, newIndex);
            }
        };
        
        const instance = new DragDropManager({ ...defaultOptions, ...options });
        this.instances.push(instance);
        return instance;
    },
    
    saveReorder: async function(itemId, oldIndex, newIndex, container) {
        try {
            const items = Array.from(container.querySelectorAll('.menu-item-card'));
            const reorderData = items.map((item, index) => ({
                id: item.dataset.itemId,
                display_order: index
            }));
            
            const response = await fetch('/api/menu/reorder-items', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]').value
                },
                body: JSON.stringify({
                    items: reorderData,
                    category_id: container.dataset.categoryId
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to save reorder');
            }
            
            // Update order indicators
            items.forEach((item, index) => {
                const indicator = item.querySelector('[data-order-indicator]');
                if (indicator) {
                    indicator.textContent = index + 1;
                }
            });
            
        } catch (error) {
            console.error('Error saving reorder:', error);
            window.dispatchEvent(new CustomEvent('showNotification', {
                detail: { message: 'Failed to save new order', type: 'error' }
            }));
        }
    },
    
    saveCategoryReorder: async function(categoryId, oldIndex, newIndex) {
        try {
            const container = document.querySelector('.categories-container');
            const categories = Array.from(container.querySelectorAll('.category-item'));
            const reorderData = categories.map((category, index) => ({
                id: category.dataset.categoryId,
                display_order: index
            }));
            
            const response = await fetch('/api/menu/reorder-categories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf_token]').value
                },
                body: JSON.stringify({
                    categories: reorderData
                })
            });
            
            if (!response.ok) {
                throw new Error('Failed to save category reorder');
            }
            
            // Update order indicators
            categories.forEach((category, index) => {
                const indicator = category.querySelector('[data-order-indicator]');
                if (indicator) {
                    indicator.textContent = index + 1;
                }
            });
            
        } catch (error) {
            console.error('Error saving category reorder:', error);
            window.dispatchEvent(new CustomEvent('showNotification', {
                detail: { message: 'Failed to save new category order', type: 'error' }
            }));
        }
    },
    
    destroyAll: function() {
        this.instances.forEach(instance => instance.destroy());
        this.instances = [];
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize menu items drag-drop
    const menuContainers = document.querySelectorAll('.menu-items-container');
    menuContainers.forEach(container => {
        window.MenuDragDrop.init({
            containerSelector: `#${container.id}`,
            itemSelector: '.menu-item-card',
            handleSelector: '.drag-handle'
        });
    });
    
    // Initialize categories drag-drop
    const categoryContainers = document.querySelectorAll('.categories-container');
    categoryContainers.forEach(container => {
        window.MenuDragDrop.initCategories({
            containerSelector: `#${container.id}`,
            itemSelector: '.category-item',
            handleSelector: '.drag-handle'
        });
    });
});