"""Image service for image operations and usage tracking"""
import json
import os
from flask import current_app
from app.extensions import db
from app.models.image import Image, ImageFolder
from app.models.page import Page
from app.models.menu import Menu
from app.models.footer import Footer


class ImageService:
    """Service for handling image-related operations"""

    @staticmethod
    def create_image_record(filename, original_filename, url, file_size,
                            mime_type, user_id, folder_id=None):
        """
        Create database record for uploaded image with metadata extraction.

        Args:
            filename: UUID filename on disk
            original_filename: User's original filename
            url: Full URL path (/static/uploads/...)
            file_size: File size in bytes
            mime_type: MIME type from magic bytes
            user_id: ID of uploading user
            folder_id: Optional folder ID

        Returns:
            Image: Created image object
        """
        # Extract image dimensions using PIL
        width, height = None, None
        filepath = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            filename
        )

        try:
            from PIL import Image as PILImage
            with PILImage.open(filepath) as img:
                width, height = img.size
        except Exception as e:
            current_app.logger.warning(f"Could not extract dimensions: {e}")

        image = Image(
            filename=filename,
            original_filename=original_filename,
            url=url,
            file_size=file_size,
            width=width,
            height=height,
            mime_type=mime_type,
            uploaded_by=user_id,
            folder_id=folder_id,
            tags='[]'  # Empty JSON array
        )

        db.session.add(image)
        db.session.commit()

        return image

    @staticmethod
    def find_image_usage(image_url):
        """
        Find all locations where an image is used.

        Scans:
        - Page.content (widget.src, widget.image, widget.styles.backgroundImage)
        - Page.page_styles (backgroundImage)
        - Menu.content (same widget structure)
        - Menu.menu_styles (backgroundImage)
        - Footer.content (same widget structure)
        - Footer.footer_styles (backgroundImage)

        Args:
            image_url: URL of image to find (e.g., /static/uploads/abc.png)

        Returns:
            list: List of dicts with keys: type, id, name, location, url
        """
        usage = []

        # Helper to recursively scan widget arrays
        def scan_widgets(widgets, entity_type, entity_id, entity_name):
            if not widgets or not isinstance(widgets, list):
                return

            for widget in widgets:
                if not isinstance(widget, dict):
                    continue

                # Check direct image properties
                if widget.get('src') == image_url:
                    usage.append({
                        'type': entity_type,
                        'id': entity_id,
                        'name': entity_name,
                        'location': f"{widget.get('type', 'widget')} src",
                        'url': ImageService._get_edit_url(entity_type, entity_id)
                    })

                if widget.get('image') == image_url:
                    usage.append({
                        'type': entity_type,
                        'id': entity_id,
                        'name': entity_name,
                        'location': f"{widget.get('type', 'card')} image",
                        'url': ImageService._get_edit_url(entity_type, entity_id)
                    })

                # Check widget styles
                if 'styles' in widget and isinstance(widget['styles'], dict):
                    bg_img = widget['styles'].get('backgroundImage', '')
                    if bg_img and image_url in bg_img:  # backgroundImage may be url(...)
                        usage.append({
                            'type': entity_type,
                            'id': entity_id,
                            'name': entity_name,
                            'location': f"{widget.get('type', 'widget')} background",
                            'url': ImageService._get_edit_url(entity_type, entity_id)
                        })

                # Recursively check children (for rows/columns)
                if 'children' in widget and isinstance(widget['children'], list):
                    scan_widgets(widget['children'], entity_type, entity_id, entity_name)

        # Scan all pages
        pages = Page.query.all()
        for page in pages:
            # Check page content
            if page.content:
                try:
                    widgets = json.loads(page.content)
                    scan_widgets(widgets, 'page', page.id, page.title)
                except json.JSONDecodeError:
                    pass

            # Check page styles
            if page.page_styles:
                try:
                    styles = json.loads(page.page_styles)
                    bg_img = styles.get('backgroundImage', '')
                    if bg_img and image_url in bg_img:
                        usage.append({
                            'type': 'page',
                            'id': page.id,
                            'name': page.title,
                            'location': 'page background',
                            'url': ImageService._get_edit_url('page', page.id)
                        })
                except json.JSONDecodeError:
                    pass

        # Scan all menus
        menus = Menu.query.all()
        for menu in menus:
            # Check menu content
            if menu.content:
                try:
                    widgets = json.loads(menu.content)
                    scan_widgets(widgets, 'menu', menu.id, menu.name)
                except json.JSONDecodeError:
                    pass

            # Check menu styles
            if menu.menu_styles:
                try:
                    styles = json.loads(menu.menu_styles)
                    bg_img = styles.get('backgroundImage', '')
                    if bg_img and image_url in bg_img:
                        usage.append({
                            'type': 'menu',
                            'id': menu.id,
                            'name': menu.name,
                            'location': 'menu background',
                            'url': ImageService._get_edit_url('menu', menu.id)
                        })
                except json.JSONDecodeError:
                    pass

        # Scan all footers
        footers = Footer.query.all()
        for footer in footers:
            # Check footer content
            if footer.content:
                try:
                    widgets = json.loads(footer.content)
                    scan_widgets(widgets, 'footer', footer.id, footer.name)
                except json.JSONDecodeError:
                    pass

            # Check footer styles
            if footer.footer_styles:
                try:
                    styles = json.loads(footer.footer_styles)
                    bg_img = styles.get('backgroundImage', '')
                    if bg_img and image_url in bg_img:
                        usage.append({
                            'type': 'footer',
                            'id': footer.id,
                            'name': footer.name,
                            'location': 'footer background',
                            'url': ImageService._get_edit_url('footer', footer.id)
                        })
                except json.JSONDecodeError:
                    pass

        return usage

    @staticmethod
    def _get_edit_url(entity_type, entity_id):
        """Generate edit URL for entity"""
        from flask import url_for

        if entity_type == 'page':
            return url_for('cms.edit_page', page_id=entity_id)
        elif entity_type == 'menu':
            return url_for('cms.edit_menu', menu_id=entity_id)
        elif entity_type == 'footer':
            return url_for('cms.edit_footer', footer_id=entity_id)
        return '#'

    @staticmethod
    def can_delete_image(image_id):
        """
        Check if image can be safely deleted.

        Returns:
            tuple: (can_delete, usage_list)
        """
        image = Image.query.get(image_id)
        if not image:
            return False, []

        usage = ImageService.find_image_usage(image.url)
        return len(usage) == 0, usage

    @staticmethod
    def delete_image(image_id):
        """
        Delete image file and database record with validation.

        Returns:
            tuple: (success, error_message)
        """
        image = Image.query.get(image_id)
        if not image:
            return False, "Image not found"

        # Check if image is in use
        can_delete, usage = ImageService.can_delete_image(image_id)
        if not can_delete:
            return False, f"Image is used in {len(usage)} location(s)"

        # Delete physical file
        filepath = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            image.filename
        )

        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            current_app.logger.error(f"Failed to delete file: {e}")
            return False, "Failed to delete file from disk"

        # Delete database record
        db.session.delete(image)
        db.session.commit()

        return True, None

    @staticmethod
    def move_to_folder(image_id, folder_id):
        """Move image to different folder"""
        image = Image.query.get(image_id)
        if not image:
            return False, "Image not found"

        # Validate folder exists (or is None for root)
        if folder_id is not None:
            folder = ImageFolder.query.get(folder_id)
            if not folder:
                return False, "Folder not found"

        image.folder_id = folder_id
        db.session.commit()

        return True, None

    @staticmethod
    def update_tags(image_id, tags):
        """
        Update image tags.

        Args:
            image_id: Image ID
            tags: List of tag strings
        """
        image = Image.query.get(image_id)
        if not image:
            return False, "Image not found"

        # Validate and clean tags
        clean_tags = []
        for tag in tags:
            tag = tag.strip().lower()
            if tag and len(tag) <= 50:  # Max tag length
                clean_tags.append(tag)

        image.tags = json.dumps(clean_tags)
        db.session.commit()

        return True, None

    @staticmethod
    def get_all_tags():
        """Get all unique tags across all images"""
        all_tags = set()

        images = Image.query.all()
        for image in images:
            if image.tags:
                try:
                    tags = json.loads(image.tags)
                    all_tags.update(tags)
                except json.JSONDecodeError:
                    pass

        return sorted(list(all_tags))

    @staticmethod
    def get_orphaned_images():
        """
        Find images on disk not in database.

        Returns:
            list: List of filenames not in database
        """
        upload_folder = current_app.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            return []

        # Get all files in upload folder
        disk_files = set()
        for filename in os.listdir(upload_folder):
            filepath = os.path.join(upload_folder, filename)
            if os.path.isfile(filepath):
                disk_files.add(filename)

        # Get all filenames in database
        db_files = set(img.filename for img in Image.query.all())

        # Find orphans
        orphans = disk_files - db_files

        return list(orphans)

    @staticmethod
    def crop_image(image_id, crop_data):
        """
        Create a cropped copy of an image.

        Args:
            image_id: Source image ID
            crop_data: Dict with keys: x, y, width, height (all in pixels)

        Returns:
            tuple: (success: bool, result: Image or error_message)
        """
        from PIL import Image as PILImage
        import uuid

        # Get source image
        source_image = Image.query.get(image_id)
        if not source_image:
            return False, "Image not found"

        # Validate crop data
        try:
            x = int(crop_data['x'])
            y = int(crop_data['y'])
            width = int(crop_data['width'])
            height = int(crop_data['height'])

            if width <= 0 or height <= 0:
                return False, "Invalid crop dimensions"
        except (KeyError, ValueError) as e:
            return False, f"Invalid crop data: {e}"

        # Get source file path
        source_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            source_image.filename
        )

        if not os.path.exists(source_path):
            return False, "Source file not found"

        try:
            # Open and crop image
            with PILImage.open(source_path) as img:
                # Validate crop coordinates
                if x < 0 or y < 0 or x + width > img.width or y + height > img.height:
                    return False, "Crop coordinates out of bounds"

                # Crop image
                cropped = img.crop((x, y, x + width, y + height))

                # Generate new filename
                ext = os.path.splitext(source_image.filename)[1]
                new_filename = f"{uuid.uuid4()}{ext}"
                new_path = os.path.join(
                    current_app.config['UPLOAD_FOLDER'],
                    new_filename
                )

                # Save cropped image
                cropped.save(new_path, quality=95, optimize=True)

            # Get new file stats
            file_size = os.path.getsize(new_path)
            new_url = f"/static/uploads/{new_filename}"

            # Determine MIME type
            mime_type = source_image.mime_type

            # Generate original filename
            base_name = os.path.splitext(source_image.original_filename)[0]
            original_filename = f"{base_name}_cropped{ext}"

            # Create new Image record
            new_image = ImageService.create_image_record(
                filename=new_filename,
                original_filename=original_filename,
                url=new_url,
                file_size=file_size,
                mime_type=mime_type,
                user_id=source_image.uploaded_by,
                folder_id=source_image.folder_id
            )

            # Copy tags from source
            if source_image.tags:
                new_image.tags = source_image.tags
                db.session.commit()

            return True, new_image

        except Exception as e:
            current_app.logger.error(f"Error cropping image: {e}")
            return False, f"Failed to crop image: {str(e)}"


