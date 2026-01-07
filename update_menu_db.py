"""Update database schema to add content column to menus table"""
from app import app, db

with app.app_context():
    try:
        with db.engine.connect() as conn:
            # Add content column to menus table
            try:
                conn.execute(db.text("ALTER TABLE menus ADD COLUMN content TEXT"))
                conn.commit()
                print("Added content column to menus table")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("content column already exists in menus table")
                else:
                    print(f"Error adding content column: {e}")

        print("\nDatabase updated successfully!")
    except Exception as e:
        print(f"Error updating database: {e}")
