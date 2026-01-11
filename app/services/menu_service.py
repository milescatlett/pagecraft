"""Menu service for menu/footer resolution and inheritance"""
import json
from app.models.menu import Menu, MenuItem
from app.models.footer import Footer


class MenuService:
    """Service for handling menu and footer operations"""

    @staticmethod
    def get_page_menus_and_footer(page, site):
        """
        Get effective menus and footer for a page, considering page overrides and parent inheritance.

        Args:
            page (Page): Page object
            site (Site): Site object

        Returns:
            dict: Dictionary with menu/footer objects and their parsed content/styles
        """
        result = {
            'top_menu': None, 'top_menu_items': [], 'top_menu_content': [], 'top_menu_styles': {},
            'left_menu': None, 'left_menu_items': [], 'left_menu_content': [], 'left_menu_styles': {},
            'right_menu': None, 'right_menu_items': [], 'right_menu_content': [], 'right_menu_styles': {},
            'footer': None, 'footer_content': [], 'footer_styles': {}
        }

        # Get effective menus (page-specific or inherited from parent, then site default)
        for position in ['top', 'left', 'right']:
            menu = page.get_effective_menu(position)
            if menu == 0:
                # Explicitly no menu - don't fall back to site default
                continue
            if not menu:
                # Fall back to site-wide active menu
                menu = Menu.query.filter_by(site_id=site.id, is_active=True, position=position).first()

            if menu:
                result[f'{position}_menu'] = menu
                result[f'{position}_menu_items'] = MenuItem.query.filter_by(menu_id=menu.id).order_by(MenuItem.order).all()
                result[f'{position}_menu_content'] = json.loads(menu.content) if menu.content else []
                try:
                    result[f'{position}_menu_styles'] = json.loads(menu.menu_styles) if menu.menu_styles else {}
                except (json.JSONDecodeError, TypeError):
                    result[f'{position}_menu_styles'] = {}

        # Get effective footer (page-specific or inherited from parent, then site default)
        footer = page.get_effective_footer()
        if footer == 0:
            # Explicitly no footer - don't fall back to site default
            footer = None
        elif not footer:
            footer = Footer.query.filter_by(site_id=site.id, is_active=True).first()

        if footer:
            result['footer'] = footer
            result['footer_content'] = json.loads(footer.content) if footer.content else []
            try:
                result['footer_styles'] = json.loads(footer.footer_styles) if footer.footer_styles else {}
            except (json.JSONDecodeError, TypeError):
                result['footer_styles'] = {}

        return result
