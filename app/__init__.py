from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from config import config
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
socketio = SocketIO()
csrf = CSRFProtect()
mail = Mail()

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG') or 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app, cors_allowed_origins="*", async_mode=app.config['SOCKETIO_ASYNC_MODE'])
    csrf.init_app(app)
    mail.init_app(app)
    
    # Initialize notification service
    from app.notifications.service import notification_service
    notification_service.init_app(app)
    
    # Enable WAL mode for SQLite
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        from sqlalchemy import event
        with app.app_context():
            @event.listens_for(db.engine, 'connect')
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.close()
    
    # Configure login manager
    login_manager.login_view = 'auth.login'  # type: ignore
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from app.auth import bp as auth_bp
    # Disable CSRF protection for auth blueprint to allow HTMX requests
    csrf.exempt(auth_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.menu import bp as menu_bp
    app.register_blueprint(menu_bp, url_prefix='/menu')
    
    from app.orders import bp as orders_bp
    app.register_blueprint(orders_bp, url_prefix='/orders')
    
    from app.kitchen import bp as kitchen_bp
    app.register_blueprint(kitchen_bp, url_prefix='/kitchen')
    
    from app.tables import bp as tables_bp
    app.register_blueprint(tables_bp, url_prefix='/tables')
    
    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')
    
    from app.api import bp as api_bp
    from app.api.offline import bp as offline_bp
    # Disable CSRF protection for API blueprint to allow HTMX requests
    csrf.exempt(api_bp)
    csrf.exempt(offline_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(offline_bp, url_prefix='/api/offline')
    
    from app.inventory import bp as inventory_bp
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    
    from app.recipes import bp as recipes_bp
    app.register_blueprint(recipes_bp, url_prefix='/recipes')
    
    from app.billing import bp as billing_bp
    app.register_blueprint(billing_bp, url_prefix='/billing')
    
    from app.billing.credit_routes import credit_bp
    app.register_blueprint(credit_bp)
    
    from app.subscription import bp as subscription_bp
    app.register_blueprint(subscription_bp, url_prefix='/subscription')
    
    from app.license import bp as license_bp
    app.register_blueprint(license_bp, url_prefix='/license')
    
    from app.error import bp as error_bp
    app.register_blueprint(error_bp, url_prefix='/error')
    
    from app.support import bp as support_bp
    app.register_blueprint(support_bp, url_prefix='/support')
    
    from app.purchase import bp as purchase_bp
    app.register_blueprint(purchase_bp, url_prefix='/purchase')
    
    from app.notifications import bp as notifications_bp
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    
    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    from app.hardware import bp as hardware_bp
    app.register_blueprint(hardware_bp, url_prefix='/hardware')
    
    from app.customers import bp as customers_bp
    app.register_blueprint(customers_bp, url_prefix='/customers')
    
    from app.online_ordering import bp as online_ordering_bp
    app.register_blueprint(online_ordering_bp, url_prefix='/online-ordering')
    
    from app.delivery import bp as delivery_bp
    app.register_blueprint(delivery_bp, url_prefix='/delivery')
    
    from app.analytics import bp as analytics_bp
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    
    from app.payment import bp as payment_bp
    app.register_blueprint(payment_bp, url_prefix='/payment')
    
    from app.settings import bp as settings_bp
    app.register_blueprint(settings_bp, url_prefix='/settings')
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Context processors
    @app.context_processor
    def inject_config():
        return dict(
            currency_symbol=app.config['CURRENCY_SYMBOL'],
            tax_rate=app.config['DEFAULT_TAX_RATE']
        )
    
    # Make CSRF token available to all templates
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        # Log the error
        import traceback
        app.logger.error(f"Internal Server Error: {error}\n{traceback.format_exc()}")
        
        # Generate error ID for tracking
        import uuid
        error_id = str(uuid.uuid4())[:8]
        
        return render_template('errors/500.html', error_id=error_id), 500
    
    # Import and register Socket.IO event handlers
    from app import socketio_events
    
    return app