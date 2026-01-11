"""Page service for page operations"""
import json
from app.extensions import db
from app.models.page import Page
from app.services.widget_service import WidgetService
from app.utils.validators import validate_page_data, validate_json_structure


class PageService:
    """Service for handling page-related operations"""

    @staticmethod
    def create_page(site_id, title, slug, parent_id=None, **kwargs):
        """
        Create a new page with validation.

        Args:
            site_id (int): Site ID
            title (str): Page title
            slug (str): Page slug
            parent_id (int, optional): Parent page ID
            **kwargs: Additional page attributes

        Returns:
            tuple: (page, error_message)
        """
        # Validate page data
        is_valid, error = validate_page_data({'title': title, 'slug': slug})
        if not is_valid:
            return None, error

        page = Page(
            site_id=site_id,
            title=title,
            slug=slug,
            parent_id=parent_id,
            **kwargs
        )

        db.session.add(page)
        try:
            db.session.commit()
            return page, None
        except Exception as e:
            db.session.rollback()
            return None, str(e)

    @staticmethod
    def update_page_content(page_id, content_data):
        """
        Update page content with sanitization.

        Args:
            page_id (int): Page ID
            content_data (list): Widget array

        Returns:
            tuple: (success, error_message)
        """
        page = Page.query.get(page_id)
        if not page:
            return False, "Page not found"

        # Validate JSON structure
        if not validate_json_structure(content_data, max_depth=10):
            return False, "Content structure too deeply nested"

        # Sanitize widget content
        sanitized_content = WidgetService.sanitize_widget_array(content_data)

        # Save as JSON
        page.content = json.dumps(sanitized_content)

        try:
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def update_page_styles(page_id, styles):
        """
        Update page styles with sanitization.

        Args:
            page_id (int): Page ID
            styles (dict): Page styles dictionary

        Returns:
            tuple: (success, error_message)
        """
        from app.utils.security import sanitize_css_properties

        page = Page.query.get(page_id)
        if not page:
            return False, "Page not found"

        # Sanitize CSS properties
        sanitized_styles = sanitize_css_properties(styles)

        # Save as JSON
        page.page_styles = json.dumps(sanitized_styles)

        try:
            db.session.commit()
            return True, None
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @staticmethod
    def copy_page(page_id, include_children=False):
        """
        Copy a page and optionally its children.

        Args:
            page_id (int): Page ID to copy
            include_children (bool): Whether to copy child pages

        Returns:
            Page: Copied page or None
        """
        original = Page.query.get(page_id)
        if not original:
            return None

        def copy_page_recursive(source_page, new_parent_id=None):
            """Recursively copy a page and its children"""
            # Create copy
            new_page = Page(
                site_id=source_page.site_id,
                parent_id=new_parent_id,
                title=f"{source_page.title} (Copy)",
                slug=f"{source_page.slug}-copy",
                content=source_page.content,
                page_styles=source_page.page_styles,
                published=False,  # Don't publish copies by default
                top_menu_id=source_page.top_menu_id,
                left_menu_id=source_page.left_menu_id,
                right_menu_id=source_page.right_menu_id,
                footer_id=source_page.footer_id
            )
            db.session.add(new_page)
            db.session.flush()  # Get ID without committing

            # Copy children if requested
            if include_children and source_page.children:
                for child in source_page.children:
                    copy_page_recursive(child, new_page.id)

            return new_page

        try:
            new_page = copy_page_recursive(original)
            db.session.commit()
            return new_page
        except Exception:
            db.session.rollback()
            return None