class FolderService:
    """Service for managing image folders"""

    @staticmethod
    def create_folder(name, parent_id=None):
        """Create new folder"""
        # Validate parent exists
        if parent_id is not None:
            parent = ImageFolder.query.get(parent_id)
            if not parent:
                return None, "Parent folder not found"

        folder = ImageFolder(name=name, parent_id=parent_id)
        db.session.add(folder)
        db.session.commit()

        return folder, None

    @staticmethod
    def delete_folder(folder_id, move_images_to_root=True):
        """
        Delete folder.

        Args:
            folder_id: Folder ID
            move_images_to_root: If True, move images to root; if False, fail if has images

        Returns:
            tuple: (success, error_message)
        """
        folder = ImageFolder.query.get(folder_id)
        if not folder:
            return False, "Folder not found"

        # Check for images
        image_count = folder.images.count()
        if image_count > 0 and not move_images_to_root:
            return False, f"Folder contains {image_count} image(s)"

        # Move images to root
        if move_images_to_root:
            for image in folder.images:
                image.folder_id = None

        # Move child folders to parent (or root)
        for child in folder.children:
            child.parent_id = folder.parent_id

        db.session.delete(folder)
        db.session.commit()

        return True, None

    @staticmethod
    def rename_folder(folder_id, new_name):
        """Rename folder"""
        folder = ImageFolder.query.get(folder_id)
        if not folder:
            return False, "Folder not found"

        folder.name = new_name
        db.session.commit()

        return True, None

    @staticmethod
    def get_folder_tree():
        """
        Get entire folder tree as nested structure.

        Returns:
            list: List of root folders with nested children
        """
        def build_tree(folder):
            return {
                'id': folder.id,
                'name': folder.name,
                'image_count': folder.images.count(),
                'children': [build_tree(child) for child in folder.children]
            }

        root_folders = ImageFolder.query.filter_by(parent_id=None).all()
        return [build_tree(f) for f in root_folders]
