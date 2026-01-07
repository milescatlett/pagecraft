from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, g, abort, flash
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import json
import os
import uuid

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cms.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

# Admin domains - requests from these domains will show the CMS admin interface
# All other domains will be checked against site.domain for public site serving
ADMIN_DOMAINS = ['localhost', '127.0.0.1', 'localhost:5000', '127.0.0.1:5000']

from database import db
db.init_app(app)

# Import models after db initialization
from models import Site, Page, Menu, MenuItem, Footer, Widget, User
from caspio import caspio_api

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables and uploads folder
with app.app_context():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Migration: Add columns to pages table if they don't exist
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    columns = [col['name'] for col in inspector.get_columns('pages')]

    migrations = [
        ('parent_id', 'ALTER TABLE pages ADD COLUMN parent_id INTEGER REFERENCES pages(id)'),
        ('top_menu_id', 'ALTER TABLE pages ADD COLUMN top_menu_id INTEGER REFERENCES menus(id)'),
        ('left_menu_id', 'ALTER TABLE pages ADD COLUMN left_menu_id INTEGER REFERENCES menus(id)'),
        ('right_menu_id', 'ALTER TABLE pages ADD COLUMN right_menu_id INTEGER REFERENCES menus(id)'),
        ('footer_id', 'ALTER TABLE pages ADD COLUMN footer_id INTEGER REFERENCES footers(id)'),
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

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_site_by_domain(domain):
    """Look up a site by its domain"""
    # Strip port if present for matching
    domain_without_port = domain.split(':')[0] if ':' in domain else domain
    # Try exact match first
    site = Site.query.filter_by(domain=domain).first()
    if not site:
        # Try without port
        site = Site.query.filter_by(domain=domain_without_port).first()
    return site

def is_admin_domain(host):
    """Check if the request is coming from an admin domain"""
    host_lower = host.lower()
    host_without_port = host_lower.split(':')[0]
    return host_lower in ADMIN_DOMAINS or host_without_port in ['localhost', '127.0.0.1']

def get_page_menus_and_footer(page, site):
    """Get effective menus and footer for a page, considering page overrides and parent inheritance.
    Returns dict with menu/footer objects and their parsed content/styles.
    """
    result = {
        'top_menu': None, 'top_menu_items': [], 'top_menu_content': [], 'top_menu_styles': {},
        'left_menu': None, 'left_menu_items': [], 'left_menu_content': [], 'left_menu_styles': {},
        'right_menu': None, 'right_menu_items': [], 'right_menu_content': [], 'right_menu_styles': {},
        'footer': None, 'footer_content': [], 'footer_styles': {}
    }

    # Get effective menus (page-specific or inherited from parent, then site default)
    for position in ['top', 'left', 'right']:
        menu = page.get_effective_menu(position)
        if menu == 0:
            # Explicitly no menu - don't fall back to site default
            continue
        if not menu:
            # Fall back to site-wide active menu
            menu = Menu.query.filter_by(site_id=site.id, is_active=True, position=position).first()

        if menu:
            result[f'{position}_menu'] = menu
            result[f'{position}_menu_items'] = MenuItem.query.filter_by(menu_id=menu.id).order_by(MenuItem.order).all()
            result[f'{position}_menu_content'] = json.loads(menu.content) if menu.content else []
            try:
                result[f'{position}_menu_styles'] = json.loads(menu.menu_styles) if menu.menu_styles else {}
            except (json.JSONDecodeError, TypeError):
                result[f'{position}_menu_styles'] = {}

    # Get effective footer (page-specific or inherited from parent, then site default)
    footer = page.get_effective_footer()
    if footer == 0:
        # Explicitly no footer - don't fall back to site default
        footer = None
    elif not footer:
        footer = Footer.query.filter_by(site_id=site.id, is_active=True).first()

    if footer:
        result['footer'] = footer
        result['footer_content'] = json.loads(footer.content) if footer.content else []
        try:
            result['footer_styles'] = json.loads(footer.footer_styles) if footer.footer_styles else {}
        except (json.JSONDecodeError, TypeError):
            result['footer_styles'] = {}

    return result

@app.before_request
def detect_site_by_domain():
    """Detect which site to serve based on the Host header"""
    host = request.host.lower()
    g.is_admin = is_admin_domain(host)
    g.current_site = None

    if not g.is_admin:
        # This is a custom domain request - find the site
        g.current_site = get_site_by_domain(host)

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=bool(remember))
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout and redirect to login page"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Admin decorator
def admin_required(f):
    """Decorator to require admin access"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# User Management Routes
@app.route('/users')
@login_required
@admin_required
def users_list():
    """List all users (admin only)"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('cms/users.html', users=users)

