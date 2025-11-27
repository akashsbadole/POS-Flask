/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/static/js/**/*.js",
    "./app/static/css/**/*.css",
  ],
  theme: {
    extend: {
      colors: {
        // Food-themed color palette
        food: {
          primary: '#f97316',    // Orange
          secondary: '#ea580c',  // Dark Orange
          accent: '#fbbf24',     // Light Orange
          dark: '#7c2d12',       // Brown
          light: '#fef3c7',      // Cream
          tomato: '#ef4444',     // Red for tomatoes
          lettuce: '#22c55e',    // Green for lettuce
          cheese: '#f59e0b',     // Yellow for cheese
          bread: '#eab308',      // Golden for bread
        },
        // Restaurant-specific colors
        restaurant: {
          bg: '#fef2f2',
          card: '#ffffff',
          border: '#e5e7eb',
          text: '#111827',
          muted: '#6b7280',
        }
      },
      fontFamily: {
        'restaurant': ['Georgia', 'serif'],
        'modern': ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'food-bounce': 'food-bounce 1s infinite',
        'plate-spin': 'plate-spin 2s linear infinite',
        'ingredient-fall': 'ingredient-fall 0.5s ease-out',
        'steam-rise': 'steam-rise 2s ease-out infinite',
        'float': 'float 3s ease-in-out infinite',
        'pulse-slow': 'pulse 3s infinite',
      },
      keyframes: {
        'food-bounce': {
          '0%, 20%, 53%, 80%, 100%': { transform: 'translate3d(0, 0, 0)' },
          '40%, 43%': { transform: 'translate3d(0, -30px, 0)' },
          '70%': { transform: 'translate3d(0, -15px, 0)' },
          '90%': { transform: 'translate3d(0, -4px, 0)' },
        },
        'plate-spin': {
          '0%': { transform: 'rotate(0deg) scale(1)' },
          '50%': { transform: 'rotate(180deg) scale(1.1)' },
          '100%': { transform: 'rotate(360deg) scale(1)' },
        },
        'ingredient-fall': {
          '0%': { transform: 'translateY(-20px) rotate(0deg)', opacity: '0' },
          '50%': { transform: 'translateY(0) rotate(180deg)', opacity: '1' },
          '100%': { transform: 'translateY(0) rotate(360deg)', opacity: '1' },
        },
        'steam-rise': {
          '0%': { transform: 'translateY(0) scale(1)', opacity: '0.8' },
          '50%': { transform: 'translateY(-10px) scale(1.2)', opacity: '0.4' },
          '100%': { transform: 'translateY(-20px) scale(1.5)', opacity: '0' },
        },
        'float': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
      },
      backgroundImage: {
        'food-gradient': 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
        'food-gradient-light': 'linear-gradient(135deg, #fef3c7 0%, #fed7aa 100%)',
        'restaurant-bg': 'linear-gradient(135deg, #fef2f2 0%, #fef9e7 100%)',
      },
      boxShadow: {
        'food': '0 4px 6px -1px rgba(249, 115, 22, 0.1), 0 2px 4px -1px rgba(249, 115, 22, 0.06)',
        'food-lg': '0 10px 15px -3px rgba(249, 115, 22, 0.1), 0 4px 6px -2px rgba(249, 115, 22, 0.05)',
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
      borderRadius: {
        'food': '0.75rem',
        'food-lg': '1rem',
      },
      fontSize: {
        'food-xs': ['0.75rem', { lineHeight: '1rem' }],
        'food-sm': ['0.875rem', { lineHeight: '1.25rem' }],
        'food-base': ['1rem', { lineHeight: '1.5rem' }],
        'food-lg': ['1.125rem', { lineHeight: '1.75rem' }],
        'food-xl': ['1.25rem', { lineHeight: '1.75rem' }],
        'food-2xl': ['1.5rem', { lineHeight: '2rem' }],
        'food-3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        'food-4xl': ['2.25rem', { lineHeight: '2.5rem' }],
      },
      backdropBlur: {
        'food': '8px',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
    require('@tailwindcss/aspect-ratio'),
  ],
  darkMode: 'class',
  variants: {
    extend: {
      backgroundColor: ['dark', 'hover'],
      textColor: ['dark', 'hover'],
      borderColor: ['dark', 'hover'],
    },
  },
  prefix: '',
  important: false,
}