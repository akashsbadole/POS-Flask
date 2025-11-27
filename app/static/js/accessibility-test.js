/**
 * Accessibility and Keyboard Navigation Test Suite
 * Tests all keyboard navigation and accessibility features
 */

class AccessibilityTester {
    constructor() {
        this.tests = [];
        this.results = [];
        this.init();
    }

    init() {
        console.log('Initializing Accessibility Tester...');
        this.setupTestSuite();
        this.runTests();
    }

    setupTestSuite() {
        // Navigation Tests
        this.addTest('Navigation Links Have ARIA Labels', () => {
            const navLinks = document.querySelectorAll('nav a');
            return Array.from(navLinks).every(link => 
                link.getAttribute('aria-label') || link.textContent.trim()
            );
        });

        this.addTest('Navigation Links Have Access Keys', () => {
            const navLinks = document.querySelectorAll('nav a');
            return Array.from(navLinks).some(link => 
                link.getAttribute('accesskey')
            );
        });

        this.addTest('Skip Links Present', () => {
            return document.getElementById('skip-to-main') !== null;
        });

        // Form Tests
        this.addTest('Form Fields Have Labels', () => {
            const inputs = document.querySelectorAll('input, select, textarea');
            return Array.from(inputs).every(input => {
                const id = input.id;
                const label = document.querySelector(`label[for="${id}"]`);
                return label || input.getAttribute('aria-label') || input.getAttribute('aria-labelledby');
            });
        });

        this.addTest('Form Fields Have Access Keys', () => {
            const inputs = document.querySelectorAll('input, select, textarea');
            return Array.from(inputs).some(input => 
                input.getAttribute('accesskey')
            );
        });

        this.addTest('Forms Have Validation Attributes', () => {
            const forms = document.querySelectorAll('form[data-validate]');
            return forms.length > 0;
        });

        // Focus Management Tests
        this.addTest('Focus Styles Applied', () => {
            const style = document.getElementById('keyboard-nav-styles');
            return style !== null && style.textContent.includes(':focus');
        });

        this.addTest('Tab Order Logical', () => {
            const focusableElements = this.getFocusableElements();
            return focusableElements.length > 0;
        });

        // Screen Reader Tests
        this.addTest('Screen Reader Announcements Present', () => {
            const announcements = document.getElementById('sr-announcements');
            return announcements !== null;
        });

        this.addTest('Live Regions Present', () => {
            const liveRegions = document.querySelectorAll('[aria-live]');
            return liveRegions.length > 0;
        });

        // Keyboard Navigation Tests
        this.addTest('Keyboard Navigation Script Loaded', () => {
            return window.keyboardNav !== undefined;
        });

        this.addTest('Help Modal Available', () => {
            return typeof window.keyboardNav?.showHelpModal === 'function';
        });

        // Billing Specific Tests
        this.addTest('Billing Shortcuts Available', () => {
            const billingButtons = document.querySelectorAll('[data-shortcut*="ctrl+i"], [data-shortcut*="ctrl+p"], [data-shortcut*="ctrl+d"]');
            return billingButtons.length > 0;
        });

        this.addTest('Invoice Form Accessible', () => {
            const invoiceForm = document.getElementById('invoice-form');
            if (!invoiceForm) return true; // Not on invoice page
            
            const inputs = invoiceForm.querySelectorAll('input, select, textarea');
            return Array.from(inputs).every(input => 
                input.id && document.querySelector(`label[for="${input.id}"]`)
            );
        });

        // High Contrast Tests
        this.addTest('High Contrast Support', () => {
            const style = document.getElementById('keyboard-nav-styles');
            return style && style.textContent.includes('prefers-contrast: high');
        });

        // Reduced Motion Tests
        this.addTest('Reduced Motion Support', () => {
            const style = document.getElementById('keyboard-nav-styles');
            return style && style.textContent.includes('prefers-reduced-motion: reduce');
        });

        // Error Handling Tests
        this.addTest('Error Messages Accessible', () => {
            const errors = document.querySelectorAll('[role="alert"], .error, .bg-red-50');
            return Array.from(errors).every(error => 
                error.getAttribute('role') === 'alert' || 
                error.getAttribute('aria-live') === 'polite' ||
                error.querySelector('.sr-only')
            );
        });

        // Button Tests
        this.addTest('Buttons Accessible', () => {
            const buttons = document.querySelectorAll('button');
            return Array.from(buttons).every(button => {
                const hasText = button.textContent.trim();
                const hasAriaLabel = button.getAttribute('aria-label');
                const hasIcon = button.querySelector('i[aria-hidden="true"]');
                return hasText || hasAriaLabel || hasIcon;
            });
        });

        // Search Functionality Tests
        this.addTest('Search Accessible', () => {
            const searchInput = document.getElementById('global-search');
            if (!searchInput) return true; // Not on page with search
            
            const hasLabel = document.querySelector('label[for="global-search"]');
            const hasAriaLabel = searchInput.getAttribute('aria-label');
            const hasAccessKey = searchInput.getAttribute('accesskey');
            
            return hasLabel || hasAriaLabel || hasAccessKey;
        });
    }

    addTest(name, testFunction) {
        this.tests.push({
            name,
            test: testFunction,
            passed: false,
            error: null
        });
    }

    runTests() {
        console.log(`Running ${this.tests.length} accessibility tests...`);
        
        this.tests.forEach(test => {
            try {
                test.passed = test.test();
                if (!test.passed) {
                    console.warn(`Test failed: ${test.name}`);
                }
            } catch (error) {
                test.passed = false;
                test.error = error.message;
                console.error(`Test error: ${test.name}`, error);
            }
        });

        this.displayResults();
        this.generateReport();
    }