@app.route('/users/create', methods=['POST'])
@login_required
@admin_required
def users_create():
    """Create a new user (admin only)"""
    data = request.get_json() if request.is_json else request.form
    username = data.get('username', '').strip()
    password = data.get('password', '')
    is_admin = data.get('is_admin', False)

    if not username or not password:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400
        flash('Username and password are required', 'danger')
        return redirect(url_for('users_list'))

    # Check if username already exists
    if User.query.filter_by(username=username).first():
        if request.is_json:
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        flash('Username already exists', 'danger')
        return redirect(url_for('users_list'))

    user = User(username=username, is_admin=bool(is_admin))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True, 'user_id': user.id})
    flash(f'User "{username}" created successfully', 'success')
    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def users_delete(user_id):
    """Delete a user (admin only)"""
    user = User.query.get_or_404(user_id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
        flash('Cannot delete your own account', 'danger')
        return redirect(url_for('users_list'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash(f'User "{username}" deleted successfully', 'success')
    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def users_toggle_admin(user_id):
    """Toggle admin status for a user (admin only)"""
    user = User.query.get_or_404(user_id)

    # Prevent removing your own admin status
    if user.id == current_user.id:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Cannot modify your own admin status'}), 400
        flash('Cannot modify your own admin status', 'danger')
        return redirect(url_for('users_list'))

    user.is_admin = not user.is_admin
    db.session.commit()

    status = 'admin' if user.is_admin else 'regular user'
    if request.is_json:
        return jsonify({'success': True, 'is_admin': user.is_admin})
    flash(f'User "{user.username}" is now a {status}', 'success')
    return redirect(url_for('users_list'))

@app.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def users_reset_password(user_id):
    """Reset password for a user (admin only)"""
    user = User.query.get_or_404(user_id)
    data = request.get_json() if request.is_json else request.form
    new_password = data.get('password', '')

    if not new_password:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Password is required'}), 400
        flash('Password is required', 'danger')
        return redirect(url_for('users_list'))

    user.set_password(new_password)
    db.session.commit()

    if request.is_json:
        return jsonify({'success': True})
    flash(f'Password reset for "{user.username}"', 'success')
    return redirect(url_for('users_list'))

# CMS Routes
@app.route('/')
def index():
    """CMS Dashboard or domain-based homepage"""
    # If accessing from a custom domain, serve the site's homepage (public)
    if not g.is_admin and g.current_site:
        return serve_domain_homepage(g.current_site)

    # CMS dashboard requires login
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    sites = Site.query.all()
    return render_template('cms/dashboard.html', sites=sites)

@app.route('/docs')
@login_required
def documentation():
    """Documentation and help page"""
    return render_template('cms/documentation.html')

def serve_domain_homepage(site):
    """Serve the homepage for a domain-based site"""
    # Find the root-level page with slug 'home' or 'index', or the first published root page
    homepage = Page.query.filter_by(site_id=site.id, parent_id=None, slug='home', published=True).first()
    if not homepage:
        homepage = Page.query.filter_by(site_id=site.id, parent_id=None, slug='index', published=True).first()
    if not homepage:
        # Get the first published root-level page
        homepage = Page.query.filter_by(site_id=site.id, parent_id=None, published=True).first()

    if not homepage:
        return render_template('public/no_homepage.html', site=site), 404

    return serve_domain_page(site, homepage)

def serve_domain_page(site, page):
    """Serve a page for a domain-based site (reusable helper)"""
    # Get effective menus and footer (page-specific, inherited, or site default)
    menus_data = get_page_menus_and_footer(page, site)

    # Parse page content and styles
    content = json.loads(page.content) if page.content else []
    try:
        page_styles = json.loads(page.page_styles) if page.page_styles else {}
    except (json.JSONDecodeError, TypeError):
        page_styles = {}

    return render_template('public/page.html',
                         page=page,
                         site=site,
                         top_menu=menus_data['top_menu'],
                         top_menu_items=menus_data['top_menu_items'],
                         top_menu_content=menus_data['top_menu_content'],
                         top_menu_styles=menus_data['top_menu_styles'],
                         left_menu=menus_data['left_menu'],
                         left_menu_items=menus_data['left_menu_items'],
                         left_menu_content=menus_data['left_menu_content'],
                         left_menu_styles=menus_data['left_menu_styles'],
                         right_menu=menus_data['right_menu'],
                         right_menu_items=menus_data['right_menu_items'],
                         right_menu_content=menus_data['right_menu_content'],
                         right_menu_styles=menus_data['right_menu_styles'],
                         footer=menus_data['footer'],
                         content=content,
                         page_styles=page_styles,
                         footer_content=menus_data['footer_content'],
                         footer_styles=menus_data['footer_styles'],
                         is_domain_based=True)

# Domain-based page route (catches all paths for custom domains)
@app.route('/<path:slug>')
def domain_page(slug):
    """Serve pages for custom domain requests"""
    # Only handle if this is a custom domain request
    if g.is_admin or not g.current_site:
        # This is admin domain - let other routes handle it or 404
        abort(404)

    site = g.current_site
    slug_parts = slug.split('/')

    # Find the page by traversing the hierarchy
    parent_id = None
    page = None
    for slug_part in slug_parts:
        page = Page.query.filter_by(
            site_id=site.id,
            slug=slug_part,
            parent_id=parent_id,
            published=True
        ).first()
        if not page:
            abort(404)
        parent_id = page.id

    return serve_domain_page(site, page)

@app.route('/site/create', methods=['GET', 'POST'])
@login_required
def create_site():
    """Create a new site"""
    if request.method == 'POST':
        data = request.json
        site = Site(
            name=data['name'],
            domain=data.get('domain', '')
        )
        db.session.add(site)
        db.session.commit()
        return jsonify({'success': True, 'site_id': site.id})
    return render_template('cms/site_form.html')

@app.route('/site/<int:site_id>')
@login_required
def site_detail(site_id):
    """Site detail page"""
    site = Site.query.get_or_404(site_id)
    pages = Page.query.filter_by(site_id=site_id).all()
    menus = Menu.query.filter_by(site_id=site_id).all()
    footers = Footer.query.filter_by(site_id=site_id).all()
    return render_template('cms/site_detail.html', site=site, pages=pages, menus=menus, footers=footers)

@app.route('/site/<int:site_id>/update', methods=['POST'])
@login_required
def update_site(site_id):
    """Update site settings (e.g., domain)"""
    site = Site.query.get_or_404(site_id)
    data = request.json

    if 'domain' in data:
        # Clean the domain - remove protocol and trailing slashes
        domain = data['domain'].strip()
        domain = domain.replace('https://', '').replace('http://', '')
        domain = domain.rstrip('/')
        site.domain = domain

    if 'name' in data:
        site.name = data['name']

    site.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'domain': site.domain})

@app.route('/site/<int:site_id>/page/create', methods=['GET', 'POST'])
@login_required
def create_page(site_id):
    """Create a new page"""
    site = Site.query.get_or_404(site_id)
    if request.method == 'POST':
        data = request.json
        parent_id = data.get('parent_id')
        if parent_id == '' or parent_id == 0:
            parent_id = None
        page = Page(
            site_id=site_id,
            parent_id=parent_id,
            title=data['title'],
            slug=data['slug'],
            content=json.dumps([])
        )
        db.session.add(page)
        db.session.commit()
        return jsonify({'success': True, 'page_id': page.id})

    # Get all pages for parent selection
    pages = Page.query.filter_by(site_id=site_id).all()
    return render_template('cms/page_form.html', site=site, pages=pages)

@app.route('/page/<int:page_id>/edit')
@login_required
def edit_page(page_id):
    """Page builder interface"""
    page = Page.query.get_or_404(page_id)
    site = Site.query.get(page.site_id)
    pages = Page.query.filter_by(site_id=site.id).all()

    # Convert pages to dict for JSON serialization (include full_path for nested pages)
    pages_list = [{'id': p.id, 'title': p.title, 'slug': p.slug, 'full_path': p.get_full_path()} for p in pages]

    # Get available menus and footers for this site
    menus = Menu.query.filter_by(site_id=site.id).all()
    footers = Footer.query.filter_by(site_id=site.id).all()

    # Parse page_styles for JavaScript
    try:
        page_styles_json = json.loads(page.page_styles) if page.page_styles else {}
    except (json.JSONDecodeError, TypeError):
        page_styles_json = {}

    return render_template('cms/page_builder.html',
                         page=page,
                         site=site,
                         pages=pages_list,
                         menus=menus,
                         footers=footers,
                         page_styles_json=page_styles_json)

@app.route('/page/<int:page_id>/save', methods=['POST'])
@login_required
def save_page(page_id):
    """Save page content"""
    page = Page.query.get_or_404(page_id)
    data = request.json

    if 'title' in data:
        page.title = data['title']
    if 'slug' in data:
        page.slug = data['slug']
    if 'content' in data:
        page.content = json.dumps(data['content'])
    if 'page_styles' in data:
        page.page_styles = json.dumps(data['page_styles'])

    # Handle page-specific menu assignments
    # Values: None/empty = use default, 0 = no menu, positive int = specific menu
    if 'top_menu_id' in data:
        val = data['top_menu_id']
        page.top_menu_id = val if val == 0 or val else None
    if 'left_menu_id' in data:
        val = data['left_menu_id']
        page.left_menu_id = val if val == 0 or val else None
    if 'right_menu_id' in data:
        val = data['right_menu_id']
        page.right_menu_id = val if val == 0 or val else None
    if 'footer_id' in data:
        val = data['footer_id']
        page.footer_id = val if val == 0 or val else None

    page.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True})

