"""
Production Deployment Script
Runs all necessary database migrations, data migrations, and setup tasks.

Usage:
    python deploy_production.py

This script is idempotent - it can be run multiple times safely.
"""
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from sqlalchemy import inspect, text


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_step(step_num, total_steps, description):
    """Print a step indicator"""
    print(f"\n[{step_num}/{total_steps}] {description}")
    print("-" * 70)


def check_database_tables():
    """Check which tables exist in the database"""
    print_header("DATABASE TABLE STATUS")

    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()

    required_tables = [
        'users', 'sites', 'pages', 'widgets', 'menus', 'menu_items',
        'footers', 'images', 'image_folders'
    ]

    print("\nTable Status:")
    all_exist = True
    for table in required_tables:
        exists = table in existing_tables
        status = "[OK] EXISTS" if exists else "[X] MISSING"
        print(f"  {table:20s} {status}")
        if not exists:
            all_exist = False

    return existing_tables, all_exist


def create_missing_tables():
    """Create all missing database tables"""
    print_header("CREATING DATABASE TABLES")

    inspector = inspect(db.engine)
    existing_tables_before = set(inspector.get_table_names())

    # Create all tables
    db.create_all()

    # Check what was created
    inspector = inspect(db.engine)
    existing_tables_after = set(inspector.get_table_names())

    new_tables = existing_tables_after - existing_tables_before

    if new_tables:
        print("\n[OK] Created new tables:")
        for table in sorted(new_tables):
            print(f"  - {table}")
    else:
        print("\n[OK] All tables already exist")

    return new_tables


def run_column_migrations():
    """Add missing columns to existing tables"""
    print_header("RUNNING COLUMN MIGRATIONS")

    inspector = inspect(db.engine)
    migrations_run = []

    # Check pages table columns
    pages_columns = [col['name'] for col in inspector.get_columns('pages')]

    # Check users table columns
    users_columns = [col['name'] for col in inspector.get_columns('users')]

    migrations = [
        # Pages table migrations
        {
            'table': 'pages',
            'column': 'page_styles',
            'check': 'page_styles' not in pages_columns,
            'sql': 'ALTER TABLE pages ADD COLUMN page_styles TEXT'
        },
        {
            'table': 'pages',
            'column': 'is_homepage',
            'check': 'is_homepage' not in pages_columns,
            'sql': 'ALTER TABLE pages ADD COLUMN is_homepage BOOLEAN DEFAULT 0'
        },
        {
            'table': 'pages',
            'column': 'top_menu_id',
            'check': 'top_menu_id' not in pages_columns,
            'sql': 'ALTER TABLE pages ADD COLUMN top_menu_id INTEGER'
        },
        {
            'table': 'pages',
            'column': 'left_menu_id',
            'check': 'left_menu_id' not in pages_columns,
            'sql': 'ALTER TABLE pages ADD COLUMN left_menu_id INTEGER'
        },
        {
            'table': 'pages',
            'column': 'right_menu_id',
            'check': 'right_menu_id' not in pages_columns,
            'sql': 'ALTER TABLE pages ADD COLUMN right_menu_id INTEGER'
        },
        {
            'table': 'pages',
            'column': 'footer_id',
            'check': 'footer_id' not in pages_columns,
            'sql': 'ALTER TABLE pages ADD COLUMN footer_id INTEGER'
        },
        # Users table migrations (password reset tokens)
        # Note: reset_token column added without UNIQUE - index created separately for SQLite compatibility
        {
            'table': 'users',
            'column': 'reset_token',
            'check': 'reset_token' not in users_columns,
            'sql': 'ALTER TABLE users ADD COLUMN reset_token VARCHAR(100)'
        },
        {
            'table': 'users',
            'column': 'reset_token_expires',
            'check': 'reset_token_expires' not in users_columns,
            'sql': 'ALTER TABLE users ADD COLUMN reset_token_expires DATETIME'
        }
    ]

    for migration in migrations:
        if migration['check']:
            try:
                db.session.execute(text(migration['sql']))
                db.session.commit()
                print(f"[OK] Added column: {migration['table']}.{migration['column']}")
                migrations_run.append(f"{migration['table']}.{migration['column']}")
            except Exception as e:
                print(f"[X] Failed to add {migration['table']}.{migration['column']}: {e}")
                db.session.rollback()

    # Create unique index for reset_token (SQLite doesn't allow UNIQUE in ALTER TABLE)
    if 'reset_token' not in users_columns:
        try:
            db.session.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_users_reset_token ON users(reset_token)'))
            db.session.commit()
            print("[OK] Created unique index on users.reset_token")
        except Exception as e:
            print(f"[X] Failed to create index: {e}")
            db.session.rollback()

    if not migrations_run:
        print("\n[OK] All columns already exist")
    else:
        print(f"\n[OK] Added {len(migrations_run)} column(s)")

    return migrations_run


