"""Update database schema to add published column to pages table"""
from app import app, db

with app.app_context():
    try:
        with db.engine.connect() as conn:
            # Add published column to pages table
            try:
                conn.execute(db.text("ALTER TABLE pages ADD COLUMN published BOOLEAN DEFAULT 0"))
                conn.commit()
                print("Added published column to pages table")
            except Exception as e:
                if "duplicate column name" in str(e).lower():
                    print("published column already exists in pages table")
                else:
                    print(f"Error adding published column: {e}")
        print("\nDatabase updated successfully!")
    except Exception as e:
        print(f"Error updating database: {e}")