@app.route('/page/<int:page_id>/publish', methods=['POST'])
@login_required
def publish_page(page_id):
    """Publish or unpublish a page"""
    page = Page.query.get_or_404(page_id)
    data = request.json
    page.published = data.get('published', True)
    db.session.commit()
    return jsonify({'success': True, 'published': page.published})

@app.route('/page/<int:page_id>/delete', methods=['POST'])
@login_required
def delete_page(page_id):
    """Delete a page"""
    page = Page.query.get_or_404(page_id)
    site_id = page.site_id
    Widget.query.filter_by(page_id=page_id).delete()
    db.session.delete(page)
    db.session.commit()
    return jsonify({'success': True, 'redirect': url_for('site_detail', site_id=site_id)})

@app.route('/page/<int:page_id>/copy', methods=['POST'])
@login_required
def copy_page(page_id):
    """Copy a page and optionally all its children"""
    page = Page.query.get_or_404(page_id)
    data = request.json

    new_title = data.get('title', f'Copy of {page.title}')
    new_slug = data.get('slug', f'{page.slug}-copy')
    include_children = data.get('include_children', False)

    def copy_single_page(source_page, new_parent_id=None, title_override=None, slug_override=None):
        """Copy a single page and return the new page"""
        new_page = Page(
            site_id=source_page.site_id,
            parent_id=new_parent_id if new_parent_id is not None else source_page.parent_id,
            title=title_override or source_page.title,
            slug=slug_override or source_page.slug,
            content=source_page.content,
            page_styles=source_page.page_styles,
            published=False,  # Copies start as drafts
            top_menu_id=source_page.top_menu_id,
            left_menu_id=source_page.left_menu_id,
            right_menu_id=source_page.right_menu_id,
            footer_id=source_page.footer_id
        )
        db.session.add(new_page)
        db.session.flush()  # Get the new page ID
        return new_page

    def copy_page_tree(source_page, new_parent_id, is_root=False):
        """Recursively copy a page and all its children"""
        if is_root:
            new_page = copy_single_page(source_page, new_parent_id, new_title, new_slug)
        else:
            new_page = copy_single_page(source_page, new_parent_id)

        # Copy all children
        for child in source_page.children:
            copy_page_tree(child, new_page.id, is_root=False)

        return new_page

    if include_children:
        # Copy the page and all its descendants
        new_page = copy_page_tree(page, page.parent_id, is_root=True)
    else:
        # Copy just the single page
        new_page = copy_single_page(page, page.parent_id, new_title, new_slug)

    db.session.commit()

    return jsonify({
        'success': True,
        'page_id': new_page.id,
        'redirect': url_for('site_detail', site_id=page.site_id)
    })

