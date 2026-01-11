"""Menu service for menu/footer resolution and inheritance"""
import json
from app.models.menu import Menu, MenuItem
from app.models.footer import Footer
from app.models.builder_menu import BuilderMenuMapping


class MenuService:
    """Service for handling menu and footer operations"""

    @staticmethod
    def get_page_menus_and_footer(page, site, builder_name=None, role=None):
        """
        Get effective menus and footer for a page, considering:
        1. User-specific menu mappings (from Caspio Builder or Role fields)
        2. Page-specific overrides
        3. Parent page inheritance
        4. Site-wide defaults

        Args:
            page (Page): Page object
            site (Site): Site object
            builder_name (str, optional): Builder name from Caspio session
            role (int/str, optional): Role from Caspio session

        Returns:
            dict: Dictionary with menu/footer objects and their parsed content/styles
        """
        result = {
            'top_menu': None, 'top_menu_items': [], 'top_menu_content': [], 'top_menu_styles': {},
            'left_menu': None, 'left_menu_items': [], 'left_menu_content': [], 'left_menu_styles': {},
            'right_menu': None, 'right_menu_items': [], 'right_menu_content': [], 'right_menu_styles': {},
            'footer': None, 'footer_content': [], 'footer_styles': {}
        }

        # Check for user-specific menu mapping (builder takes priority over role)
        user_mapping = None
        if builder_name or role is not None:
            user_mapping = BuilderMenuMapping.get_for_user(site.id, builder_name=builder_name, role=role)

        # Get effective menus (builder-specific, then page-specific, then inherited, then site default)
        for position in ['top', 'left', 'right']:
            menu = None

            # Priority 1: Builder-specific menu (if mapping exists and has a menu for this position)
            if user_mapping:
                menu_id = getattr(user_mapping, f'{position}_menu_id')
                if menu_id:
                    menu = Menu.query.get(menu_id)

            # Priority 2: Page-specific or inherited menu
            if not menu:
                menu = page.get_effective_menu(position)
                if menu == 0:
                    # Explicitly no menu - don't fall back to site default
                    continue

            # Priority 3: Site-wide active menu
            if not menu:
                menu = Menu.query.filter_by(site_id=site.id, is_active=True, position=position).first()

            if menu:
                result[f'{position}_menu'] = menu
                result[f'{position}_menu_items'] = MenuItem.query.filter_by(menu_id=menu.id).order_by(MenuItem.order).all()
                result[f'{position}_menu_content'] = json.loads(menu.content) if menu.content else []
                try:
                    result[f'{position}_menu_styles'] = json.loads(menu.menu_styles) if menu.menu_styles else {}
                except (json.JSONDecodeError, TypeError):
                    result[f'{position}_menu_styles'] = {}

        # Get effective footer (builder-specific, then page-specific, then inherited, then site default)
        footer = None

        # Priority 1: Builder-specific footer
        if user_mapping and user_mapping.footer_id:
            footer = Footer.query.get(user_mapping.footer_id)

        # Priority 2: Page-specific or inherited footer
        if not footer:
            footer = page.get_effective_footer()
            if footer == 0:
                # Explicitly no footer - don't fall back to site default
                footer = None
            elif not footer:
                # Priority 3: Site-wide active footer
                footer = Footer.query.filter_by(site_id=site.id, is_active=True).first()

        if footer:
            result['footer'] = footer
            result['footer_content'] = json.loads(footer.content) if footer.content else []
            try:
                result['footer_styles'] = json.loads(footer.footer_styles) if footer.footer_styles else {}
            except (json.JSONDecodeError, TypeError):
                result['footer_styles'] = {}

        return result
