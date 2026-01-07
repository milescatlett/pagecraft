"""
Clean corrupted page_styles in the database
"""
from app import app
from models import Page
from database import db

def main():
    with app.app_context():
        pages = Page.query.all()

        for page in pages:
            print(f"\nPage: {page.title}")
            print(f"  Current page_styles: {repr(page.page_styles)}")

            # Reset to empty JSON object
            page.page_styles = '{}'
            print("  Reset to: {}")

        db.session.commit()
        print("\n[SUCCESS] All page styles have been reset")

if __name__ == '__main__':
    main()
