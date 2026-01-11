"""Public blueprint for serving published pages"""
import json
from flask import Blueprint, render_template, g, abort, session
from app.models import Site, Page
from app.services.menu_service import MenuService

bp = Blueprint('public', __name__)


@bp.route('/site/<int:site_id>/<path:slug>')
def public_page(site_id, slug):
    """
    Public page view - only shows published pages.
    Supports hierarchical URLs like /site/1/parent/child/grandchild
    """
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

    site = Site.query.get_or_404(site_id)

    # Get Caspio user from session for user-specific menu rendering
    caspio_user = session.get('caspio_user')
    caspio_user_data = session.get('caspio_user_data', {})
    builder_name = caspio_user_data.get('builder')
    role = caspio_user_data.get('role')

    # Get effective menus and footer (builder-specific, role-specific, page-specific, inherited, or site default)
    menus_data = MenuService.get_page_menus_and_footer(page, site, builder_name=builder_name, role=role)

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
                         caspio_user=caspio_user,
                         caspio_user_data=caspio_user_data)


@bp.route('/<path:slug>')
def domain_page(slug):
    """
    Serve pages for custom domain requests.
    Only processes requests from non-admin domains.
    """
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

    return _serve_domain_page(site, page)


def _serve_domain_homepage(site):
    """Serve the homepage for a domain-based site"""
    # First, check for a page explicitly marked as homepage
    homepage = Page.query.filter_by(site_id=site.id, is_homepage=True, published=True).first()

    # Fallback: Find the root-level page with slug 'home' or 'index', or the first published root page
    if not homepage:
        homepage = Page.query.filter_by(site_id=site.id, parent_id=None, slug='home', published=True).first()
    if not homepage:
        homepage = Page.query.filter_by(site_id=site.id, parent_id=None, slug='index', published=True).first()
    if not homepage:
        # Get the first published root-level page
        homepage = Page.query.filter_by(site_id=site.id, parent_id=None, published=True).first()

    if not homepage:
        return render_template('public/no_homepage.html', site=site), 404

    return _serve_domain_page(site, homepage)


def _serve_domain_page(site, page):
    """Serve a page for a domain-based site (reusable helper)"""
    # Get Caspio user from session for user-specific menu rendering
    caspio_user = session.get('caspio_user')
    caspio_user_data = session.get('caspio_user_data', {})
    builder_name = caspio_user_data.get('builder')
    role = caspio_user_data.get('role')

    # Get effective menus and footer (builder-specific, role-specific, page-specific, inherited, or site default)
    menus_data = MenuService.get_page_menus_and_footer(page, site, builder_name=builder_name, role=role)

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
                         is_domain_based=True,
                         caspio_user=caspio_user,
                         caspio_user_data=caspio_user_data)
