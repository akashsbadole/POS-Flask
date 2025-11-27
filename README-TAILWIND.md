# Restaurant POS System 🍽️

A comprehensive Restaurant Point of Sale (POS) system built with Flask, featuring offline capabilities, license management, and a modern food-themed interface with TailwindCSS.

## Features

### Core Functionality
- **Point of Sale**: Complete order management with payment processing 💰
- **Kitchen Display**: Real-time order tracking for kitchen staff 👨‍🍳
- **Table Management**: Visual table status and reservation system 🪑
- **Menu Management**: Dynamic menu categories and items with pricing 📖
- **Inventory Management**: Stock tracking and ingredient management 📦
- **Billing System**: Invoicing and payment processing 🧾
- **Reporting**: Comprehensive sales and performance reports 📊

### Advanced Features
- **Offline Functionality**: Works without internet connection, syncs when online 📱
- **License Management**: Commercial licensing with trial periods and activation 🔑
- **Error Management**: Comprehensive error logging and pattern detection 🚨
- **Support System**: Ticket-based customer support with email notifications 🎫
- **User Management**: Role-based access control (Admin, Manager, Cashier, Kitchen) 👥
- **GST Compliance**: Indian GST tax calculation and reporting 🇮🇳
- **Recipe Management**: Cost calculation and recipe tracking 📝
- **Multi-device Support**: Responsive design for tablets and mobile 📱

### Technical Features
- **HTMX Integration**: Dynamic content loading without page refreshes ⚡
- **Alpine.js**: Reactive frontend components 🔄
- **PWA Support**: Progressive Web App capabilities 📲
- **Service Worker**: Offline caching and background sync 🔄
- **Real-time Updates**: Live order and table status updates 🔄
- **Food-themed UI**: Beautiful restaurant-themed design with animations 🎨
- **TailwindCSS**: Modern utility-first CSS framework with food-themed customization 🎨

## Installation

### Prerequisites
- Python 3.8+
- Node.js 14+ (for TailwindCSS)
- npm or yarn

### Setup Instructions

1. Clone the repository
```bash
git clone <repository-url>
cd restaurant-pos
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies
```bash
pip install -r requirements.txt
```

4. Install Node.js dependencies and build CSS
```bash
# Using npm
npm install
npm run build-css

# Or use the build script
chmod +x build-css.sh  # On Unix systems
./build-css.sh
```

5. Initialize database
```bash
python init_db.py
```

6. Run the application
```bash
python run.py
```

The application will be available at `http://localhost:5000`

### Development Mode

For development with live CSS reloading:
```bash
npm run dev
```

This will start both the TailwindCSS watch process and the Flask development server concurrently.

### Production Build

For production deployment:
```bash
npm run build
```

This will create minified CSS files optimized for production.

## Configuration

### Environment Variables
Create a `.env` file with the following variables:

```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///restaurant_pos.db
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

### TailwindCSS Configuration
The application uses a customized TailwindCSS setup with food-themed design:

- **Config File**: `tailwind.config.js` - Custom food-themed colors and animations
- **Input CSS**: `app/static/css/input.css` - Base styles and component classes
- **Output CSS**: `app/static/css/tailwind.css` - Compiled styles
- **Build Script**: `build-css.sh` - Automated build process

### License Configuration
For commercial use, configure the license settings in the admin panel:
- Generate license keys for restaurant owners
- Set trial periods (default: 30 days)
- Configure license validation endpoints
- Monitor license usage and violations

### Offline Configuration
The application automatically configures offline capabilities:
- Service Worker registration
- IndexedDB for local storage
- Background sync for queued actions
- Cache management for menu items and tables

### Food Theme Customization
The food theme can be customized in `tailwind.config.js`:
- Food-themed color palette (orange, red, green, yellow)
- Custom animations (bounce, spin, float, steam)
- Restaurant-specific component styles
- Responsive design for mobile and tablet

## Usage

### User Roles
- **Admin**: Full system access, user management, system settings 👨‍💼
- **Manager**: Restaurant management, reports, inventory, menu management 📊
- **Cashier**: Point of sale, order management, payment processing 💰
- **Kitchen**: Kitchen display, order preparation, item management 👨‍🍳

### Daily Operations
1. **Opening**: Check inventory, update menu items, set table availability 🌅
2. **Service**: Take orders, process payments, manage kitchen workflow 🍽️
3. **Closing**: Generate reports, reconcile payments, backup data 🌙

### Offline Usage
- The application works seamlessly without internet connection 📱
- All data is stored locally and synced when connection is restored 🔄
- Critical features remain available (POS, kitchen display, table management) ✅

### Food-Themed Features
- **Animated Elements**: Food-themed animations and transitions 🎨
- **Color Scheme**: Restaurant-inspired orange and warm colors 🍊
- **Icons**: Food emojis and icons throughout the interface 🍕
- **Responsive Design**: Optimized for tablets and mobile devices 📱

## Architecture

### Backend
- **Flask**: Web framework with Blueprint architecture 🐍
- **SQLAlchemy**: ORM with SQLite database 🗄️
- **Werkzeug**: Security and utilities 🔐
- **Jinja2**: Template engine 📝

### Frontend
- **HTMX**: Dynamic content loading ⚡
- **Alpine.js**: Reactive components 🔄
- **TailwindCSS**: Utility-first CSS framework 🎨
- **Font Awesome**: Icon library (replaced with food emojis) 🎨

### Design System
- **Food Theme**: Custom color palette and animations 🍽️
- **Responsive Design**: Mobile-first approach 📱
- **Accessibility**: WCAG compliance with high contrast support ♿
- **Dark Mode**: Automatic dark mode support 🌙

### Offline Features
- **Service Worker**: PWA capabilities 📲
- **IndexedDB**: Client-side storage 💾
- **Background Sync**: Data synchronization 🔄

### Security
- **Flask-Login**: User authentication 🔐
- **Werkzeug Security**: Password hashing 🔒
- **CSRF Protection**: Cross-site request forgery prevention 🛡️
- **Role-based Access**: Permission system 👥

## Development

### CSS Development
To modify the food theme:
1. Edit `app/static/css/input.css` for base styles
2. Modify `tailwind.config.js` for theme customization
3. Run `npm run build-css` to compile changes
4. Use `npm run dev` for live reloading

### Adding New Components
1. Create component classes in `input.css` under `@layer components`
2. Use food-themed naming convention (`.btn-food`, `.restaurant-card`)
3. Test responsive behavior on different screen sizes
4. Ensure accessibility compliance

### Performance Optimization
- CSS is minified in production builds
- Critical CSS is inlined for faster loading
- Images are optimized for web delivery
- Service Worker caches static assets

## Contributing

1. Fork the repository 🍴
2. Create a feature branch 🌿
3. Make your changes with food theme in mind 🍽️
4. Add tests if applicable 🧪
5. Submit a pull request 📤

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository 🐛
- Use the in-app support system 🎫
- Contact the development team 📧

---

**Built with ❤️ and 🍽️ for the restaurant industry**