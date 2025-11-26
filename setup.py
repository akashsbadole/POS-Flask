#!/usr/bin/env python3
"""
Setup script for Restaurant POS System
Installs dependencies and initializes the database
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(e.stderr)
        return False

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version {sys.version.split()[0]} is compatible")
    return True

def create_virtual_env():
    """Create virtual environment if it doesn't exist"""
    if not os.path.exists('venv'):
        print("Creating virtual environment...")
        return run_command(f"{sys.executable} -m venv venv", "Creating virtual environment")
    else:
        print("✅ Virtual environment already exists")
        return True

def activate_venv_and_install():
    """Activate virtual environment and install dependencies"""
    if os.name == 'nt':  # Windows
        pip_command = "venv\\Scripts\\pip"
        python_command = "venv\\Scripts\\python"
    else:  # Unix/Mac
        pip_command = "venv/bin/pip"
        python_command = "venv/bin/python"
    
    # Install dependencies
    success = run_command(f"{pip_command} install -r requirements.txt", "Installing dependencies")
    
    if success:
        # Initialize database
        return run_command(f"{python_command} init_db.py", "Initializing database")
    
    return False

def create_env_file():
    """Create .env file with default configuration"""
    if not os.path.exists('.env'):
        print("Creating .env file with default configuration...")
        env_content = """# Restaurant POS System Environment Configuration

# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-change-in-production

# Database Configuration
DATABASE_URL=sqlite:///pos.db

# Admin User Configuration
ADMIN_EMAIL=admin@restaurant.com
ADMIN_PASSWORD=admin123

# Optional: Printer Configuration
# PRINTER_DEVICE=/dev/usb/lp0
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ .env file created with default configuration")
        print("🔒 Please update the SECRET_KEY before production use")
    else:
        print("✅ .env file already exists")

def main():
    """Main setup function"""
    print("🍽 Restaurant POS System Setup")
    print("=" * 40)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Create virtual environment
    if not create_virtual_env():
        return False
    
    # Install dependencies and initialize database
    if not activate_venv_and_install():
        return False
    
    # Create environment file
    create_env_file()
    
    print("\n" + "=" * 40)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Activate virtual environment:")
    
    if os.name == 'nt':  # Windows
        print("   venv\\Scripts\\activate")
    else:  # Unix/Mac
        print("   source venv/bin/activate")
    
    print("2. Run the application:")
    print("   python run.py")
    print("\n3. Open your browser and go to:")
    print("   http://localhost:5000")
    print("\nDefault login credentials:")
    print("   Email: admin@restaurant.com")
    print("   Password: admin123")
    print("   PIN: 1234")
    print("\n🔒 Please change default passwords after first login!")
    
    return True

if __name__ == '__main__':
    main()