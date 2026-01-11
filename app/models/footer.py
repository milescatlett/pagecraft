"""Footer model"""
from datetime import datetime
from app.extensions import db


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