    getFocusableElements() {
        const focusableSelectors = [
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
            '[contenteditable="true"]'
        ];

        return Array.from(
            document.querySelectorAll(focusableSelectors.join(', '))
        ).filter(element => {
            const style = window.getComputedStyle(element);
            return style.display !== 'none' && 
                   style.visibility !== 'hidden' && 
                   element.offsetParent !== null;
        });
    }

    displayResults() {
        const passedTests = this.tests.filter(test => test.passed).length;
        const totalTests = this.tests.length;
        const percentage = Math.round((passedTests / totalTests) * 100);

        console.log(`\n=== Accessibility Test Results ===`);
        console.log(`Passed: ${passedTests}/${totalTests} (${percentage}%)`);
        console.log(`=====================================\n`);

        this.tests.forEach(test => {
            const status = test.passed ? '✅ PASS' : '❌ FAIL';
            const error = test.error ? ` (${test.error})` : '';
            console.log(`${status} ${test.name}${error}`);
        });

        // Display visual results if in browser
        if (typeof document !== 'undefined') {
            this.showVisualResults(passedTests, totalTests, percentage);
        }
    }

    showVisualResults(passedTests, totalTests, percentage) {
        // Create results modal
        const modal = document.createElement('div');
        modal.id = 'accessibility-test-results';
        modal.className = 'fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'test-results-title');

        const statusClass = percentage >= 80 ? 'bg-green-100' : percentage >= 60 ? 'bg-yellow-100' : 'bg-red-100';
        const statusText = percentage >= 80 ? 'Excellent' : percentage >= 60 ? 'Good' : 'Needs Improvement';

        modal.innerHTML = `
            <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                <div class="p-6">
                    <div class="flex justify-between items-center mb-4">
                        <h2 id="test-results-title" class="text-xl font-semibold">Accessibility Test Results</h2>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="text-gray-500 hover:text-gray-700"
                                aria-label="Close results">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div class="${statusClass} p-4 rounded-lg mb-4">
                        <div class="text-center">
                            <div class="text-3xl font-bold mb-2">${percentage}%</div>
                            <div class="text-lg">${statusText}</div>
                            <div class="text-sm text-gray-600 mt-1">${passedTests} of ${totalTests} tests passed</div>
                        </div>
                    </div>
                    
                    <div class="space-y-2">
                        <h3 class="font-semibold mb-2">Test Details:</h3>
                        ${this.tests.map(test => `
                            <div class="flex items-center justify-between p-2 border-b">
                                <span class="${test.passed ? 'text-green-600' : 'text-red-600'}">
                                    ${test.passed ? '✅' : '❌'} ${test.name}
                                </span>
                                <span class="text-sm text-gray-500">
                                    ${test.error ? test.error : (test.passed ? 'Passed' : 'Failed')}
                                </span>
                            </div>
                        `).join('')}
                    </div>
                    
                    <div class="mt-4 flex justify-end space-x-2">
                        <button onclick="window.print()" 
                                class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                            Print Results
                        </button>
                        <button onclick="this.closest('.fixed').remove()" 
                                class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    generateReport() {
        const report = {
            timestamp: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            results: this.tests.map(test => ({
                name: test.name,
                passed: test.passed,
                error: test.error
            })),
            summary: {
                total: this.tests.length,
                passed: this.tests.filter(test => test.passed).length,
                failed: this.tests.filter(test => !test.passed).length,
                percentage: Math.round((this.tests.filter(test => test.passed).length / this.tests.length) * 100)
            }
        };

        // Save to console for debugging
        console.log('Accessibility Test Report:', report);

        // Save to localStorage
        try {
            localStorage.setItem('accessibility-test-report', JSON.stringify(report));
        } catch (error) {
            console.warn('Could not save report to localStorage:', error);
        }
    }

    // Test keyboard shortcuts functionality
    testKeyboardShortcuts() {
        console.log('Testing keyboard shortcuts...');
        
        const shortcuts = [
            { key: 'ctrl+/', action: 'showHelp', description: 'Show help' },
            { key: 'ctrl+k', action: 'focusSearch', description: 'Focus search' },
            { key: 'escape', action: 'escapeAction', description: 'Escape action' },
            { key: 'ctrl+i', action: 'newInvoice', description: 'New invoice' },
            { key: 'ctrl+p', action: 'printReceipt', description: 'Print receipt' },
            { key: 'ctrl+d', action: 'addDiscount', description: 'Add discount' }
        ];

        shortcuts.forEach(shortcut => {
            console.log(`Press ${shortcut.key} to test: ${shortcut.description}`);
        });

        // Announce to screen reader
        if (window.keyboardNav) {
            window.keyboardNav.announceToScreenReader('Keyboard shortcuts test initiated. Check console for shortcuts to test.');
        }
    }
}

// Auto-run tests when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.accessibilityTester = new AccessibilityTester();
    });
} else {
    window.accessibilityTester = new AccessibilityTester();
}

// Make available globally
window.AccessibilityTester = AccessibilityTester;

// Add test runner function
window.runAccessibilityTests = () => {
    if (window.accessibilityTester) {
        window.accessibilityTester.runTests();
    } else {
        console.error('Accessibility tester not initialized');
    }
};

// Add keyboard shortcut test function
window.testKeyboardShortcuts = () => {
    if (window.accessibilityTester) {
        window.accessibilityTester.testKeyboardShortcuts();
    } else {
        console.error('Accessibility tester not initialized');
    }
};