@app.route('/site/<int:site_id>/menu/create', methods=['GET', 'POST'])
@login_required
def create_menu(site_id):
    """Create a new menu"""
    site = Site.query.get_or_404(site_id)
    if request.method == 'POST':
        data = request.json
        menu = Menu(
            site_id=site_id,
            name=data['name'],
            position=data.get('position', 'top')
        )
        db.session.add(menu)
        db.session.commit()
        return jsonify({'success': True, 'menu_id': menu.id})
    return render_template('cms/menu_form.html', site=site)

@app.route('/menu/<int:menu_id>/edit')
@login_required
def edit_menu(menu_id):
    """Menu builder interface"""
    menu = Menu.query.get_or_404(menu_id)
    site = Site.query.get(menu.site_id)
    menu_items = MenuItem.query.filter_by(menu_id=menu_id).order_by(MenuItem.order).all()
    pages = Page.query.filter_by(site_id=menu.site_id).all()

    # Convert pages to dict for JSON serialization (include full_path for nested pages)
    pages_list = [{'id': p.id, 'title': p.title, 'slug': p.slug, 'full_path': p.get_full_path()} for p in pages]

    # Parse menu content (widgets) from JSON
    menu_content = json.loads(menu.content) if menu.content else []

    # Parse menu styles from JSON
    try:
        menu_styles = json.loads(menu.menu_styles) if menu.menu_styles else {}
    except (json.JSONDecodeError, TypeError):
        menu_styles = {}

    return render_template('cms/menu_builder.html', menu=menu, site=site, menu_items=menu_items, pages=pages_list, menu_content=menu_content, menu_styles=menu_styles)

