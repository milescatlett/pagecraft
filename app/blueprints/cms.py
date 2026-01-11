"""CMS blueprint for site management, page builder, menu builder, footer builder"""
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, g
from flask_login import login_required, current_user
from app.models import Site, Page, Menu, MenuItem, Footer, Widget, BuilderMenuMapping
from app.extensions import db, limiter
from app.services.page_service import PageService
from app.services.menu_service import MenuService
from app.services.widget_service import WidgetService
from app.utils.decorators import site_access_required, page_access_required, menu_access_required, footer_access_required
from app.blueprints.public import _serve_domain_homepage

bp = Blueprint('cms', __name__)


@bp.route('/')
def index():
    """CMS Dashboard or domain-based homepage"""
    # If accessing from a custom domain, serve the site's homepage (public)
    if not g.is_admin and g.current_site:
        return _serve_domain_homepage(g.current_site)

    # CMS dashboard requires login
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    sites = Site.query.all()
    return render_template('cms/dashboard.html', sites=sites)


@bp.route('/docs')
@login_required
def documentation():
    """Documentation and help page"""
    return render_template('cms/documentation.html')


@bp.route('/images')
@login_required
def images():
    """Image gallery management page"""
    return render_template('cms/images.html')


# Site Management Routes

@bp.route('/site/create', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per minute")
def create_site():
    """Create a new site with CSRF protection"""
    if request.method == 'POST':
        data = request.json
        site = Site(
            name=data['name'],
            domain=data.get('domain', '')
        )
        db.session.add(site)
        db.session.commit()
        return jsonify({'success': True, 'site_id': site.id})
    return render_template('cms/site_form.html')


@bp.route('/site/<int:site_id>')
@login_required
def site_detail(site_id):
    """Site detail page"""
    site = Site.query.get_or_404(site_id)
    pages = Page.query.filter_by(site_id=site_id).all()
    menus = Menu.query.filter_by(site_id=site_id).all()
    footers = Footer.query.filter_by(site_id=site_id).all()
    return render_template('cms/site_detail.html', site=site, pages=pages, menus=menus, footers=footers)


@bp.route('/site/<int:site_id>/update', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def update_site(site_id):
    """Update site settings (e.g., domain) with CSRF protection"""
    site = Site.query.get_or_404(site_id)
    data = request.json

    if 'domain' in data:
        # Clean the domain - remove protocol and trailing slashes
        domain = data['domain'].strip()
        domain = domain.replace('https://', '').replace('http://', '')
        domain = domain.rstrip('/')
        site.domain = domain

    if 'name' in data:
        site.name = data['name']

    site.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True, 'domain': site.domain})


# Page Management Routes

