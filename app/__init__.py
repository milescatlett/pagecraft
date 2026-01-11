"""Flask application factory"""
import os
from flask import Flask, g, request
from app.config import config
from app.extensions import db, login_manager, csrf, limiter, talisman


def create_app(config_name=None):
    """Create and configure the Flask application"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Configure Talisman (security headers)
    # Disabled for local development, enable in production
    # talisman.init_app(app,
    #     content_security_policy={
    #         'default-src': "'self'",
    #         'script-src': ["'self'", 'cdn.jsdelivr.net'],
    #         'style-src': ["'self'", 'cdn.jsdelivr.net', "'unsafe-inline'"],
    #         'img-src': ["'self'", 'data:', 'https:'],
    #         'frame-src': ["'self'", 'https://*.caspio.com']
    #     },
    #     force_https=False
    # )

    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))

    # Register blueprints
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.users import bp as users_bp
    from app.blueprints.cms import bp as cms_bp
    from app.blueprints.public import bp as public_bp
    from app.blueprints.api import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(cms_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Before request hook for domain detection
    @app.before_request
    def detect_site_by_domain():
        """Detect which site to serve based on the Host header"""
        from app.services.site_service import SiteService
        host = request.host.lower()
        g.is_admin = SiteService.is_admin_domain(host)
        g.current_site = None

        if not g.is_admin:
            # This is a custom domain request - find the site
            g.current_site = SiteService.get_site_by_domain(host)

    # Create database tables and run migrations
    with app.app_context():
        _initialize_database(app)

    return app


def _initialize_database(app):
    """Initialize database and run migrations"""
    from sqlalchemy import inspect, text
    from app.models import User

    # Check if image tables need to be created
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    # Create all tables
    db.create_all()

    # Print message if new tables were created
    if 'images' not in existing_tables or 'image_folders' not in existing_tables:
        print("Created images and image_folders tables...")

    # Create uploads folder
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Run migrations
    columns = [col['name'] for col in inspector.get_columns('pages')]

    migrations = [
        ('parent_id', 'ALTER TABLE pages ADD COLUMN parent_id INTEGER REFERENCES pages(id)'),
        ('top_menu_id', 'ALTER TABLE pages ADD COLUMN top_menu_id INTEGER REFERENCES menus(id)'),
        ('left_menu_id', 'ALTER TABLE pages ADD COLUMN left_menu_id INTEGER REFERENCES menus(id)'),
        ('right_menu_id', 'ALTER TABLE pages ADD COLUMN right_menu_id INTEGER REFERENCES menus(id)'),
        ('footer_id', 'ALTER TABLE pages ADD COLUMN footer_id INTEGER REFERENCES footers(id)'),
        ('is_homepage', 'ALTER TABLE pages ADD COLUMN is_homepage BOOLEAN DEFAULT 0'),
    ]

    for col_name, sql in migrations:
        if col_name not in columns:
            with db.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()

    # Create default admin user if no users exist
    if User.query.count() == 0:
        admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
        admin = User(username=admin_username, is_admin=True)
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created admin user: {admin_username}")
        if admin_password == 'admin':
            print("WARNING: Using default password 'admin'. Set ADMIN_PASSWORD environment variable for security.")