@app.route('/menu/<int:menu_id>/save', methods=['POST'])
@login_required
def save_menu(menu_id):
    """Save menu and menu items"""
    menu = Menu.query.get_or_404(menu_id)
    data = request.json

    if 'name' in data:
        menu.name = data['name']
    if 'position' in data:
        menu.position = data['position']
    if 'is_active' in data:
        menu.is_active = data['is_active']
    if 'menu_styles' in data:
        menu.menu_styles = json.dumps(data['menu_styles'])
    if 'content' in data:
        # Save widget content as JSON
        menu.content = json.dumps(data['content'])
    if 'items' in data:
        # Delete existing menu items
        MenuItem.query.filter_by(menu_id=menu_id).delete()

        # Create new menu items
        for idx, item_data in enumerate(data['items']):
            item = MenuItem(
                menu_id=menu_id,
                label=item_data['label'],
                link_type=item_data['link_type'],
                page_id=item_data.get('page_id'),
                custom_url=item_data.get('custom_url'),
                order=idx
            )
            db.session.add(item)

    menu.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@app.route('/menu/<int:menu_id>/delete', methods=['POST'])
@login_required
def delete_menu(menu_id):
    """Delete a menu"""
    menu = Menu.query.get_or_404(menu_id)
    site_id = menu.site_id
    MenuItem.query.filter_by(menu_id=menu_id).delete()
    db.session.delete(menu)
    db.session.commit()
    return jsonify({'success': True, 'redirect': url_for('site_detail', site_id=site_id)})

