/**
 * Theme Manager for Restaurant POS
 * Handles food-related themes and beautiful design switching
 */

class ThemeManager {
    constructor() {
        this.themes = {
            classic: {
                name: 'Classic Restaurant',
                primary: '#dc2626',
                secondary: '#059669',
                accent: '#16a34a',
                background: '#ffffff',
                text: '#111827',
                description: 'Traditional restaurant theme with warm colors',
                foodColors: {
                    tomato: '#ef4444',
                    lettuce: '#22c55e',
                    cheese: '#f59e0b',
                    bread: '#fbbf24'
                }
            },
            modern: {
                name: 'Modern Bistro',
                primary: '#3b82f6',
                secondary: '#1e40af',
                accent: '#10b981',
                background: '#f9fafb',
                text: '#1f2937',
                description: 'Clean modern design with blue accents',
                foodColors: {
                    tomato: '#3b82f6',
                    lettuce: '#06b6d4',
                    cheese: '#f59e0b',
                    bread: '#eab308'
                }
            },
            organic: {
                name: 'Organic Kitchen',
                primary: '#059669',
                secondary: '#047857',
                accent: '#10b981',
                background: '#f0fdf4',
                text: '#064e3b',
                description: 'Fresh organic theme with green colors',
                foodColors: {
                    tomato: '#16a34a',
                    lettuce: '#059669',
                    cheese: '#84cc16',
                    bread: '#65a30d'
                }
            },
            sunset: {
                name: 'Sunset Dining',
                primary: '#f97316',
                secondary: '#ea580c',
                accent: '#fbbf24',
                background: '#fffbeb',
                text: '#7c2d12',
                description: 'Warm sunset theme with orange tones',
                foodColors: {
                    tomato: '#f97316',
                    lettuce: '#fb923c',
                    cheese: '#fed7aa',
                    bread: '#fbbf24'
                }
            },
            midnight: {
                name: 'Midnight Service',
                primary: '#1e293b',
                secondary: '#312e81',
                accent: '#4f46e5',
                background: '#111827',
                text: '#f9fafb',
                description: 'Dark theme for night service',
                foodColors: {
                    tomato: '#dc2626',
                    lettuce: '#059669',
                    cheese: '#fbbf24',
                    bread: '#f59e0b'
                }
            },
            mediterranean: {
                name: 'Mediterranean Cuisine',
                primary: '#0891b2',
                secondary: '#0e7490',
                accent: '#06b6d4',
                background: '#f0f9ff',
                text: '#0c4a6e',
                description: 'Fresh Mediterranean theme with sea blue colors',
                foodColors: {
                    tomato: '#dc2626',
                    lettuce: '#16a34a',
                    cheese: '#f59e0b',
                    bread: '#eab308'
                }
            },
            asian: {
                name: 'Asian Fusion',
                primary: '#dc2626',
                secondary: '#991b1b',
                accent: '#f59e0b',
                background: '#fef2f2',
                text: '#7f1d1d',
                description: 'Vibrant Asian theme with red and gold accents',
                foodColors: {
                    tomato: '#dc2626',
                    lettuce: '#16a34a',
                    cheese: '#fbbf24',
                    bread: '#f59e0b'
                }
            }
        };
        
        this.currentTheme = 'classic';
        this.init();
    }

