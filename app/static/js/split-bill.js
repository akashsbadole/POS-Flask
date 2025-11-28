/**
 * Split Bill JavaScript Module
 * Handles advanced split bill functionality with equal split, custom amounts, and item-based splitting
 */

class SplitBillManager {
    constructor() {
        this.orderId = null;
        this.orderData = null;
        this.splits = [];
        this.splitType = 'equal';
        this.numberOfSplits = 2;
        this.balanceDue = 0;
        
        this.init();
    }
    
    init() {
        // Initialize event listeners
        this.setupEventListeners();
        
        // Initialize keyboard shortcuts
        this.setupKeyboardShortcuts();
    }
    
    setupEventListeners() {
        // Close modal when clicking outside
        document.addEventListener('click', (e) => {
            const splitBillModal = document.getElementById('split-bill-modal');
            if (splitBillModal && splitBillModal.style.display === 'block' && 
                e.target === splitBillModal) {
                this.closeModal();
            }
        });
        
        // Handle escape key to close modal
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        });
        
        // Handle form submission
        const splitBillForm = document.querySelector('#split-bill-modal form');
        if (splitBillForm) {
            splitBillForm.addEventListener('submit', (e) => {
                this.handleFormSubmit(e);
            });
        }
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+Shift+B to open split bill modal
            if (e.ctrlKey && e.shiftKey && e.key === 'B') {
                e.preventDefault();
                this.openModal();
            }
        });
    }
    
    openModal(orderId = null) {
        const modal = document.getElementById('split-bill-modal');
        if (!modal) return;
        
        if (orderId) {
            this.orderId = orderId;
            this.loadOrderData(orderId);
        }
        
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        
        // Focus on first input
        setTimeout(() => {
            const firstInput = modal.querySelector('input, select, button');
            if (firstInput) firstInput.focus();
        }, 100);
    }
    
    closeModal() {
        const modal = document.getElementById('split-bill-modal');
        if (!modal) return;
        
        modal.style.display = 'none';
        document.body.style.overflow = '';
        
        // Reset form
        this.resetForm();
    }
    
    resetForm() {
        // Reset Alpine.js data if available
        if (window.Alpine && window.Alpine.store) {
            // This will be handled by Alpine.js in the template
        }
    }
    
    async loadOrderData(orderId) {
        try {
            const response = await fetch(`/api/orders/${orderId}`);
            if (!response.ok) throw new Error('Failed to load order data');
            
            this.orderData = await response.json();
            this.balanceDue = this.orderData.balance_due;
            
            // Update modal with order data
            this.updateModalWithData();
            
        } catch (error) {
            console.error('Error loading order data:', error);
            this.showNotification('Error loading order data', 'error');
        }
    }
    
    updateModalWithData() {
        if (!this.orderData) return;
        
        // Update balance display
        const balanceElements = document.querySelectorAll('[data-balance-due]');
        balanceElements.forEach(el => {
            el.textContent = `₹${this.balanceDue.toFixed(2)}`;
        });
        
        // Update order items display
        this.updateOrderItemsDisplay();
    }
    
    updateOrderItemsDisplay() {
        const itemsContainer = document.querySelector('[data-order-items]');
        if (!itemsContainer || !this.orderData.items) return;
        
        itemsContainer.innerHTML = '';
        
        this.orderData.items.forEach(item => {
            const itemElement = this.createOrderItemElement(item);
            itemsContainer.appendChild(itemElement);
        });
    }
    
    createOrderItemElement(item) {
        const div = document.createElement('div');
        div.className = 'flex items-center justify-between p-2 bg-gray-50 rounded mb-2';
        div.innerHTML = `
            <div class="flex-1">
                <span class="text-sm font-medium">${item.quantity}x ${item.item_name}</span>
                <span class="text-xs text-gray-500 ml-2">₹${item.total_price.toFixed(2)}</span>
            </div>
            <div class="flex space-x-1" data-item-id="${item.id}">
                <!-- Split assignment buttons will be added by Alpine.js -->
            </div>
        `;
        return div;
    }
    
    async handleFormSubmit(e) {
        e.preventDefault();
        
        const form = e.target;
        const formData = new FormData(form);
        
        try {
            // Validate split data
            if (!this.validateSplitData(formData)) {
                return;
            }
            
            // Submit split payment
            const response = await fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || 'Payment processing failed');
            }
            
            const result = await response.json();
            
            // Show success message
            this.showNotification('Split payment processed successfully!', 'success');
            
            // Close modal
            this.closeModal();
            
            // Update order totals if needed
            if (result.update_totals) {
                this.updateOrderTotals(result.order_data);
            }
            
            // Redirect if needed
            if (result.redirect) {
                setTimeout(() => {
                    window.location.href = result.redirect;
                }, 1000);
            }
            
        } catch (error) {
            console.error('Error processing split payment:', error);
            this.showNotification(error.message || 'Error processing payment', 'error');
        }
    }
    
    validateSplitData(formData) {
        const splitNames = formData.getAll('split_name[]');
        const splitAmounts = formData.getAll('split_amount[]');
        const splitPaymentMethods = formData.getAll('split_payment_method[]');
        
        // Check if all required fields are present
        if (splitNames.length === 0 || splitAmounts.length === 0 || splitPaymentMethods.length === 0) {
            this.showNotification('Please fill in all split details', 'error');
            return false;
        }
        
        // Calculate total allocated
        let totalAllocated = 0;
        for (let i = 0; i < splitAmounts.length; i++) {
            const amount = parseFloat(splitAmounts[i]);
            if (isNaN(amount) || amount <= 0) {
                this.showNotification(`Invalid amount for ${splitNames[i]}`, 'error');
                return false;
            }
            totalAllocated += amount;
        }
        
        // Check if total matches balance due
        const tolerance = 0.01; // Small tolerance for floating point
        if (Math.abs(totalAllocated - this.balanceDue) > tolerance) {
            this.showNotification(`Total allocated (₹${totalAllocated.toFixed(2)}) must equal balance due (₹${this.balanceDue.toFixed(2)})`, 'error');
            return false;
        }
        
        return true;
    }
    
    updateOrderTotals(orderData) {
        const totalsContainer = document.getElementById('order-totals');
        if (!totalsContainer) return;
        
        // Update with HTMX if available, otherwise manual update
        if (window.htmx) {
            htmx.trigger('#order-totals', 'updateTotals', { orderData });
        } else {
            // Manual update would go here
            console.log('Order totals updated:', orderData);
        }
    }
    
    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg max-w-sm ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.innerHTML = `
            <div class="flex items-center">
                <div class="flex-1">${message}</div>
                <button onclick="this.parentElement.parentElement.remove()" class="ml-4 text-white hover:text-gray-200">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
    
    // Utility methods for split calculations
    calculateEqualSplit(totalAmount, numberOfSplits) {
        return totalAmount / numberOfSplits;
    }
    
    calculateItemSplit(items, splitAssignments) {
        const splits = {};
        
        // Initialize splits
        splitAssignments.forEach(assignment => {
            splits[assignment.splitId] = {
                items: [],
                total: 0
            };
        });
        
        // Assign items to splits
        items.forEach(item => {
            const assignment = splitAssignments.find(a => a.itemId === item.id);
            if (assignment) {
                splits[assignment.splitId].items.push(item);
                splits[assignment.splitId].total += item.total_price;
            }
        });
        
        return splits;
    }
    
    validateCustomSplitAmounts(amounts, totalAmount) {
        const total = amounts.reduce((sum, amount) => sum + parseFloat(amount), 0);
        return Math.abs(total - totalAmount) < 0.01;
    }
}

// Initialize split bill manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.splitBillManager = new SplitBillManager();
    
    // Make it globally available for inline scripts
    window.openSplitBillModal = (orderId) => {
        window.splitBillManager.openModal(orderId);
    };
    
    window.closeSplitBillModal = () => {
        window.splitBillManager.closeModal();
    };
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SplitBillManager;
}