def create_default_admin_user():
    """Create default admin user if no users exist"""
    print_header("CHECKING ADMIN USER")

    from app.models.user import User

    user_count = User.query.count()

    if user_count == 0:
        print("\n! No users found - creating default admin user")
        print("  Username: admin")
        print("  Password: admin")
        print("  WARNING:  CHANGE THIS PASSWORD IMMEDIATELY!")

        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()

        print("\n[OK] Default admin user created")
        return True
    else:
        print(f"\n[OK] Users exist ({user_count} user(s))")
        return False


def migrate_existing_images():
    """Migrate existing uploaded images to database"""
    print_header("MIGRATING EXISTING IMAGES")

    from app.models.image import Image
    from migrations.migrate_existing_images import get_mime_type, get_image_dimensions

    upload_folder = current_app.config['UPLOAD_FOLDER']

    if not os.path.exists(upload_folder):
        print(f"\n! Upload folder does not exist: {upload_folder}")
        print("  Creating folder...")
        os.makedirs(upload_folder, exist_ok=True)
        print("[OK] Folder created")
        print("[OK] No images to migrate")
        return 0

    # Get all image files in upload folder
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}
    disk_files = []

    for filename in os.listdir(upload_folder):
        filepath = os.path.join(upload_folder, filename)
        if os.path.isfile(filepath):
            ext = os.path.splitext(filename)[1].lower()
            if ext in valid_extensions:
                disk_files.append(filename)

    print(f"\nFound {len(disk_files)} image file(s) on disk")

    # Get existing filenames in database
    existing_filenames = set(img.filename for img in Image.query.all())
    print(f"Found {len(existing_filenames)} image(s) in database")

    # Find files not in database
    new_files = [f for f in disk_files if f not in existing_filenames]

    if not new_files:
        print("\n[OK] No new images to migrate")
        return 0

    print(f"\nMigrating {len(new_files)} new image(s)...")

    migrated = 0
    errors = 0

    for filename in new_files:
        try:
            filepath = os.path.join(upload_folder, filename)

            # Get file stats
            file_stats = os.stat(filepath)
            file_size = file_stats.st_size
            uploaded_at = datetime.fromtimestamp(file_stats.st_mtime)

            # Get MIME type
            mime_type = get_mime_type(filepath)

            # Get dimensions
            width, height = get_image_dimensions(filepath)

            # Generate URL
            url = f"/static/uploads/{filename}"

            # Create Image record
            image = Image(
                filename=filename,
                original_filename=filename,
                url=url,
                file_size=file_size,
                width=width,
                height=height,
                mime_type=mime_type,
                uploaded_by=None,
                uploaded_at=uploaded_at,
                folder_id=None,
                tags='[]'
            )

            db.session.add(image)
            db.session.commit()

            migrated += 1
            print(f"  [OK] {filename} ({file_size} bytes)")

        except Exception as e:
            print(f"  [X] {filename}: {e}")
            errors += 1
            db.session.rollback()

    print(f"\n[OK] Migrated {migrated} image(s)")
    if errors > 0:
        print(f"[X] {errors} error(s)")

    return migrated


