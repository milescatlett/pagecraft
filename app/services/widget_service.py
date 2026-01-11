"""Widget service for sanitization and validation"""
from app.utils.security import sanitize_html_content, sanitize_css_properties


class WidgetService:
    """Service for handling widget content sanitization and validation"""

    @staticmethod
    def sanitize_widget_array(widgets):
        """
        Recursively sanitize all widgets in an array.
        Sanitizes HTML content and CSS styles.

        Args:
            widgets (list): Array of widget dictionaries

        Returns:
            list: Sanitized widget array
        """
        if not isinstance(widgets, list):
            return []

        sanitized = []
        for widget in widgets:
            sanitized_widget = WidgetService.sanitize_widget(widget)
            if sanitized_widget:
                sanitized.append(sanitized_widget)

        return sanitized

    @staticmethod
    def sanitize_widget(widget):
        """
        Sanitize a single widget.

        Args:
            widget (dict): Widget dictionary

        Returns:
            dict: Sanitized widget
        """
        if not isinstance(widget, dict):
            return None

        sanitized = widget.copy()

        # Sanitize widget content based on type
        widget_type = widget.get('type', '')

        # For richtext and html widgets, sanitize the HTML content
        if widget_type in ['richtext', 'html']:
            content = widget.get('content', '')
            if content:
                sanitized['content'] = sanitize_html_content(content)

        # For heading widgets, sanitize content (may contain HTML)
        elif widget_type == 'heading':
            content = widget.get('content', '')
            if content:
                # Headings shouldn't have complex HTML, but sanitize anyway
                sanitized['content'] = sanitize_html_content(content)

        # For card widgets, sanitize title and content
        elif widget_type == 'card':
            if widget.get('title'):
                sanitized['title'] = sanitize_html_content(widget['title'])
            if widget.get('content'):
                sanitized['content'] = sanitize_html_content(widget['content'])

        # For accordion, sanitize each item
        elif widget_type == 'accordion':
            if 'items' in widget and isinstance(widget['items'], list):
                sanitized['items'] = []
                for item in widget['items']:
                    if isinstance(item, dict):
                        sanitized_item = {
                            'title': sanitize_html_content(item.get('title', '')),
                            'content': sanitize_html_content(item.get('content', '')),
                            'expanded': item.get('expanded', False)
                        }
                        sanitized['items'].append(sanitized_item)

        # For tabs, sanitize each tab
        elif widget_type == 'tabs':
            if 'tabs' in widget and isinstance(widget['tabs'], list):
                sanitized['tabs'] = []
                for tab in widget['tabs']:
                    if isinstance(tab, dict):
                        sanitized_tab = {
                            'title': sanitize_html_content(tab.get('title', '')),
                            'content': sanitize_html_content(tab.get('content', '')),
                            'active': tab.get('active', False)
                        }
                        sanitized['tabs'].append(sanitized_tab)

        # For alert and collapse widgets
        elif widget_type in ['alert', 'collapse']:
            if widget.get('content'):
                sanitized['content'] = sanitize_html_content(widget['content'])

        # Sanitize CSS styles for all widgets
        if 'styles' in widget:
            sanitized['styles'] = sanitize_css_properties(widget['styles'])

        # Recursively sanitize children (for row/column widgets)
        if 'children' in widget and isinstance(widget['children'], list):
            sanitized['children'] = WidgetService.sanitize_widget_array(widget['children'])

        # Sanitize dropdown items for button and link widgets
        if 'dropdownItems' in widget and isinstance(widget['dropdownItems'], list):
            sanitized['dropdownItems'] = []
            for item in widget['dropdownItems']:
                if isinstance(item, dict):
                    sanitized_item = item.copy()
                    # Text fields might contain HTML
                    if 'text' in sanitized_item:
                        sanitized_item['text'] = sanitize_html_content(sanitized_item['text'])
                    # Sanitize nested items
                    if 'nestedItems' in sanitized_item and isinstance(sanitized_item['nestedItems'], list):
                        sanitized_item['nestedItems'] = [
                            {
                                'text': sanitize_html_content(nested.get('text', '')),
                                'url': nested.get('url', '')
                            }
                            for nested in sanitized_item['nestedItems']
                            if isinstance(nested, dict)
                        ]
                    sanitized['dropdownItems'].append(sanitized_item)

        return sanitized

    @staticmethod
    def validate_widget_structure(widget, max_depth=10, current_depth=0):
        """
        Validate widget structure to prevent deeply nested objects (DoS).

        Args:
            widget (dict): Widget to validate
            max_depth (int): Maximum nesting depth
            current_depth (int): Current depth

        Returns:
            bool: True if valid
        """
        if current_depth > max_depth:
            return False

        if not isinstance(widget, dict):
            return False

        # Check required fields
        if 'type' not in widget:
            return False

        # Recursively check children
        if 'children' in widget:
            if not isinstance(widget['children'], list):
                return False
            for child in widget['children']:
                if not WidgetService.validate_widget_structure(child, max_depth, current_depth + 1):
                    return False

        return True
