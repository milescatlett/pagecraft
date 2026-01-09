from datetime import datetime
from database import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    """Represents a user for authentication"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Site(db.Model):
    """Represents a website"""
    __tablename__ = 'sites'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    domain = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    pages = db.relationship('Page', backref='site', lazy=True, cascade='all, delete-orphan')
    menus = db.relationship('Menu', backref='site', lazy=True, cascade='all, delete-orphan')
    footers = db.relationship('Footer', backref='site', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Site {self.name}>'


class Page(db.Model):
    """Represents a page within a site"""
    __tablename__ = 'pages'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)  # JSON string of widgets
    page_styles = db.Column(db.Text)  # JSON string of page styling
    published = db.Column(db.Boolean, default=False)  # Whether page is live
    is_homepage = db.Column(db.Boolean, default=False)  # Whether this is the site's homepage
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Page-specific menu overrides (nullable - inherits from parent or uses site default)
    top_menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True)
    left_menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True)
    right_menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True)
    footer_id = db.Column(db.Integer, db.ForeignKey('footers.id'), nullable=True)

    # Relationships
    widgets = db.relationship('Widget', backref='page', lazy=True, cascade='all, delete-orphan')
    children = db.relationship('Page', backref=db.backref('parent', remote_side='Page.id'), lazy=True)
    top_menu = db.relationship('Menu', foreign_keys=[top_menu_id])
    left_menu = db.relationship('Menu', foreign_keys=[left_menu_id])
    right_menu = db.relationship('Menu', foreign_keys=[right_menu_id])
    page_footer = db.relationship('Footer', foreign_keys=[footer_id])

    def get_full_path(self):
        """Get the full URL path including all parent slugs"""
        path_parts = [self.slug]
        current = self
        while current.parent_id:
            current = Page.query.get(current.parent_id)
            if current:
                path_parts.insert(0, current.slug)
            else:
                break
        return '/'.join(path_parts)

    def get_ancestors(self):
        """Get list of ancestor pages from root to parent"""
        ancestors = []
        current = self
        while current.parent_id:
            current = Page.query.get(current.parent_id)
            if current:
                ancestors.insert(0, current)
            else:
                break
        return ancestors

    def get_effective_menu(self, position):
        """Get the effective menu for this page at given position.
        Checks this page first, then traverses up parent hierarchy.
        Returns:
            - Menu object if a specific menu is set
            - 0 if explicitly set to "no menu"
            - None if no page-specific setting found (use site default)
        """
        menu_attr = f'{position}_menu_id'
        current = self
        while current:
            menu_id = getattr(current, menu_attr, None)
            if menu_id is not None:
                if menu_id == 0:
                    return 0  # Explicitly no menu
                from models import Menu
                return Menu.query.get(menu_id)
            if current.parent_id:
                current = Page.query.get(current.parent_id)
            else:
                break
        return None

    def get_effective_footer(self):
        """Get the effective footer for this page.
        Checks this page first, then traverses up parent hierarchy.
        Returns:
            - Footer object if a specific footer is set
            - 0 if explicitly set to "no footer"
            - None if no page-specific setting found (use site default)
        """
        current = self
        while current:
            if current.footer_id is not None:
                if current.footer_id == 0:
                    return 0  # Explicitly no footer
                from models import Footer
                return Footer.query.get(current.footer_id)
            if current.parent_id:
                current = Page.query.get(current.parent_id)
            else:
                break
        return None

    def __repr__(self):
        return f'<Page {self.title}>'


class Menu(db.Model):
    """Represents a navigation menu"""
    __tablename__ = 'menus'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(20), default='top')  # top, left, right
    is_active = db.Column(db.Boolean, default=True)
    content = db.Column(db.Text)  # JSON string of widgets
    menu_styles = db.Column(db.Text)  # JSON string of menu styling
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    menu_items = db.relationship('MenuItem', backref='menu', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Menu {self.name}>'


class MenuItem(db.Model):
    """Represents an item in a menu"""
    __tablename__ = 'menu_items'

    id = db.Column(db.Integer, primary_key=True)
    menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=False)
    label = db.Column(db.String(100), nullable=False)
    link_type = db.Column(db.String(20), default='page')  # page, custom
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=True)
    custom_url = db.Column(db.String(500), nullable=True)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MenuItem {self.label}>'


class Footer(db.Model):
    """Represents a footer"""
    __tablename__ = 'footers'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text)  # JSON string of widgets
    is_active = db.Column(db.Boolean, default=True)
    footer_styles = db.Column(db.Text)  # JSON string of footer styling
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Footer {self.name}>'


class Widget(db.Model):
    """Represents a widget on a page"""
    __tablename__ = 'widgets'

    id = db.Column(db.Integer, primary_key=True)
    page_id = db.Column(db.Integer, db.ForeignKey('pages.id'), nullable=False)
    widget_type = db.Column(db.String(50), nullable=False)  # richtext, html, title, separator, button, card, etc.
    content = db.Column(db.Text)  # JSON string of widget data
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Widget {self.widget_type}>'
