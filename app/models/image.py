"""Image models for media library"""
from datetime import datetime
from app.extensions import db


class Image(db.Model):
    """Represents an uploaded image with metadata"""
    __tablename__ = 'images'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), unique=True, nullable=False)  # UUID filename
    original_filename = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(500), nullable=False)  # /static/uploads/...
    file_size = db.Column(db.Integer, nullable=False)  # bytes
    width = db.Column(db.Integer, nullable=True)  # pixels
    height = db.Column(db.Integer, nullable=True)  # pixels
    mime_type = db.Column(db.String(50), nullable=False)

    # Organization
    folder_id = db.Column(db.Integer, db.ForeignKey('image_folders.id'), nullable=True)
    tags = db.Column(db.Text, nullable=True)  # JSON array of strings

    # Audit fields
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    folder = db.relationship('ImageFolder', back_populates='images')
    uploader = db.relationship('User', backref='uploaded_images')

    def __repr__(self):
        return f'<Image {self.original_filename}>'

    def to_dict(self):
        """Convert image to dictionary"""
        import json
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'url': self.url,
            'file_size': self.file_size,
            'width': self.width,
            'height': self.height,
            'mime_type': self.mime_type,
            'folder_id': self.folder_id,
            'folder_name': self.folder.name if self.folder else None,
            'folder_path': self.folder.get_path() if self.folder else 'Root',
            'tags': json.loads(self.tags) if self.tags else [],
            'uploaded_by': self.uploader.username if self.uploader else None,
            'uploaded_at': self.uploaded_at.isoformat()
        }


class ImageFolder(db.Model):
    """Represents a folder for organizing images (hierarchical)"""
    __tablename__ = 'image_folders'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('image_folders.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    parent = db.relationship('ImageFolder', remote_side='ImageFolder.id', backref='children')
    images = db.relationship('Image', back_populates='folder', lazy='dynamic')

    def get_path(self):
        """Get full folder path like 'Parent/Child/Current'"""
        path_parts = [self.name]
        current = self
        while current.parent_id:
            current = ImageFolder.query.get(current.parent_id)
            if current:
                path_parts.insert(0, current.name)
            else:
                break
        return '/'.join(path_parts)

    def __repr__(self):
        return f'<ImageFolder {self.name}>'

    def to_dict(self, include_children=False):
        """Convert folder to dictionary"""
        result = {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'image_count': self.images.count(),
            'created_at': self.created_at.isoformat()
        }
        if include_children:
            result['children'] = [child.to_dict(include_children=True) for child in self.children]
        return result
