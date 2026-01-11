"""Menu and MenuItem models"""
from datetime import datetime
from app.extensions import db


class Menu(db.Model):
    """Represents a navigation menu"""
    __tablename__ = 'menus'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(20), default='top')  # top, left, right
    is_active = db.Column(db.Boolean, default=True)
    is_sticky = db.Column(db.Boolean, default=False)  # Sticky at top of page (top menus only)
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
