import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///pos.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # Remember me lasts 7 days
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_PERMANENT = True
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Tax configuration (default 8.75%)
    DEFAULT_TAX_RATE = 0.0875
    
    # Currency
    CURRENCY_SYMBOL = '$'
    
    # Receipt printer configuration
    PRINTER_DEVICE = os.environ.get('PRINTER_DEVICE') or None
    
    # WebSocket configuration
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@restaurant.com'
    MAIL_MAX_EMAILS = int(os.environ.get('MAIL_MAX_EMAILS') or 10)
    MAIL_SUPPRESS_SEND = os.environ.get('MAIL_SUPPRESS_SEND', 'false').lower() in ['true', 'on', '1']
    
    # Email provider presets
    EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER') or 'gmail'  # gmail, outlook, custom
    
    # SMS configuration
    SMS_PROVIDER = os.environ.get('SMS_PROVIDER') or 'twilio'  # twilio, aws_sns, custom
    SMS_ACCOUNT_SID = os.environ.get('SMS_ACCOUNT_SID')
    SMS_AUTH_TOKEN = os.environ.get('SMS_AUTH_TOKEN')
    SMS_FROM_NUMBER = os.environ.get('SMS_FROM_NUMBER')
    SMS_AWS_ACCESS_KEY = os.environ.get('SMS_AWS_ACCESS_KEY')
    SMS_AWS_SECRET_KEY = os.environ.get('SMS_AWS_SECRET_KEY')
    SMS_AWS_REGION = os.environ.get('SMS_AWS_REGION') or 'us-east-1'
    
    # Notification settings
    ENABLE_EMAIL_NOTIFICATIONS = os.environ.get('ENABLE_EMAIL_NOTIFICATIONS', 'true').lower() in ['true', 'on', '1']
    ENABLE_SMS_NOTIFICATIONS = os.environ.get('ENABLE_SMS_NOTIFICATIONS', 'false').lower() in ['true', 'on', '1']
    NOTIFICATION_QUEUE_ENABLED = os.environ.get('NOTIFICATION_QUEUE_ENABLED', 'true').lower() in ['true', 'on', '1']
    NOTIFICATION_RETRY_ATTEMPTS = int(os.environ.get('NOTIFICATION_RETRY_ATTEMPTS') or 3)
    NOTIFICATION_RETRY_DELAY = int(os.environ.get('NOTIFICATION_RETRY_DELAY') or 60)  # seconds

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///pos_dev.db'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///pos.db'

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}