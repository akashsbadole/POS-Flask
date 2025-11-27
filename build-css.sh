#!/bin/bash

# Build TailwindCSS for Restaurant POS System
echo "🍽️ Building TailwindCSS for Restaurant POS System..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build CSS for development
echo "🎨 Building CSS for development..."
npm run build-css

echo "✅ TailwindCSS build completed!"
echo "🔥 Your food-themed styles are ready to serve!"