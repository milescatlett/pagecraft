"""Site model"""
from datetime import datetime
from app.extensions import db


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

    @classmethod
    def get_by_domain(cls, domain):
        """
        Look up a site by its domain.

        Args:
            domain (str): Domain name with or without port

        Returns:
            Site: Site object or None
        """
        # Strip port if present for matching
        domain_without_port = domain.split(':')[0] if ':' in domain else domain

        # Try exact match first
        site = cls.query.filter_by(domain=domain).first()
        if not site:
            # Try without port
            site = cls.query.filter_by(domain=domain_without_port).first()

        return site

    def __repr__(self):
        return f'<Site {self.name}>'
