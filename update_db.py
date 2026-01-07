"""Update database schema to add styling columns"""
from app import app, db
from models import Page, Menu, Footer

with app.app_context():
    # Add columns manually using raw SQL since SQLite doesn't support ALTER TABLE fully
    try:
        with db.engine.connect() as conn:
            # Add page_styles column to pages table
            try:
                conn.execute(db.text("ALTER TABLE pages ADD COLUMN page_styles TEXT"))
                conn.commit()
                print("Added page_styles column to pages table")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("page_styles column already exists in pages table")
                else:
                    print(f"Error adding page_styles: {e}")

            # Add menu_styles column to menus table
            try:
                conn.execute(db.text("ALTER TABLE menus ADD COLUMN menu_styles TEXT"))
                conn.commit()
                print("Added menu_styles column to menus table")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("menu_styles column already exists in menus table")
                else:
                    print(f"Error adding menu_styles: {e}")

            # Add footer_styles column to footers table
            try:
                conn.execute(db.text("ALTER TABLE footers ADD COLUMN footer_styles TEXT"))
                conn.commit()
                print("Added footer_styles column to footers table")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("footer_styles column already exists in footers table")
                else:
                    print(f"Error adding footer_styles: {e}")

        print("\nDatabase updated successfully!")
    except Exception as e:
        print(f"Error updating database: {e}")
