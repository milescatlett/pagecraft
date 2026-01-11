"""Authorization decorators to prevent unauthorized resource access"""
from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def admin_required(f):
    """
    Decorator to require admin access.
    Redirects non-admin users to index.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        if not current_user.is_admin:
            flash('You need admin privileges to access this page.', 'danger')
            return redirect(url_for('cms.index'))

        return f(*args, **kwargs)
    return decorated_function


def site_access_required(f):
    """
    Decorator to verify user has access to a site.
    Expects 'site_id' in route parameters.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import Site

        site_id = kwargs.get('site_id')
        if not site_id:
            abort(400, "Site ID required")

        site = Site.query.get_or_404(site_id)

        # For now, all authenticated users can access all sites
        # In future, add user-site ownership relationship
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # Store site in kwargs for use in route
        kwargs['site'] = site
        return f(*args, **kwargs)

    return decorated_function


def page_access_required(f):
    """
    Decorator to verify user has access to a page.
    Expects 'page_id' or 'id' in route parameters.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import Page, Site

        page_id = kwargs.get('page_id') or kwargs.get('id')
        if not page_id:
            abort(400, "Page ID required")

        page = Page.query.get_or_404(page_id)
        site = Site.query.get_or_404(page.site_id)

        # Verify user is authenticated
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # TODO: Add user-site ownership check when implemented
        # For now, all authenticated users can access all pages

        # Store page and site in kwargs for use in route
        kwargs['page'] = page
        kwargs['site'] = site
        return f(*args, **kwargs)

    return decorated_function


def menu_access_required(f):
    """
    Decorator to verify user has access to a menu.
    Expects 'menu_id' or 'id' in route parameters.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import Menu, Site

        menu_id = kwargs.get('menu_id') or kwargs.get('id')
        if not menu_id:
            abort(400, "Menu ID required")

        menu = Menu.query.get_or_404(menu_id)
        site = Site.query.get_or_404(menu.site_id)

        # Verify user is authenticated
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # TODO: Add user-site ownership check when implemented

        # Store menu and site in kwargs for use in route
        kwargs['menu'] = menu
        kwargs['site'] = site
        return f(*args, **kwargs)

    return decorated_function


def footer_access_required(f):
    """
    Decorator to verify user has access to a footer.
    Expects 'footer_id' or 'id' in route parameters.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.models import Footer, Site

        footer_id = kwargs.get('footer_id') or kwargs.get('id')
        if not footer_id:
            abort(400, "Footer ID required")

        footer = Footer.query.get_or_404(footer_id)
        site = Site.query.get_or_404(footer.site_id)

        # Verify user is authenticated
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))

        # TODO: Add user-site ownership check when implemented

        # Store footer and site in kwargs for use in route
        kwargs['footer'] = footer
        kwargs['site'] = site
        return f(*args, **kwargs)

    return decorated_function
