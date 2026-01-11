"""
Backward compatibility module - imports from new extensions module.
This file maintains backward compatibility for any code that imports from database.py.
The db instance is now defined in app/extensions.py and imported here.
"""
from app.extensions import db

__all__ = ['db']