@bp.route('/site/<int:site_id>/page/create', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per minute")
def create_page(site_id):
    """Create a new page with CSRF protection and validation"""
    site = Site.query.get_or_404(site_id)
    if request.method == 'POST':
        data = request.json
        parent_id = data.get('parent_id')
        if parent_id == '' or parent_id == 0:
            parent_id = None

        # Create page through service (includes validation)
        page, error = PageService.create_page(
            site_id=site_id,
            title=data['title'],
            slug=data['slug'],
            parent_id=parent_id,
            content=json.dumps([])
        )

        if error:
            return jsonify({'success': False, 'error': error}), 400

        return jsonify({'success': True, 'page_id': page.id})

    # Get all pages for parent selection
    pages = Page.query.filter_by(site_id=site_id).all()
    return render_template('cms/page_form.html', site=site, pages=pages)


@bp.route('/page/<int:page_id>/edit')
@login_required
def edit_page(page_id):
    """Page builder interface"""
    page = Page.query.get_or_404(page_id)
    site = Site.query.get(page.site_id)
    pages = Page.query.filter_by(site_id=site.id).all()

    # Convert pages to dict for JSON serialization (include full_path for nested pages)
    pages_list = [{'id': p.id, 'title': p.title, 'slug': p.slug, 'full_path': p.get_full_path()} for p in pages]

    # Get available menus and footers for this site
    menus = Menu.query.filter_by(site_id=site.id).all()
    footers = Footer.query.filter_by(site_id=site.id).all()

    # Parse page_styles for JavaScript
    try:
        page_styles_json = json.loads(page.page_styles) if page.page_styles else {}
    except (json.JSONDecodeError, TypeError):
        page_styles_json = {}

    return render_template('cms/page_builder.html',
                         page=page,
                         site=site,
                         pages=pages_list,
                         menus=menus,
                         footers=footers,
                         page_styles_json=page_styles_json)


@bp.route('/page/<int:page_id>/save', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def save_page(page_id):
    """Save page content with CSRF protection and sanitization"""
    page = Page.query.get_or_404(page_id)
    data = request.json

    if 'title' in data:
        page.title = data['title']
    if 'slug' in data:
        page.slug = data['slug']

    # Sanitize and save widget content
    if 'content' in data:
        success, error = PageService.update_page_content(page_id, data['content'])
        if not success:
            return jsonify({'success': False, 'error': error}), 400

    # Sanitize and save page styles
    if 'page_styles' in data:
        success, error = PageService.update_page_styles(page_id, data['page_styles'])
        if not success:
            return jsonify({'success': False, 'error': error}), 400

    # Handle page-specific menu assignments
    # Values: None/empty = use default, 0 = no menu, positive int = specific menu
    if 'top_menu_id' in data:
        val = data['top_menu_id']
        page.top_menu_id = val if val == 0 or val else None
    if 'left_menu_id' in data:
        val = data['left_menu_id']
        page.left_menu_id = val if val == 0 or val else None
    if 'right_menu_id' in data:
        val = data['right_menu_id']
        page.right_menu_id = val if val == 0 or val else None
    if 'footer_id' in data:
        val = data['footer_id']
        page.footer_id = val if val == 0 or val else None

    # Handle homepage setting - only one page per site can be the homepage
    if 'is_homepage' in data:
        if data['is_homepage']:
            # Unset any existing homepage for this site
            Page.query.filter_by(site_id=page.site_id, is_homepage=True).update({'is_homepage': False})
            page.is_homepage = True
        else:
            page.is_homepage = False

    page.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({'success': True})


@bp.route('/page/<int:page_id>/publish', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def publish_page(page_id):
    """Publish or unpublish a page with CSRF protection"""
    page = Page.query.get_or_404(page_id)
    data = request.json
    page.published = data.get('published', True)
    db.session.commit()
    return jsonify({'success': True, 'published': page.published})


@bp.route('/page/<int:page_id>/delete', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def delete_page(page_id):
    """Delete a page with CSRF protection"""
    page = Page.query.get_or_404(page_id)
    site_id = page.site_id
    Widget.query.filter_by(page_id=page_id).delete()
    db.session.delete(page)
    db.session.commit()
    return jsonify({'success': True, 'redirect': url_for('cms.site_detail', site_id=site_id)})


@bp.route('/page/<int:page_id>/copy', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def copy_page_route(page_id):
    """Copy a page and optionally all its children with CSRF protection"""
    page = Page.query.get_or_404(page_id)
    data = request.json

    include_children = data.get('include_children', False)

    # Use page service for copying
    new_page = PageService.copy_page(page_id, include_children)

    if not new_page:
        return jsonify({'success': False, 'error': 'Failed to copy page'}), 500

    return jsonify({
        'success': True,
        'page_id': new_page.id,
        'redirect': url_for('cms.site_detail', site_id=page.site_id)
    })


# Menu Management Routes

@bp.route('/site/<int:site_id>/menu/create', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per minute")
def create_menu(site_id):
    """Create a new menu with CSRF protection"""
    site = Site.query.get_or_404(site_id)
    if request.method == 'POST':
        data = request.json
        menu = Menu(
            site_id=site_id,
            name=data['name'],
            position=data.get('position', 'top')
        )
        db.session.add(menu)
        db.session.commit()
        return jsonify({'success': True, 'menu_id': menu.id})
    return render_template('cms/menu_form.html', site=site)


@bp.route('/menu/<int:menu_id>/edit')
@login_required
def edit_menu(menu_id):
    """Menu builder interface"""
    menu = Menu.query.get_or_404(menu_id)
    site = Site.query.get(menu.site_id)
    menu_items = MenuItem.query.filter_by(menu_id=menu_id).order_by(MenuItem.order).all()
    pages = Page.query.filter_by(site_id=menu.site_id).all()

    # Convert pages to dict for JSON serialization (include full_path for nested pages)
    pages_list = [{'id': p.id, 'title': p.title, 'slug': p.slug, 'full_path': p.get_full_path()} for p in pages]

    # Parse menu content (widgets) from JSON
    menu_content = json.loads(menu.content) if menu.content else []

    # Parse menu styles from JSON
    try:
        menu_styles = json.loads(menu.menu_styles) if menu.menu_styles else {}
    except (json.JSONDecodeError, TypeError):
        menu_styles = {}

    return render_template('cms/menu_builder.html', menu=menu, site=site, menu_items=menu_items, pages=pages_list, menu_content=menu_content, menu_styles=menu_styles)


@bp.route('/menu/<int:menu_id>/save', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def save_menu(menu_id):
    """Save menu and menu items with CSRF protection and sanitization"""
    menu = Menu.query.get_or_404(menu_id)
    data = request.json

    if 'name' in data:
        menu.name = data['name']
    if 'position' in data:
        menu.position = data['position']
    if 'is_active' in data:
        menu.is_active = data['is_active']
    if 'is_sticky' in data:
        menu.is_sticky = data['is_sticky']

    # Sanitize and save menu styles
    if 'menu_styles' in data:
        from app.utils.security import sanitize_css_properties
        sanitized_styles = sanitize_css_properties(data['menu_styles'])
        menu.menu_styles = json.dumps(sanitized_styles)

    # Sanitize and save widget content
    if 'content' in data:
        sanitized_content = WidgetService.sanitize_widget_array(data['content'])
        menu.content = json.dumps(sanitized_content)

    if 'items' in data:
        # Delete existing menu items
        MenuItem.query.filter_by(menu_id=menu_id).delete()

        # Create new menu items
        for idx, item_data in enumerate(data['items']):
            item = MenuItem(
                menu_id=menu_id,
                label=item_data['label'],
                link_type=item_data['link_type'],
                page_id=item_data.get('page_id'),
                custom_url=item_data.get('custom_url'),
                order=idx
            )
            db.session.add(item)

    menu.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/menu/<int:menu_id>/delete', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def delete_menu(menu_id):
    """Delete a menu with CSRF protection"""
    menu = Menu.query.get_or_404(menu_id)
    site_id = menu.site_id
    MenuItem.query.filter_by(menu_id=menu_id).delete()
    db.session.delete(menu)
    db.session.commit()
    return jsonify({'success': True, 'redirect': url_for('cms.site_detail', site_id=site_id)})


# Footer Management Routes

@bp.route('/site/<int:site_id>/footer/create', methods=['GET', 'POST'])
@login_required
@limiter.limit("30 per minute")
def create_footer(site_id):
    """Create a new footer with CSRF protection"""
    site = Site.query.get_or_404(site_id)
    if request.method == 'POST':
        data = request.json
        footer = Footer(
            site_id=site_id,
            name=data['name'],
            content=json.dumps([])
        )
        db.session.add(footer)
        db.session.commit()
        return jsonify({'success': True, 'footer_id': footer.id})
    return render_template('cms/footer_form.html', site=site)


@bp.route('/footer/<int:footer_id>/edit')
@login_required
def edit_footer(footer_id):
    """Footer builder interface"""
    footer = Footer.query.get_or_404(footer_id)
    site = Site.query.get(footer.site_id)
    pages = Page.query.filter_by(site_id=site.id).all()

    # Convert pages to dict for JSON serialization (include full_path for nested pages)
    pages_list = [{'id': p.id, 'title': p.title, 'slug': p.slug, 'full_path': p.get_full_path()} for p in pages]

    # Parse footer_styles
    footer_styles = {}
    if footer.footer_styles:
        try:
            footer_styles = json.loads(footer.footer_styles)
        except:
            footer_styles = {}

    return render_template('cms/footer_builder.html', footer=footer, site=site, pages=pages_list, footer_styles=footer_styles)


@bp.route('/footer/<int:footer_id>/save', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def save_footer(footer_id):
    """Save footer content with CSRF protection and sanitization"""
    footer = Footer.query.get_or_404(footer_id)
    data = request.json

    if 'name' in data:
        footer.name = data['name']
    if 'is_active' in data:
        footer.is_active = data['is_active']

    # Sanitize and save widget content
    if 'content' in data:
        sanitized_content = WidgetService.sanitize_widget_array(data['content'])
        footer.content = json.dumps(sanitized_content)

    # Sanitize and save footer styles
    if 'footer_styles' in data:
        from app.utils.security import sanitize_css_properties
        sanitized_styles = sanitize_css_properties(data['footer_styles'])
        footer.footer_styles = json.dumps(sanitized_styles)

    db.session.commit()
    return jsonify({'success': True})


@bp.route('/footer/<int:footer_id>/delete', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def delete_footer(footer_id):
    """Delete a footer with CSRF protection"""
    footer = Footer.query.get_or_404(footer_id)
    site_id = footer.site_id
    db.session.delete(footer)
    db.session.commit()
    return jsonify({'success': True, 'redirect': url_for('cms.site_detail', site_id=site_id)})


# Preview Route

@bp.route('/preview/<int:page_id>')
@login_required
def preview_page(page_id):
    """Preview a page"""
    page = Page.query.get_or_404(page_id)
    site = Site.query.get(page.site_id)

    # Get effective menus and footer (page-specific, inherited, or site default)
    menus_data = MenuService.get_page_menus_and_footer(page, site)

    # Parse page content and styles
    content = json.loads(page.content) if page.content else []
    try:
        page_styles = json.loads(page.page_styles) if page.page_styles else {}
    except (json.JSONDecodeError, TypeError):
        page_styles = {}

    return render_template('preview/page.html',
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
                         footer_styles=menus_data['footer_styles'])


# Builder Menu Mapping Routes

@bp.route('/site/<int:site_id>/builder-menus')
@login_required
def builder_menus(site_id):
    """Manage builder-to-menu mappings for a site"""
    site = Site.query.get_or_404(site_id)
    mappings = BuilderMenuMapping.query.filter_by(site_id=site_id).order_by(BuilderMenuMapping.builder_name).all()
    menus = Menu.query.filter_by(site_id=site_id).all()
    footers = Footer.query.filter_by(site_id=site_id).all()

    # Organize menus by position
    top_menus = [m for m in menus if m.position == 'top']
    left_menus = [m for m in menus if m.position == 'left']
    right_menus = [m for m in menus if m.position == 'right']

    return render_template('cms/builder_menus.html',
                         site=site,
                         mappings=mappings,
                         top_menus=top_menus,
                         left_menus=left_menus,
                         right_menus=right_menus,
                         footers=footers)


@bp.route('/site/<int:site_id>/builder-menus/create', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def create_builder_mapping(site_id):
    """Create a new builder-to-menu mapping (by builder name or role)"""
    site = Site.query.get_or_404(site_id)
    data = request.json

    builder_name = data.get('builder_name', '').strip() if data.get('builder_name') else None
    role = data.get('role')

    # Must have either builder_name or role
    if not builder_name and role is None:
        return jsonify({'success': False, 'error': 'Either builder name or role is required'}), 400

    # Check for duplicates
    if builder_name:
        existing = BuilderMenuMapping.query.filter(
            BuilderMenuMapping.site_id == site_id,
            BuilderMenuMapping.builder_name.isnot(None),
            db.func.lower(BuilderMenuMapping.builder_name) == builder_name.lower()
        ).first()
        if existing:
            return jsonify({'success': False, 'error': 'A mapping for this builder already exists'}), 400
    elif role is not None:
        existing = BuilderMenuMapping.query.filter_by(site_id=site_id, role=int(role)).first()
        if existing:
            return jsonify({'success': False, 'error': 'A mapping for this role already exists'}), 400

    mapping = BuilderMenuMapping(
        site_id=site_id,
        builder_name=builder_name,
        role=int(role) if role is not None else None,
        top_menu_id=data.get('top_menu_id') or None,
        left_menu_id=data.get('left_menu_id') or None,
        right_menu_id=data.get('right_menu_id') or None,
        footer_id=data.get('footer_id') or None
    )
    db.session.add(mapping)
    db.session.commit()

    return jsonify({'success': True, 'mapping_id': mapping.id})


@bp.route('/site/<int:site_id>/builder-menus/<int:mapping_id>', methods=['PUT'])
@login_required
@limiter.limit("30 per minute")
def update_builder_mapping(site_id, mapping_id):
    """Update a builder-to-menu mapping"""
    mapping = BuilderMenuMapping.query.filter_by(id=mapping_id, site_id=site_id).first_or_404()
    data = request.json

    if 'builder_name' in data:
        new_name = data['builder_name'].strip() if data['builder_name'] else None
        if new_name and new_name.lower() != (mapping.builder_name or '').lower():
            # Check for duplicate
            existing = BuilderMenuMapping.query.filter(
                BuilderMenuMapping.site_id == site_id,
                BuilderMenuMapping.id != mapping_id,
                BuilderMenuMapping.builder_name.isnot(None),
                db.func.lower(BuilderMenuMapping.builder_name) == new_name.lower()
            ).first()
            if existing:
                return jsonify({'success': False, 'error': 'A mapping for this builder already exists'}), 400
        mapping.builder_name = new_name

    if 'role' in data:
        new_role = int(data['role']) if data['role'] is not None else None
        if new_role is not None and new_role != mapping.role:
            # Check for duplicate
            existing = BuilderMenuMapping.query.filter(
                BuilderMenuMapping.site_id == site_id,
                BuilderMenuMapping.id != mapping_id,
                BuilderMenuMapping.role == new_role
            ).first()
            if existing:
                return jsonify({'success': False, 'error': 'A mapping for this role already exists'}), 400
        mapping.role = new_role

    if 'top_menu_id' in data:
        mapping.top_menu_id = data['top_menu_id'] or None
    if 'left_menu_id' in data:
        mapping.left_menu_id = data['left_menu_id'] or None
    if 'right_menu_id' in data:
        mapping.right_menu_id = data['right_menu_id'] or None
    if 'footer_id' in data:
        mapping.footer_id = data['footer_id'] or None

    db.session.commit()
    return jsonify({'success': True})


@bp.route('/site/<int:site_id>/builder-menus/<int:mapping_id>', methods=['DELETE'])
@login_required
@limiter.limit("30 per minute")
def delete_builder_mapping(site_id, mapping_id):
    """Delete a builder-to-menu mapping"""
    mapping = BuilderMenuMapping.query.filter_by(id=mapping_id, site_id=site_id).first_or_404()
    db.session.delete(mapping)
    db.session.commit()
    return jsonify({'success': True})
