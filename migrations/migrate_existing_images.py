"""
Migration script to import existing uploaded images into the Image database table.

This script scans the static/uploads/ directory and creates Image records for
any files that don't already have database entries.

Usage:
    python migrations/migrate_existing_images.py
"""
import os
import sys
import json
from datetime import datetime

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.image import Image


def get_mime_type(filepath):
    """Get MIME type from file extension or magic bytes"""
    try:
        import magic
        with open(filepath, 'rb') as f:
            header = f.read(2048)
            return magic.from_buffer(header, mime=True)
    except ImportError:
        # Fallback to extension-based detection
        ext = os.path.splitext(filepath)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml',
            '.bmp': 'image/bmp',
            '.ico': 'image/x-icon'
        }
        return mime_types.get(ext, 'application/octet-stream')


def get_image_dimensions(filepath):
    """Extract image dimensions using PIL"""
    try:
        from PIL import Image as PILImage
        with PILImage.open(filepath) as img:
            return img.size  # Returns (width, height)
    except Exception as e:
        print(f"  Warning: Could not extract dimensions: {e}")
        return None, None


def migrate_images():
    """Main migration function"""
    app = create_app()

    with app.app_context():
        upload_folder = app.config['UPLOAD_FOLDER']

        if not os.path.exists(upload_folder):
            print(f"Upload folder does not exist: {upload_folder}")
            print("Creating folder...")
            os.makedirs(upload_folder, exist_ok=True)
            print("No images to migrate.")
            return

        # Get all files in upload folder
        print(f"Scanning upload folder: {upload_folder}")
        print("-" * 60)

        files = []
        # Image extensions to process
        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.bmp', '.ico'}

        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)
            if os.path.isfile(filepath):
                ext = os.path.splitext(filename)[1].lower()
                if ext in valid_extensions:
                    files.append(filename)

        print(f"Found {len(files)} file(s) on disk")

        # Get existing filenames in database
        existing_filenames = set(img.filename for img in Image.query.all())
        print(f"Found {len(existing_filenames)} image(s) already in database")

        # Find files not in database
        new_files = [f for f in files if f not in existing_filenames]

        if not new_files:
            print("\nNo new images to migrate!")
            return

        print(f"\nMigrating {len(new_files)} new image(s)...")
        print("-" * 60)

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
                    original_filename=filename,  # We don't have the original name
                    url=url,
                    file_size=file_size,
                    width=width,
                    height=height,
                    mime_type=mime_type,
                    uploaded_by=None,  # Unknown uploader
                    uploaded_at=uploaded_at,
                    folder_id=None,  # Root folder
                    tags='[]'  # Empty tags
                )

                db.session.add(image)
                db.session.commit()

                print(f"[OK] Migrated: {filename}")
                print(f"     Size: {file_size} bytes, Dimensions: {width}x{height}, Type: {mime_type}")
                migrated += 1

            except Exception as e:
                print(f"[ERROR] Failed to migrate {filename}: {e}")
                errors += 1
                db.session.rollback()

        # Summary
        print("-" * 60)
        print(f"\nMigration complete!")
        print(f"  Migrated: {migrated}")
        print(f"  Errors: {errors}")
        print(f"  Skipped (already in DB): {len(existing_filenames)}")
        print(f"  Total files on disk: {len(files)}")


if __name__ == '__main__':
    print("=" * 60)
    print("Image Migration Script")
    print("=" * 60)
    print()

    try:
        migrate_images()
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nDone!")
