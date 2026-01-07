"""
Fix accordion widget IDs by removing decimal points from existing widgets
"""
from app import app
from models import Page
from database import db
import json
import re

def fix_widget_ids(widget):
    """Recursively fix widget IDs by replacing decimals with dashes"""
    if isinstance(widget, dict):
        # Fix the widget's own ID
        if 'id' in widget and isinstance(widget['id'], (int, float)):
            # Convert decimal ID to string format with dashes
            old_id = widget['id']
            if isinstance(old_id, float):
                # Convert 1765218369732.9053 to 1765218369732-9053
                widget['id'] = str(old_id).replace('.', '-')
                print(f"  Fixed widget ID: {old_id} -> {widget['id']}")

        # Recursively fix children
        if 'children' in widget and isinstance(widget['children'], list):
            for child in widget['children']:
                fix_widget_ids(child)

    return widget

def main():
    with app.app_context():
        pages = Page.query.all()
        fixed_count = 0

        for page in pages:
            if not page.content:
                continue

            try:
                content = json.loads(page.content)
                modified = False

                print(f"\nChecking page: {page.title}")

                # Fix all widgets in the page
                for widget in content:
                    old_widget = json.dumps(widget)
                    fix_widget_ids(widget)
                    if json.dumps(widget) != old_widget:
                        modified = True

                # Save if modified
                if modified:
                    page.content = json.dumps(content)
                    fixed_count += 1
                    print(f"  [OK] Updated page: {page.title}")

            except Exception as e:
                print(f"  [ERROR] Error processing {page.title}: {e}")

        if fixed_count > 0:
            db.session.commit()
            print(f"\n[SUCCESS] Fixed {fixed_count} page(s)")
        else:
            print("\n[INFO] No pages needed fixing")

if __name__ == '__main__':
    main()