@app.route('/site/<int:site_id>/footer/create', methods=['GET', 'POST'])
@login_required
def create_footer(site_id):
    """Create a new footer"""
    site = Site.query.get_or_404(site_id)
    if request.method == 'POST':
        data = request.json
        footer = Footer(
            site_id=site_id,
            name=data['name'],
            content=json.dumps([])
        )
        db.session.add(footer)
        db.session.commit()
        return jsonify({'success': True, 'footer_id': footer.id})
    return render_template('cms/footer_form.html', site=site)

@app.route('/footer/<int:footer_id>/edit')
@login_required
def edit_footer(footer_id):
    """Footer builder interface"""
    footer = Footer.query.get_or_404(footer_id)
    site = Site.query.get(footer.site_id)
    pages = Page.query.filter_by(site_id=site.id).all()

    # Convert pages to dict for JSON serialization (include full_path for nested pages)
    pages_list = [{'id': p.id, 'title': p.title, 'slug': p.slug, 'full_path': p.get_full_path()} for p in pages]

    # Parse footer_styles
    footer_styles = {}
    if footer.footer_styles:
        try:
            footer_styles = json.loads(footer.footer_styles)
        except:
            footer_styles = {}

    return render_template('cms/footer_builder.html', footer=footer, site=site, pages=pages_list, footer_styles=footer_styles)

@app.route('/footer/<int:footer_id>/save', methods=['POST'])
@login_required
def save_footer(footer_id):
    """Save footer content"""
    footer = Footer.query.get_or_404(footer_id)
    data = request.json

    if 'name' in data:
        footer.name = data['name']
    if 'is_active' in data:
        footer.is_active = data['is_active']
    if 'content' in data:
        footer.content = json.dumps(data['content'])
    if 'footer_styles' in data:
        footer.footer_styles = json.dumps(data['footer_styles'])

    db.session.commit()
    return jsonify({'success': True})

@app.route('/footer/<int:footer_id>/delete', methods=['POST'])
@login_required
def delete_footer(footer_id):
    """Delete a footer"""
    footer = Footer.query.get_or_404(footer_id)
    site_id = footer.site_id
    db.session.delete(footer)
    db.session.commit()
    return jsonify({'success': True, 'redirect': url_for('site_detail', site_id=site_id)})

@app.route('/preview/<int:page_id>')
@login_required
def preview_page(page_id):
    """Preview a page"""
    page = Page.query.get_or_404(page_id)
    site = Site.query.get(page.site_id)

    # Get effective menus and footer (page-specific, inherited, or site default)
    menus_data = get_page_menus_and_footer(page, site)

    # Parse page content and styles
    content = json.loads(page.content) if page.content else []
    try:
        page_styles = json.loads(page.page_styles) if page.page_styles else {}
    except (json.JSONDecodeError, TypeError):
        page_styles = {}

    return render_template('preview/page.html',
                         page=page,
                         site=site,
                         top_menu=menus_data['top_menu'],
                         top_menu_items=menus_data['top_menu_items'],
                         top_menu_content=menus_data['top_menu_content'],
                         top_menu_styles=menus_data['top_menu_styles'],
                         left_menu=menus_data['left_menu'],
                         left_menu_items=menus_data['left_menu_items'],
                         left_menu_content=menus_data['left_menu_content'],
                         left_menu_styles=menus_data['left_menu_styles'],
                         right_menu=menus_data['right_menu'],
                         right_menu_items=menus_data['right_menu_items'],
                         right_menu_content=menus_data['right_menu_content'],
                         right_menu_styles=menus_data['right_menu_styles'],
                         footer=menus_data['footer'],
                         content=content,
                         page_styles=page_styles,
                         footer_content=menus_data['footer_content'],
                         footer_styles=menus_data['footer_styles'])

