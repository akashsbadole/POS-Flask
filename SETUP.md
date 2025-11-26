# Restaurant POS System - Quick Setup Guide

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Git
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Automatic Setup (Recommended)

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd pos
   ```

2. **Run the setup script**
   ```bash
   python setup.py
   ```

3. **Activate virtual environment**
   
   **Windows:**
   ```bash
   venv\Scripts\activate
   ```
   
   **Mac/Linux:**
   ```bash
   source venv/bin/activate
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

5. **Open your browser**
   Navigate to http://localhost:5000

### Manual Setup

If the automatic setup doesn't work, follow these steps:

1. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment**
   
   **Windows:**
   ```bash
   venv\Scripts\activate
   ```
   
   **Mac/Linux:**
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file**
   Create a `.env` file with:
   ```
   FLASK_APP=run.py
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=sqlite:///pos.db
   ADMIN_EMAIL=admin@restaurant.com
   ADMIN_PASSWORD=admin123
   ```

5. **Initialize database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

## 🔑 Default Login Credentials

| Role | Email | Password | PIN |
|-------|--------|----------|-----|
| Admin | admin@restaurant.com | admin123 | 1234 |
| Manager | manager@restaurant.com | manager123 | 3333 |
| Cashier | cashier@restaurant.com | cashier123 | 1111 |
| Kitchen | kitchen@restaurant.com | kitchen123 | 2222 |

**⚠️ Important:** Change these passwords after first login!

## 🏗️ Project Structure

```
pos/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models/                   # Database models
│   │   ├── user.py              # User and role models
│   │   ├── menu.py              # Menu items and categories
│   │   ├── order.py             # Orders and payments
│   │   └── table.py             # Table management
│   ├── auth/                     # Authentication routes
│   ├── menu/                     # Menu management routes
│   ├── orders/                   # Order processing routes
│   ├── kitchen/                  # Kitchen display system
│   ├── tables/                   # Table management
│   ├── reports/                  # Reporting and analytics
│   ├── static/                   # Static assets
│   └── templates/                # Jinja2 templates
├── migrations/                   # Database migrations
├── config.py                     # Configuration settings
├── run.py                       # Application entry point
├── requirements.txt              # Python dependencies
├── setup.py                     # Setup script
├── init_db.py                   # Database initialization
└── README.md                    # Project documentation
```

## 🎯 Features Implemented

### ✅ Completed
- **Project Structure**: Complete Flask application structure with blueprints
- **Database Models**: User, Menu, Order, and Table models
- **Authentication**: Login/logout with role-based access
- **Base Templates**: Responsive base template with navigation
- **Login Page**: Modern login interface with PIN support
- **Cashier Dashboard**: Basic POS interface layout
- **Setup Scripts**: Automated setup and database initialization

### 🚧 In Progress
- **Menu Management**: CRUD operations for menu items
- **Order Processing**: Cart and checkout functionality
- **Kitchen Display**: Real-time order tracking

### ⏳ Planned
- **Table Management**: Visual floor plan
- **Reporting**: Sales analytics and reports
- **Receipt Printing**: Thermal printer integration
- **PWA**: Offline capabilities

## 🛠️ Development Commands

### Database Operations
```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Reset database (development only)
python init_db.py
```

### Create Sample Users
```bash
python init_db.py sample-users
```

### Running Tests
```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_auth.py
```

## 🔧 Configuration

### Environment Variables
- `FLASK_ENV`: Development/Production mode
- `SECRET_KEY`: Flask secret key (change in production)
- `DATABASE_URL`: Database connection string
- `ADMIN_EMAIL`: Default admin email
- `ADMIN_PASSWORD`: Default admin password

### Database Configuration
- **Development**: SQLite (default)
- **Production**: PostgreSQL recommended

### Printer Configuration
Set `PRINTER_DEVICE` in `.env` for thermal printer:
```
PRINTER_DEVICE=/dev/usb/lp0  # Linux
PRINTER_DEVICE=COM1           # Windows
```

## 🌐 Access URLs

After running the application:

- **Main Application**: http://localhost:5000
- **Login**: http://localhost:5000/auth/login
- **Admin Dashboard**: http://localhost:5000/manager/dashboard
- **Kitchen Display**: http://localhost:5000/kitchen/display
- **Cashier POS**: http://localhost:5000/cashier/dashboard

## 📱 Browser Support

- ✅ Chrome 80+
- ✅ Firefox 75+
- ✅ Safari 13+
- ✅ Edge 80+

## 🔒 Security Notes

1. **Change Default Passwords**: Always change default credentials
2. **Use HTTPS**: Enable SSL in production
3. **Session Timeout**: Auto-logout after 15 minutes
4. **PIN Security**: Use 4-digit PINs for quick access
5. **Regular Updates**: Keep dependencies updated

## 🐛 Troubleshooting

### Common Issues

**Port 5000 already in use:**
```bash
# Kill existing process (Windows)
taskkill /F /IM python.exe

# Kill existing process (Mac/Linux)
sudo lsof -ti:5000 | xargs kill -9
```

**Database errors:**
```bash
# Reinitialize database
rm pos.db
python init_db.py
```

**Module not found:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Permission errors:**
```bash
# Use virtual environment
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate         # Windows
```

### Getting Help

1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure virtual environment is activated
4. Check database file permissions
5. Review configuration settings

## 📈 Next Steps

1. **Explore the System**: Log in with different roles
2. **Add Menu Items**: Use manager account to add menu items
3. **Test Orders**: Create test orders with cashier account
4. **Check Kitchen**: View orders in kitchen display
5. **Customize**: Modify colors, layout, and features
6. **Deploy**: Set up production environment

## 📚 Documentation

- [README.md](README.md) - Project overview
- [architecture.md](architecture.md) - System architecture
- [implementation_guide.md](implementation_guide.md) - Technical details
- [development_roadmap.md](development_roadmap.md) - Development plan
- [features.md](features.md) - Complete feature list

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🎉 Thank you for using Restaurant POS System!**

For support and updates, please visit our GitHub repository.