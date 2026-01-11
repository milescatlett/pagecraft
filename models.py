"""
Backward compatibility module - imports from new modular structure.
This file maintains backward compatibility for any code that imports from models.py.
All models are now defined in app/models/ and imported here.
"""
from app.models import User, Site, Page, Widget, Menu, MenuItem, Footer

__all__ = ['User', 'Site', 'Page', 'Widget', 'Menu', 'MenuItem', 'Footer']