# Public site routes (for live sites)
@app.route('/site/<int:site_id>/<path:slug>')
def public_page(site_id, slug):
    """Public page view - only shows published pages"""
    # Handle nested paths like admin/reports/somepage
    slug_parts = slug.split('/')

    # Find the page by traversing the hierarchy
    parent_id = None
    page = None
    for slug_part in slug_parts:
        page = Page.query.filter_by(
            site_id=site_id,
            slug=slug_part,
            parent_id=parent_id,
            published=True
        ).first()
        if not page:
            abort(404)
        parent_id = page.id
    site = Site.query.get(site_id)

    # Get effective menus and footer (page-specific, inherited, or site default)
    menus_data = get_page_menus_and_footer(page, site)

    # Parse page content and styles
    content = json.loads(page.content) if page.content else []
    try:
        page_styles = json.loads(page.page_styles) if page.page_styles else {}
    except (json.JSONDecodeError, TypeError):
        page_styles = {}

    return render_template('public/page.html',
                         page=page,
                         site=site,
                         top_menu=menus_data['top_menu'],
                         top_menu_items=menus_data['top_menu_items'],
                         top_menu_content=menus_data['top_menu_content'],
                         top_menu_styles=menus_data['top_menu_styles'],
                         left_menu=menus_data['left_menu'],
                         left_menu_items=menus_data['left_menu_items'],
                         left_menu_content=menus_data['left_menu_content'],
                         left_menu_styles=menus_data['left_menu_styles'],
                         right_menu=menus_data['right_menu'],
                         right_menu_items=menus_data['right_menu_items'],
                         right_menu_content=menus_data['right_menu_content'],
                         right_menu_styles=menus_data['right_menu_styles'],
                         footer=menus_data['footer'],
                         content=content,
                         page_styles=page_styles,
                         footer_content=menus_data['footer_content'],
                         footer_styles=menus_data['footer_styles'])

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Upload an image file"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file part'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'success': False, 'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Save file
        file.save(filepath)

        # Return URL for the uploaded file
        file_url = f"/static/uploads/{filename}"
        return jsonify({'success': True, 'url': file_url})

    return jsonify({'success': False, 'error': 'File type not allowed'}), 400

@app.route('/images/list')
@login_required
def list_images():
    """List all images in the uploads directory"""
    uploads_dir = os.path.join(app.static_folder, 'uploads')

    if not os.path.exists(uploads_dir):
        return jsonify({'success': True, 'images': []})

    images = []
    for filename in os.listdir(uploads_dir):
        if allowed_file(filename):
            images.append({
                'filename': filename,
                'url': f'/static/uploads/{filename}'
            })

    # Sort by filename (most recent first if using timestamp-based names)
    images.sort(key=lambda x: x['filename'], reverse=True)

    return jsonify({'success': True, 'images': images})

@app.route('/api/caspio/datapages')
@login_required
def get_caspio_datapages():
    """Get all Caspio datapages organized by app and folder"""
    result = caspio_api.get_datapages()
    return jsonify(result)

@app.route('/api/caspio/status')
@login_required
def get_caspio_status():
    """Check if Caspio API is configured"""
    return jsonify({
        'configured': caspio_api.is_configured(),
        'account_id': caspio_api.account_id if caspio_api.is_configured() else None
    })

if __name__ == '__main__':
    app.run(debug=True)
