"""Fix over-encoded menu_styles in database"""
from app import app, Menu
import json

def main():
    with app.app_context():
        menus = Menu.query.all()

        for menu in menus:
            print(f"\nMenu {menu.id} ({menu.name}):")
            print(f"  Current menu_styles: {repr(menu.menu_styles)[:100]}...")

            # Reset to empty JSON object
            menu.menu_styles = '{}'
            print("  Reset to: {}")

        from database import db
        db.session.commit()
        print("\n[SUCCESS] All menu styles have been reset")
        print("You can now set your menu styles again and they will save properly!")

if __name__ == '__main__':
    main()