def verify_uploads_folder():
    """Ensure uploads folder exists and is writable"""
    print_header("VERIFYING UPLOADS FOLDER")

    upload_folder = current_app.config['UPLOAD_FOLDER']

    # Create if doesn't exist
    if not os.path.exists(upload_folder):
        print(f"\n! Folder does not exist: {upload_folder}")
        os.makedirs(upload_folder, exist_ok=True)
        print("[OK] Created uploads folder")
    else:
        print(f"\n[OK] Folder exists: {upload_folder}")

    # Check if writable
    test_file = os.path.join(upload_folder, '.write_test')
    try:
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("[OK] Folder is writable")
    except Exception as e:
        print(f"[X] Folder is not writable: {e}")
        return False

    return True


def print_summary(results):
    """Print deployment summary"""
    print_header("DEPLOYMENT SUMMARY")

    print(f"\nDeployment completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nChanges made:")

    total_changes = 0

    if results['new_tables']:
        print(f"\n  Database Tables Created: {len(results['new_tables'])}")
        for table in sorted(results['new_tables']):
            print(f"    - {table}")
        total_changes += len(results['new_tables'])

    if results['columns_added']:
        print(f"\n  Database Columns Added: {len(results['columns_added'])}")
        for col in results['columns_added']:
            print(f"    - {col}")
        total_changes += len(results['columns_added'])

    if results['admin_created']:
        print(f"\n  WARNING:  Default Admin User Created")
        print(f"    Username: admin")
        print(f"    Password: admin")
        print(f"    CHANGE THIS PASSWORD IMMEDIATELY!")
        total_changes += 1

    if results['images_migrated'] > 0:
        print(f"\n  Images Migrated: {results['images_migrated']}")
        total_changes += results['images_migrated']

    if total_changes == 0:
        print("\n  [OK] No changes needed - system is up to date")
    else:
        print(f"\n[OK] Total changes: {total_changes}")

    print("\nNext steps:")
    if results['admin_created']:
        print("  1. Log in with username 'admin' and password 'admin'")
        print("  2. IMMEDIATELY change the admin password")
        print("  3. Create additional user accounts as needed")
    else:
        print("  1. Restart your Flask application")
        print("  2. Verify all features are working correctly")
        print("  3. Check the Images page to see migrated images")

    print("\n" + "=" * 70)


def main():
    """Main deployment function"""
    print("\n")
    print("+" + "=" * 68 + "+")
    print("|" + " " * 68 + "|")
    print("|" + "  PageCraft - Production Deployment Script".center(68) + "|")
    print("|" + " " * 68 + "|")
    print("+" + "=" * 68 + "+")

    results = {
        'new_tables': set(),
        'columns_added': [],
        'admin_created': False,
        'images_migrated': 0
    }

    try:
        # Step 1: Check database status
        print_step(1, 6, "Checking Database Tables")
        existing_tables, all_exist = check_database_tables()

        # Step 2: Create missing tables
        print_step(2, 6, "Creating Missing Tables")
        new_tables = create_missing_tables()
        results['new_tables'] = new_tables

        # Step 3: Run column migrations
        print_step(3, 6, "Adding Missing Columns")
        columns_added = run_column_migrations()
        results['columns_added'] = columns_added

        # Step 4: Create default admin if needed
        print_step(4, 6, "Setting Up Admin User")
        admin_created = create_default_admin_user()
        results['admin_created'] = admin_created

        # Step 5: Verify uploads folder
        print_step(5, 6, "Verifying Uploads Folder")
        verify_uploads_folder()

        # Step 6: Migrate existing images
        print_step(6, 6, "Migrating Existing Images")
        images_migrated = migrate_existing_images()
        results['images_migrated'] = images_migrated

        # Print summary
        print_summary(results)

        print("\n[OK] Deployment completed successfully!\n")
        return 0

    except KeyboardInterrupt:
        print("\n\n[X] Deployment cancelled by user")
        return 1
    except Exception as e:
        print(f"\n\n[X] Deployment failed with error:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    # Create Flask app context
    app = create_app()
    current_app = app

    with app.app_context():
        exit_code = main()
        sys.exit(exit_code)
