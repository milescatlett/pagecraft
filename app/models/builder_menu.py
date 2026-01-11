"""Menu mapping model for Caspio user-based menus (by builder or role)"""
from datetime import datetime
from app.extensions import db


class BuilderMenuMapping(db.Model):
    """Maps builder names or roles (from Caspio) to specific menus.

    Can match on:
    - builder_name: String match (e.g., "NVR INC", "STANLEY MARTIN")
    - role: Integer match (e.g., 1, 2, 3)

    Priority: Builder match takes precedence over role match.
    """
    __tablename__ = 'builder_menu_mappings'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False)

    # Condition fields - at least one should be set
    builder_name = db.Column(db.String(200), nullable=True)  # e.g., "NVR INC", "STANLEY MARTIN"
    role = db.Column(db.Integer, nullable=True)  # e.g., 1, 2, 3

    # Menu assignments (nullable - if null, use site default)
    top_menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True)
    left_menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True)
    right_menu_id = db.Column(db.Integer, db.ForeignKey('menus.id'), nullable=True)
    footer_id = db.Column(db.Integer, db.ForeignKey('footers.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = db.relationship('Site', backref=db.backref('builder_mappings', lazy=True))
    top_menu = db.relationship('Menu', foreign_keys=[top_menu_id])
    left_menu = db.relationship('Menu', foreign_keys=[left_menu_id])
    right_menu = db.relationship('Menu', foreign_keys=[right_menu_id])
    footer = db.relationship('Footer', foreign_keys=[footer_id])

    def __repr__(self):
        if self.builder_name:
            return f'<MenuMapping builder={self.builder_name}>'
        elif self.role is not None:
            return f'<MenuMapping role={self.role}>'
        return f'<MenuMapping id={self.id}>'

    @property
    def condition_display(self):
        """Human-readable condition string"""
        if self.builder_name:
            return f'Builder: {self.builder_name}'
        elif self.role is not None:
            return f'Role: {self.role}'
        return 'No condition'

    @property
    def condition_type(self):
        """Returns 'builder' or 'role' based on which is set"""
        if self.builder_name:
            return 'builder'
        elif self.role is not None:
            return 'role'
        return None

    @classmethod
    def get_for_user(cls, site_id, builder_name=None, role=None):
        """
        Get menu mapping for a user based on builder name and/or role.

        Priority:
        1. Exact builder name match (case-insensitive)
        2. Role match

        Args:
            site_id: The site ID
            builder_name: Builder name from Caspio (optional)
            role: Role integer from Caspio (optional)

        Returns:
            BuilderMenuMapping or None
        """
        # Priority 1: Try builder name match first
        if builder_name:
            mapping = cls.query.filter(
                cls.site_id == site_id,
                cls.builder_name.isnot(None),
                db.func.lower(cls.builder_name) == builder_name.lower()
            ).first()
            if mapping:
                return mapping

        # Priority 2: Try role match
        if role is not None:
            # Convert role to int if it's a string
            try:
                role_int = int(role)
            except (ValueError, TypeError):
                role_int = None

            if role_int is not None:
                mapping = cls.query.filter(
                    cls.site_id == site_id,
                    cls.role == role_int
                ).first()
                if mapping:
                    return mapping

        return None

    @classmethod
    def get_for_builder(cls, site_id, builder_name):
        """Legacy method - get menu mapping for a specific builder only"""
        if not builder_name:
            return None
        return cls.query.filter(
            cls.site_id == site_id,
            cls.builder_name.isnot(None),
            db.func.lower(cls.builder_name) == builder_name.lower()
        ).first()
