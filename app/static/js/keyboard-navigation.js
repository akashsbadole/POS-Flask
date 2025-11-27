/**
 * Keyboard Navigation System for Restaurant POS
 * Provides comprehensive keyboard shortcuts and accessibility features
 */

class KeyboardNavigation {
    constructor() {
        this.shortcuts = new Map();
        this.currentFocusIndex = -1;
        this.focusableElements = [];
        this.modalOpen = false;
        this.searchMode = false;
        
        this.init();
    }

    init() {
        console.log('Initializing keyboard navigation system...');
        
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setupKeyboardShortcuts();
                this.setupAccessibilityFeatures();
                this.setupNavigationHelpers();
            });
        } else {
            this.setupKeyboardShortcuts();
            this.setupAccessibilityFeatures();
            this.setupNavigationHelpers();
        }
    }

    setupKeyboardShortcuts() {
        // Global shortcuts
        this.registerShortcut('ctrl+/', 'showHelp', 'Show keyboard shortcuts help');
        this.registerShortcut('ctrl+k', 'focusSearch', 'Focus search bar');
        this.registerShortcut('escape', 'escapeAction', 'Escape/cancel current action');
        this.registerShortcut('ctrl+n', 'toggleNotifications', 'Toggle notifications panel');
        this.registerShortcut('ctrl+b', 'toggleSidebar', 'Toggle sidebar');
        
        // Navigation shortcuts (for managers)
        this.registerShortcut('alt+1', 'navigateToDashboard', 'Go to Dashboard');
        this.registerShortcut('alt+2', 'navigateToMenu', 'Go to Menu');
        this.registerShortcut('alt+3', 'navigateToTables', 'Go to Tables');
        this.registerShortcut('alt+4', 'navigateToReports', 'Go to Reports');
        this.registerShortcut('alt+5', 'navigateToInventory', 'Go to Inventory');
        this.registerShortcut('alt+6', 'navigateToBilling', 'Go to Billing');
        this.registerShortcut('alt+7', 'navigateToSettings', 'Go to Settings');
        
        // Form shortcuts
        this.registerShortcut('ctrl+s', 'saveForm', 'Save current form');
        this.registerShortcut('ctrl+enter', 'submitForm', 'Submit current form');
        this.registerShortcut('tab', 'navigateForm', 'Navigate form fields', true);
        this.registerShortcut('shift+tab', 'navigateFormBackward', 'Navigate form fields backward', true);
        
        // Billing specific shortcuts
        this.registerShortcut('ctrl+i', 'newInvoice', 'Create new invoice');
        this.registerShortcut('ctrl+p', 'printReceipt', 'Print receipt/invoice');
        this.registerShortcut('ctrl+d', 'addDiscount', 'Add discount');
        this.registerShortcut('ctrl+shift+p', 'splitPayment', 'Split payment');
        this.registerShortcut('ctrl+shift+i', 'invoiceList', 'View invoice list');
        this.registerShortcut('ctrl+shift+r', 'recurringInvoice', 'Create recurring invoice');
        this.registerShortcut('ctrl+shift+s', 'invoiceSettings', 'Invoice settings');
        this.registerShortcut('ctrl+shift+v', 'viewInvoice', 'View current invoice');
        this.registerShortcut('ctrl+shift+e', 'editInvoice', 'Edit current invoice');
        this.registerShortcut('ctrl+shift+d', 'deleteInvoice', 'Delete current invoice');
        this.registerShortcut('ctrl+shift+t', 'generateReport', 'Generate billing report');
        
        // Cart shortcuts (for cashiers)
        this.registerShortcut('ctrl+plus', 'addToCart', 'Add selected item to cart');
        this.registerShortcut('ctrl+minus', 'removeFromCart', 'Remove selected item from cart');
        this.registerShortcut('f1', 'quickCash', 'Quick cash payment');
        this.registerShortcut('f2', 'quickCard', 'Quick card payment');
        this.registerShortcut('f3', 'quickUPI', 'Quick UPI payment');
        
        // Order management shortcuts
        this.registerShortcut('ctrl+o', 'orderList', 'View order list');
        this.registerShortcut('ctrl+shift+o', 'createOrder', 'Create new order');
        
        // Accessibility shortcuts
        this.registerShortcut('ctrl+alt+a', 'toggleAccessibility', 'Toggle accessibility mode');
        this.registerShortcut('ctrl+alt+1', 'increaseFontSize', 'Increase font size');
        this.registerShortcut('ctrl+alt+0', 'resetFontSize', 'Reset font size');
        
        // Setup event listener
        document.addEventListener('keydown', this.handleKeyDown.bind(this));
    }

    registerShortcut(key, action, description, preventDefault = true) {
        this.shortcuts.set(key.toLowerCase(), {
            action,
            description,
            preventDefault
        });
    }

    handleKeyDown(event) {
        const key = this.getKeyString(event);
        const shortcut = this.shortcuts.get(key);
        
        if (shortcut) {
            if (shortcut.preventDefault) {
                event.preventDefault();
            }
            
            this.executeAction(shortcut.action, event);
        }
    }

    getKeyString(event) {
        const parts = [];
        
        if (event.ctrlKey) parts.push('ctrl');
        if (event.altKey) parts.push('alt');
        if (event.shiftKey) parts.push('shift');
        
        let key = event.key.toLowerCase();
        
        // Handle special keys
        if (key === ' ') key = 'space';
        if (key === 'escape') key = 'escape';
        if (key === 'enter') key = 'enter';
        if (key === 'tab') key = 'tab';
        if (key === 'arrowup') key = 'up';
        if (key === 'arrowdown') key = 'down';
        if (key === 'arrowleft') key = 'left';
        if (key === 'arrowright') key = 'right';
        
        // Handle function keys
        if (key.startsWith('f') && key.length > 1) {
            key = key;
        }
        
        parts.push(key);
        return parts.join('+');
    }

    executeAction(action, event) {
        switch (action) {
            case 'showHelp':
                this.showHelpModal();
                break;
            case 'focusSearch':
                this.focusSearchBar();
                break;
            case 'escapeAction':
                this.handleEscape();
                break;
            case 'toggleNotifications':
                this.toggleNotifications();
                break;
            case 'toggleSidebar':
                this.toggleSidebar();
                break;
            case 'navigateToDashboard':
                this.navigateTo('/manager/dashboard');
                break;
            case 'navigateToMenu':
                this.navigateTo('/menu/dashboard');
                break;
            case 'navigateToTables':
                this.navigateTo('/tables/dashboard');
                break;
            case 'navigateToReports':
                this.navigateTo('/reports/dashboard');
                break;
            case 'navigateToInventory':
                this.navigateTo('/inventory/dashboard');
                break;
            case 'navigateToBilling':
                this.navigateTo('/billing/invoices');
                break;
            case 'navigateToSettings':
                this.navigateTo('/settings/dashboard');
                break;
            case 'saveForm':
                this.saveCurrentForm();
                break;
            case 'submitForm':
                this.submitCurrentForm();
                break;
            case 'navigateForm':
                this.navigateFormFields(1);
                break;
            case 'navigateFormBackward':
                this.navigateFormFields(-1);
                break;
            case 'newInvoice':
                this.navigateTo('/billing/invoice/new');
                break;
            case 'printReceipt':
                this.printCurrentReceipt();
                break;
            case 'addDiscount':
                this.openDiscountModal();
                break;
            case 'splitPayment':
                this.openSplitPaymentModal();
                break;
            case 'invoiceList':
                this.navigateTo('/billing/invoices');
                break;
            case 'recurringInvoice':
                this.navigateTo('/billing/recurring/new');
                break;
            case 'invoiceSettings':
                this.navigateTo('/billing/settings');
                break;
            case 'viewInvoice':
                this.viewCurrentInvoice();
                break;
            case 'editInvoice':
                this.editCurrentInvoice();
                break;
            case 'deleteInvoice':
                this.deleteCurrentInvoice();
                break;
            case 'generateReport':
                this.generateBillingReport();
                break;
            case 'addToCart':
                this.addSelectedToCart();
                break;
            case 'removeFromCart':
                this.removeFromCart();
                break;
            case 'quickCash':
                this.quickPayment('cash');
                break;
            case 'quickCard':
                this.quickPayment('card');
                break;
            case 'quickUPI':
                this.quickPayment('upi');
                break;
            case 'toggleAccessibility':
                this.toggleAccessibilityMode();
                break;
            case 'increaseFontSize':
                this.adjustFontSize(1);
                break;
            case 'resetFontSize':
                this.resetFontSize();
                break;
        }
    }

    setupAccessibilityFeatures() {
        // Add ARIA labels to navigation elements
        this.addAriaLabels();
        
        // Setup focus management
        this.setupFocusManagement();
        
        // Setup screen reader announcements
        this.setupScreenReaderAnnouncements();
        
        // Add skip links
        this.addSkipLinks();
    }

    addAriaLabels() {
        // Add ARIA labels to main navigation
        const navLinks = document.querySelectorAll('nav a');
        navLinks.forEach((link, index) => {
            if (!link.getAttribute('aria-label')) {
                link.setAttribute('aria-label', `Navigation item ${index + 1}: ${link.textContent.trim()}`);
            }
            link.setAttribute('role', 'menuitem');
        });

        // Add ARIA labels to buttons
        const buttons = document.querySelectorAll('button');
        buttons.forEach(button => {
            if (!button.getAttribute('aria-label') && button.textContent.trim()) {
                button.setAttribute('aria-label', button.textContent.trim());
            }
        });

        // Mark navigation regions
        const nav = document.querySelector('nav');
        if (nav) {
            nav.setAttribute('role', 'navigation');
            nav.setAttribute('aria-label', 'Main navigation');
        }

        // Mark main content
        const main = document.querySelector('main');
        if (main) {
            main.setAttribute('role', 'main');
            main.setAttribute('aria-label', 'Main content');
        }
    }

    setupFocusManagement() {
        // Track focusable elements
        this.updateFocusableElements();
        
        // Update focusable elements when DOM changes
        const observer = new MutationObserver(() => {
            this.updateFocusableElements();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['disabled', 'hidden', 'aria-hidden']
        });

        // Trap focus in modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                this.trapFocus(e);
            }
        });
    }

    updateFocusableElements() {
        const focusableSelectors = [
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
            '[contenteditable="true"]'
        ];

        this.focusableElements = Array.from(
            document.querySelectorAll(focusableSelectors.join(', '))
        ).filter(element => {
            // Filter out hidden elements
            const style = window.getComputedStyle(element);
            return style.display !== 'none' && 
                   style.visibility !== 'hidden' && 
                   element.offsetParent !== null;
        });
    }

    trapFocus(event) {
        const modal = document.querySelector('.modal:not(.hidden), [role="dialog"]:not([aria-hidden="true"])');
        
        if (modal) {
            const modalFocusableElements = this.focusableElements.filter(el => 
                modal.contains(el)
            );
            
            if (modalFocusableElements.length === 0) return;
            
            const firstElement = modalFocusableElements[0];
            const lastElement = modalFocusableElements[modalFocusableElements.length - 1];
            
            if (event.shiftKey) {
                if (document.activeElement === firstElement) {
                    event.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    event.preventDefault();
                    firstElement.focus();
                }
            }
        }
    }

    setupScreenReaderAnnouncements() {
        // Create live region for announcements
        if (!document.getElementById('sr-announcements')) {
            const liveRegion = document.createElement('div');
            liveRegion.id = 'sr-announcements';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('aria-atomic', 'true');
            liveRegion.className = 'sr-only';
            document.body.appendChild(liveRegion);
        }
    }

    addSkipLinks() {
        // Add skip to main content link
        if (!document.getElementById('skip-to-main')) {
            const skipLink = document.createElement('a');
            skipLink.id = 'skip-to-main';
            skipLink.href = '#main-content';
            skipLink.className = 'sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-blue-600 text-white px-4 py-2 rounded z-50';
            skipLink.textContent = 'Skip to main content';
            document.body.insertBefore(skipLink, document.body.firstChild);
        }

        // Add id to main content if not present
        const main = document.querySelector('main');
        if (main && !main.id) {
            main.id = 'main-content';
        }
    }

    setupNavigationHelpers() {
        // Add visual indicators for keyboard focus
        this.addFocusStyles();
        
        // Setup arrow key navigation for menus
        this.setupArrowKeyNavigation();
        
        // Setup home/end key navigation
        this.setupHomeEndNavigation();
    }

    addFocusStyles() {
        if (!document.getElementById('keyboard-nav-styles')) {
            const style = document.createElement('style');
            style.id = 'keyboard-nav-styles';
            style.textContent = `
                /* Enhanced focus styles for keyboard navigation */
                :focus {
                    outline: 3px solid #3b82f6 !important;
                    outline-offset: 2px !important;
                }
                
                /* Skip link styles */
                .sr-only {
                    position: absolute;
                    width: 1px;
                    height: 1px;
                    padding: 0;
                    margin: -1px;
                    overflow: hidden;
                    clip: rect(0, 0, 0, 0);
                    white-space: nowrap;
                    border: 0;
                }
                
                .focus\\:not-sr-only:focus {
                    position: static;
                    width: auto;
                    height: auto;
                    padding: inherit;
                    margin: inherit;
                    overflow: visible;
                    clip: auto;
                    white-space: normal;
                }
                
                /* High contrast mode support */
                @media (prefers-contrast: high) {
                    :focus {
                        outline: 4px solid #000000 !important;
                        background-color: #ffff00 !important;
                        color: #000000 !important;
                    }
                }
                
                /* Reduced motion support */
                @media (prefers-reduced-motion: reduce) {
                    * {
                        animation-duration: 0.01ms !important;
                        animation-iteration-count: 1 !important;
                        transition-duration: 0.01ms !important;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    setupArrowKeyNavigation() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                const menu = document.querySelector('[role="menu"]:focus-within, .dropdown:focus-within');
                if (menu) {
                    e.preventDefault();
                    this.navigateMenuItems(e.key === 'ArrowDown' ? 1 : -1);
                }
            }
        });
    }

    setupHomeEndNavigation() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Home' || e.key === 'End') {
                const menu = document.querySelector('[role="menu"]:focus-within, .dropdown:focus-within');
                if (menu) {
                    e.preventDefault();
                    const items = menu.querySelectorAll('[role="menuitem"], .dropdown-item');
                    if (items.length > 0) {
                        const targetIndex = e.key === 'Home' ? 0 : items.length - 1;
                        items[targetIndex].focus();
                    }
                }
            }
        });
    }

    // Action implementations
    showHelpModal() {
        const helpContent = this.generateHelpContent();
        this.showModal('Keyboard Shortcuts', helpContent);
    }

    generateHelpContent() {
        const categories = {
            'Global': ['ctrl+/', 'ctrl+k', 'escape', 'ctrl+n', 'ctrl+b'],
            'Navigation': ['alt+1', 'alt+2', 'alt+3', 'alt+4', 'alt+5', 'alt+6', 'alt+7'],
            'Forms': ['ctrl+s', 'ctrl+enter', 'tab', 'shift+tab'],
            'Billing': ['ctrl+i', 'ctrl+p', 'ctrl+d', 'ctrl+shift+p'],
            'Cart': ['ctrl+plus', 'ctrl+minus', 'f1', 'f2', 'f3'],
            'Accessibility': ['ctrl+alt+a', 'ctrl+alt+1', 'ctrl+alt+0']
        };

        let html = '<div class="space-y-4">';
        
        for (const [category, shortcuts] of Object.entries(categories)) {
            html += `<div class="mb-4">
                <h3 class="font-semibold text-lg mb-2">${category}</h3>
                <div class="space-y-1">`;
            
            shortcuts.forEach(shortcut => {
                const info = this.shortcuts.get(shortcut);
                if (info) {
                    html += `
                        <div class="flex justify-between items-center py-1">
                            <kbd class="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-sm">${shortcut}</kbd>
                            <span class="text-sm">${info.description}</span>
                        </div>
                    `;
                }
            });
            
            html += '</div></div>';
        }
        
        html += '</div>';
        return html;
    }

    focusSearchBar() {
        const searchInput = document.querySelector('input[type="text"][placeholder*="Search"], input[name="search"], #search');
        if (searchInput) {
            searchInput.focus();
            this.announceToScreenReader('Search bar focused');
        } else {
            this.announceToScreenReader('Search bar not found');
        }
    }

    handleEscape() {
        // Close modals
        const modals = document.querySelectorAll('.modal:not(.hidden), [role="dialog"]:not([aria-hidden="true"])');
        modals.forEach(modal => {
            modal.classList.add('hidden');
            modal.setAttribute('aria-hidden', 'true');
        });

        // Close dropdowns
        const dropdowns = document.querySelectorAll('.dropdown:not(.hidden)');
        dropdowns.forEach(dropdown => {
            dropdown.classList.add('hidden');
        });

        // Clear search
        const searchInput = document.querySelector('input[type="text"][placeholder*="Search"]');
        if (searchInput && searchInput.value) {
            searchInput.value = '';
            searchInput.dispatchEvent(new Event('input'));
        }

        this.announceToScreenReader('Action cancelled');
    }

    toggleNotifications() {
        const notificationButton = document.querySelector('[data-dropdown-target*="notification"], button:has(.fa-bell)');
        if (notificationButton) {
            notificationButton.click();
            this.announceToScreenReader('Notifications toggled');
        }
    }

    toggleSidebar() {
        const sidebarToggle = document.querySelector('button[onclick*="toggleSidebar"], button:has(.fa-bars)');
        if (sidebarToggle) {
            sidebarToggle.click();
            this.announceToScreenReader('Sidebar toggled');
        }
    }

    navigateTo(path) {
        if (window.location.pathname !== path) {
            window.location.href = path;
            this.announceToScreenReader(`Navigating to ${path}`);
        }
    }

    saveCurrentForm() {
        const saveButton = document.querySelector('button[type="submit"]:contains("Save"), button:contains("Save")');
        if (saveButton) {
            saveButton.click();
            this.announceToScreenReader('Form saved');
        } else {
            this.announceToScreenReader('No save button found');
        }
    }

    submitCurrentForm() {
        const form = document.querySelector('form');
        if (form) {
            form.requestSubmit();
            this.announceToScreenReader('Form submitted');
        } else {
            this.announceToScreenReader('No form found');
        }
    }

    navigateFormFields(direction) {
        const focusableInputs = this.focusableElements.filter(el => 
            el.matches('input, select, textarea, button') && 
            !el.matches('button[type="submit"]')
        );
        
        const currentIndex = focusableInputs.indexOf(document.activeElement);
        let nextIndex = currentIndex + direction;
        
        if (nextIndex < 0) nextIndex = focusableInputs.length - 1;
        if (nextIndex >= focusableInputs.length) nextIndex = 0;
        
        if (focusableInputs[nextIndex]) {
            focusableInputs[nextIndex].focus();
        }
    }

    printCurrentReceipt() {
        const printButton = document.querySelector('button:contains("Print"), button[onclick*="print"]');
        if (printButton) {
            printButton.click();
            this.announceToScreenReader('Printing receipt');
        } else {
            window.print();
            this.announceToScreenReader('Printing page');
        }
    }

    openDiscountModal() {
        const discountButton = document.querySelector('button:contains("Discount"), button[onclick*="discount"]');
        if (discountButton) {
            discountButton.click();
            this.announceToScreenReader('Discount modal opened');
        }
    }

    openSplitPaymentModal() {
        const splitPaymentButton = document.querySelector('button:contains("Split Payment"), button[onclick*="split"]');
        if (splitPaymentButton) {
            splitPaymentButton.click();
            this.announceToScreenReader('Split payment modal opened');
        }
    }

    addSelectedToCart() {
        // This would need to be implemented based on specific cart UI
        this.announceToScreenReader('Add to cart feature not implemented');
    }

    removeFromCart() {
        // This would need to be implemented based on specific cart UI
        this.announceToScreenReader('Remove from cart feature not implemented');
    }

    quickPayment(method) {
        // This would need to be implemented based on specific payment UI
        this.announceToScreenReader(`Quick ${method} payment feature not implemented`);
    }

    toggleAccessibilityMode() {
        document.body.classList.toggle('high-contrast');
        document.body.classList.toggle('large-text');
        this.announceToScreenReader('Accessibility mode toggled');
    }

    adjustFontSize(increase) {
        const currentSize = parseFloat(getComputedStyle(document.documentElement).fontSize);
        const newSize = increase ? currentSize + 2 : currentSize - 2;
        document.documentElement.style.fontSize = `${newSize}px`;
        this.announceToScreenReader(`Font size adjusted to ${newSize}px`);
    }

    resetFontSize() {
        document.documentElement.style.fontSize = '16px';
        this.announceToScreenReader('Font size reset to default');
    }

    navigateMenuItems(direction) {
        const menu = document.querySelector('[role="menu"]:focus-within, .dropdown:focus-within');
        if (menu) {
            const items = menu.querySelectorAll('[role="menuitem"], .dropdown-item');
            const currentIndex = Array.from(items).findIndex(item => item === document.activeElement);
            let nextIndex = currentIndex + direction;
            
            if (nextIndex < 0) nextIndex = items.length - 1;
            if (nextIndex >= items.length) nextIndex = 0;
            
            if (items[nextIndex]) {
                items[nextIndex].focus();
            }
        }
    }

    showModal(title, content) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('keyboard-help-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'keyboard-help-modal';
            modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
            modal.setAttribute('role', 'dialog');
            modal.setAttribute('aria-modal', 'true');
            modal.setAttribute('aria-labelledby', 'modal-title');
            
            modal.innerHTML = `
                <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                    <div class="p-6">
                        <div class="flex justify-between items-center mb-4">
                            <h2 id="modal-title" class="text-xl font-semibold">${title}</h2>
                            <button onclick="this.closest('.fixed').remove()" 
                                    class="text-gray-500 hover:text-gray-700"
                                    aria-label="Close modal">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                        <div id="modal-content">
                            ${content}
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
        } else {
            document.getElementById('modal-title').textContent = title;
            document.getElementById('modal-content').innerHTML = content;
            modal.classList.remove('hidden');
        }
        
        // Focus management
        const closeButton = modal.querySelector('button[onclick*="remove"]');
        if (closeButton) {
            closeButton.focus();
        }
        
        this.announceToScreenReader(`${title} modal opened`);
    }

    announceToScreenReader(message) {
        const announcement = document.getElementById('sr-announcements');
        if (announcement) {
            announcement.textContent = message;
            
            // Clear after announcement
            setTimeout(() => {
                announcement.textContent = '';
            }, 1000);
        }
    }
}

// Initialize keyboard navigation
const keyboardNav = new KeyboardNavigation();

// Make available globally
window.KeyboardNavigation = KeyboardNavigation;
window.keyboardNav = keyboardNav;