    init() {
        // Load saved theme or default
        const savedTheme = localStorage.getItem('restaurant-theme') || 'classic';
        this.setTheme(savedTheme);
        
        // Listen for system theme changes
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            darkModeQuery.addListener((e) => {
                if (e.matches) {
                    this.setTheme('midnight');
                } else {
                    this.setTheme(this.currentTheme);
                }
            });
        }
    }

    setTheme(themeName) {
        const theme = this.themes[themeName];
        if (!theme) return;

        this.currentTheme = themeName;
        
        // Apply theme colors
        this.applyThemeColors(theme, themeName);
        
        // Save preference
        localStorage.setItem('restaurant-theme', themeName);
        
        // Update theme selector
        this.updateThemeSelector();
        
        // Dispatch theme change event
        window.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName, colors: theme }
        }));
    }

    applyThemeColors(theme, themeName) {
        const root = document.documentElement;
        
        // Set CSS custom properties
        root.style.setProperty('--primary-color', theme.primary);
        root.style.setProperty('--secondary-color', theme.secondary);
        root.style.setProperty('--accent-color', theme.accent);
        root.style.setProperty('--bg-primary', theme.background);
        root.style.setProperty('--text-primary', theme.text);
        
        // Apply food theme colors
        if (theme.foodColors) {
            root.style.setProperty('--food-tomato', theme.foodColors.tomato);
            root.style.setProperty('--food-lettuce', theme.foodColors.lettuce);
            root.style.setProperty('--food-cheese', theme.foodColors.cheese);
            root.style.setProperty('--food-bread', theme.foodColors.bread);
        }
        
        // Update body class for theme-specific styling
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        document.body.classList.add(`theme-${themeName}`);
        
        // Add food-themed animations
        this.applyFoodAnimations();
        
        // Update meta theme-color
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.content = theme.primary;
        }
    }

    updateThemeSelector() {
        const selector = document.getElementById('theme-selector');
        if (!selector) return;

        selector.innerHTML = this.getThemeOptions();
        selector.value = this.currentTheme;
    }

    getThemeOptions() {
        return Object.keys(this.themes).map(themeName => {
            const theme = this.themes[themeName];
            const selected = themeName === this.currentTheme ? 'selected' : '';
            return `
                <option value="${themeName}" ${selected}>
                    ${theme.name}
                </option>
            `;
        }).join('');
    }

    getCurrentTheme() {
        return this.themes[this.currentTheme];
    }

    // Auto theme based on time of day
    setAutoTheme() {
        const hour = new Date().getHours();
        let themeName;
        
        if (hour >= 6 && hour < 12) {
            themeName = 'organic'; // Morning - fresh
        } else if (hour >= 12 && hour < 17) {
            themeName = 'modern'; // Afternoon - professional
        } else if (hour >= 17 && hour < 21) {
            themeName = 'sunset'; // Evening - warm
        } else {
            themeName = 'midnight'; // Night - dark
        }
        
        this.setTheme(themeName);
    }

    // Toggle between light and dark versions of current theme
    toggleDarkMode() {
        const currentTheme = this.getCurrentTheme();
        const isDark = document.body.classList.contains('dark-mode');
        
        if (isDark) {
            // Switch to light version
            document.body.classList.remove('dark-mode');
            this.applyThemeColors(currentTheme, this.currentTheme);
        } else {
            // Switch to dark version
            document.body.classList.add('dark-mode');
            const darkTheme = this.getDarkVersion(this.currentTheme);
            this.applyThemeColors(darkTheme, this.currentTheme);
        }
    }

    getDarkVersion(themeName) {
        const darkThemes = {
            classic: 'midnight',
            modern: 'midnight',
            organic: 'midnight',
            sunset: 'midnight',
            midnight: 'classic' // Light version of midnight
        };
        
        return this.themes[darkThemes[themeName]] || this.themes[themeName];
    }

    // Apply food-specific animations
    applyFoodAnimations() {
        const foodItems = document.querySelectorAll('.menu-item-card, .order-item, .table-card');
        
        foodItems.forEach((item, index) => {
            // Add staggered entrance animation
            item.style.animation = `fadeIn 0.5s ease-out ${index * 0.1}s both`;
            
            // Add hover effects for food items
            if (item.classList.contains('menu-item-card')) {
                item.addEventListener('mouseenter', () => {
                    item.style.transform = 'translateY(-4px) scale(1.02)';
                    item.style.boxShadow = '0 8px 16px rgba(0,0,0,0.15)';
                });
                
                item.addEventListener('mouseleave', () => {
                    item.style.transform = 'translateY(0) scale(1)';
                    item.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
                });
            }
        });
        
        // Add food-themed loading animations
        this.addFoodLoadingAnimations();
        
        // Add plate spinning for loading states
        this.addPlateSpinner();
    }
    
    addFoodLoadingAnimations() {
        // Create custom food-themed loading animations
        const style = document.createElement('style');
        style.textContent = `
            @keyframes food-bounce {
                0%, 20%, 53%, 80%, 100% { transform: translate3d(0, 0, 0); }
                40%, 43% { transform: translate3d(0, -30px, 0); }
                70% { transform: translate3d(0, -15px, 0); }
                90% { transform: translate3d(0, -4px, 0); }
            }
            
            @keyframes plate-spin {
                0% { transform: rotate(0deg) scale(1); }
                50% { transform: rotate(180deg) scale(1.1); }
                100% { transform: rotate(360deg) scale(1); }
            }
            
            @keyframes ingredient-fall {
                0% { transform: translateY(-20px) rotate(0deg); opacity: 0; }
                50% { transform: translateY(0) rotate(180deg); opacity: 1; }
                100% { transform: translateY(0) rotate(360deg); opacity: 1; }
            }
            
            .food-bounce { animation: food-bounce 1s infinite; }
            .plate-spin { animation: plate-spin 2s linear infinite; }
            .ingredient-fall { animation: ingredient-fall 0.5s ease-out; }
        `;
        document.head.appendChild(style);
    }
    
    addPlateSpinner() {
        // Replace loading spinners with food-themed plate spinner
        const spinners = document.querySelectorAll('.spinner');
        spinners.forEach(spinner => {
            spinner.classList.add('plate-spinner');
            spinner.innerHTML = `
                <div class="plate-spinner-inner">
                    <div class="plate"></div>
                    <div class="food-item"></div>
                </div>
            `;
        });
    }

    // Apply restaurant-specific styling
    applyRestaurantStyling() {
        // Add food-themed gradients
        const cards = document.querySelectorAll('.restaurant-card, .menu-item-card');
        cards.forEach(card => {
            card.classList.add('food-gradient');
        });
        
        // Add custom scrollbars
        const scrollableElements = document.querySelectorAll('.menu-grid, .order-list, .table-grid');
        scrollableElements.forEach(element => {
            element.classList.add('food-scrollbar');
        });
        
        // Add plate spinner for loading
        const spinners = document.querySelectorAll('.spinner');
        spinners.forEach(spinner => {
            spinner.classList.add('plate-spinner');
        });
    }

    // Initialize theme-specific features
    initThemeFeatures() {
        this.applyFoodAnimations();
        this.applyRestaurantStyling();
        
        // Add theme toggle button if not exists
        if (!document.getElementById('theme-toggle')) {
            const toggleButton = document.createElement('button');
            toggleButton.id = 'theme-toggle';
            toggleButton.className = 'fixed top-4 right-4 z-50 p-2 bg-white rounded-full shadow-lg transition-all duration-200 hover:scale-110';
            toggleButton.innerHTML = `
                <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 3v1m0 8v1m0 8v1m0 8v1m0 8v1M3 21h18M3 12h18m-9 4h.01M3 16h18M3 20h18"/>
                </svg>
            `;
            toggleButton.addEventListener('click', () => this.toggleDarkMode());
            document.body.appendChild(toggleButton);
        }
    }
}

// Initialize theme manager
window.ThemeManager = ThemeManager;

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.themeManager = new ThemeManager();
        window.themeManager.initThemeFeatures();
    });
} else {
    window.themeManager = new ThemeManager();
    window.themeManager.initThemeFeatures();
}