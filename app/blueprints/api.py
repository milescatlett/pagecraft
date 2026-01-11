"""API blueprint for file uploads and Caspio integration"""
import os
from flask import Blueprint, request, jsonify, current_app

# Optional magic import for file type detection
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
from flask_login import login_required, current_user
from app.extensions import limiter
from app.services.upload_service import UploadService
from app.services.image_service import ImageService
from caspio import caspio_api

bp = Blueprint('api', __name__)


def _get_mime_from_extension(filename):
    """Get MIME type from file extension (fallback when magic is not available)"""
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    mime_map = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'svg': 'image/svg+xml',
        'bmp': 'image/bmp',
        'ico': 'image/x-icon'
    }
    return mime_map.get(ext, 'application/octet-stream')


@bp.route('/upload', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def upload():
    """
    Upload image file with CSRF protection and validation.
    Uses magic bytes validation and admin-only SVG uploads.
    Creates Image database record with metadata.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    folder_id = request.form.get('folder_id')  # Optional folder

    # Save original filename before upload
    original_filename = file.filename

    # Use upload service for validation and saving
    success, result = UploadService.save_uploaded_file(file, current_user)

    if success:
        # result is the URL
        # Extract filename from URL
        filename = os.path.basename(result)

        # Get file size
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file_size = os.path.getsize(filepath)

        # Get MIME type using magic bytes (if available) or extension
        if MAGIC_AVAILABLE:
            with open(filepath, 'rb') as f:
                header = f.read(2048)
                try:
                    mime_type = magic.from_buffer(header, mime=True)
                except Exception:
                    # Fall back to extension-based MIME type
                    mime_type = _get_mime_from_extension(filename)
        else:
            # Use extension-based MIME type
            mime_type = _get_mime_from_extension(filename)

        # Create Image record
        try:
            image = ImageService.create_image_record(
                filename=filename,
                original_filename=original_filename,
                url=result,
                file_size=file_size,
                mime_type=mime_type,
                user_id=current_user.id,
                folder_id=int(folder_id) if folder_id else None
            )

            return jsonify({
                'success': True,
                'url': result,
                'image_id': image.id
            })
        except Exception as e:
            current_app.logger.error(f"Failed to create Image record: {e}")
            # Still return success since file was uploaded
            return jsonify({'success': True, 'url': result})
    else:
        return jsonify({'success': False, 'error': result}), 400


@bp.route('/images/list', methods=['GET'])
@login_required
def images_list():
    """List all uploaded images"""
    files = UploadService.list_uploaded_files()
    return jsonify({'success': True, 'images': files})


@bp.route('/caspio/datapages', methods=['GET'])
@login_required
def caspio_datapages():
    """Get Caspio datapages organized by app and folder"""
    try:
        result = caspio_api.get_datapages()
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'configured': caspio_api.is_configured(),
            'error': str(e)
        }), 500


@bp.route('/caspio/status', methods=['GET'])
@login_required
def caspio_status():
    """Check if Caspio is configured"""
    is_configured = caspio_api.is_configured()
    result = {
        'configured': is_configured,
        'account_id': caspio_api.account_id if is_configured else None
    }
    return jsonify(result)


# ===== IMAGE MANAGEMENT ROUTES =====

@bp.route('/images', methods=['GET'])
@login_required
def images():
    """
    List images with filtering, search, and pagination.

    Query params:
    - folder_id: Filter by folder (use 'root' for root folder)
    - tags: Comma-separated tag list (OR logic)
    - search: Search in original_filename
    - sort: uploaded_at, file_size, original_filename (default: uploaded_at)
    - order: asc, desc (default: desc)
    - page: Page number (default: 1)
    - per_page: Items per page (default: 50, max: 200)
    """
    from app.models.image import Image
    from sqlalchemy import or_

    # Parse query params
    folder_id = request.args.get('folder_id')
    tags_str = request.args.get('tags', '')
    search = request.args.get('search', '').strip()
    sort_by = request.args.get('sort', 'uploaded_at')
    order = request.args.get('order', 'desc')
    page = int(request.args.get('page', 1))
    per_page = min(int(request.args.get('per_page', 50)), 200)

    # Build query
    query = Image.query

    # Filter by folder
    if folder_id == 'root':
        query = query.filter_by(folder_id=None)
    elif folder_id:
        query = query.filter_by(folder_id=int(folder_id))

    # Filter by tags (OR logic)
    if tags_str:
        tags = [t.strip().lower() for t in tags_str.split(',')]
        tag_filters = [Image.tags.like(f'%"{tag}"%') for tag in tags]
        query = query.filter(or_(*tag_filters))

    # Search in filename
    if search:
        query = query.filter(Image.original_filename.like(f'%{search}%'))

    # Sort
    sort_column = getattr(Image, sort_by, Image.uploaded_at)
    if order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Serialize images
    images_data = [img.to_dict() for img in pagination.items]

    return jsonify({
        'success': True,
        'images': images_data,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    })


@bp.route('/images/<int:image_id>', methods=['GET'])
@login_required
def image_detail(image_id):
    """Get image details including usage locations"""
    from app.models.image import Image

    image = Image.query.get_or_404(image_id)
    usage = ImageService.find_image_usage(image.url)

    image_data = image.to_dict()
    image_data['usage'] = usage

    return jsonify({
        'success': True,
        'image': image_data
    })


@bp.route('/images/<int:image_id>', methods=['PUT'])
@login_required
@limiter.limit("30 per minute")
def image_update(image_id):
    """Update image metadata (tags, folder)"""
    data = request.json

    # Update tags
    if 'tags' in data:
        success, error = ImageService.update_tags(image_id, data['tags'])
        if not success:
            return jsonify({'success': False, 'error': error}), 400

    # Move to folder
    if 'folder_id' in data:
        folder_id = data['folder_id'] if data['folder_id'] != 'root' else None
        success, error = ImageService.move_to_folder(image_id, folder_id)
        if not success:
            return jsonify({'success': False, 'error': error}), 400

    return jsonify({'success': True})


@bp.route('/images/<int:image_id>', methods=['DELETE'])
@login_required
@limiter.limit("30 per minute")
def image_delete(image_id):
    """Delete image (only if not in use)"""
    success, error = ImageService.delete_image(image_id)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 400


@bp.route('/images/<int:image_id>/crop', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def image_crop(image_id):
    """Create a cropped copy of an image"""
    data = request.json

    # Validate crop data
    required_fields = ['x', 'y', 'width', 'height']
    if not all(field in data for field in required_fields):
        return jsonify({
            'success': False,
            'error': 'Missing crop coordinates'
        }), 400

    success, result = ImageService.crop_image(image_id, data)

    if success:
        # result is the new Image object
        return jsonify({
            'success': True,
            'image': result.to_dict()
        })
    else:
        # result is the error message
        return jsonify({
            'success': False,
            'error': result
        }), 400


# ===== FOLDER MANAGEMENT ROUTES =====

@bp.route('/images/folders', methods=['GET'])
@login_required
def folders_list():
    """Get folder tree"""
    from app.services.image_service import FolderService

    tree = FolderService.get_folder_tree()

    return jsonify({
        'success': True,
        'folders': tree
    })


@bp.route('/images/folders', methods=['POST'])
@login_required
@limiter.limit("30 per minute")
def folder_create():
    """Create new folder"""
    from app.services.image_service import FolderService

    data = request.json
    name = data.get('name', '').strip()
    parent_id = data.get('parent_id')

    if not name:
        return jsonify({'success': False, 'error': 'Name required'}), 400

    folder, error = FolderService.create_folder(name, parent_id)

    if folder:
        return jsonify({
            'success': True,
            'folder': folder.to_dict()
        })
    else:
        return jsonify({'success': False, 'error': error}), 400


@bp.route('/images/folders/<int:folder_id>', methods=['PUT'])
@login_required
@limiter.limit("30 per minute")
def folder_update(folder_id):
    """Rename folder"""
    from app.services.image_service import FolderService

    data = request.json
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Name required'}), 400

    success, error = FolderService.rename_folder(folder_id, name)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 400


@bp.route('/images/folders/<int:folder_id>', methods=['DELETE'])
@login_required
@limiter.limit("30 per minute")
def folder_delete(folder_id):
    """Delete folder"""
    from app.services.image_service import FolderService

    # Get move_images param (default True)
    move_images = request.args.get('move_images', 'true').lower() == 'true'

    success, error = FolderService.delete_folder(folder_id, move_images)

    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': error}), 400


# ===== UTILITY ROUTES =====

@bp.route('/images/tags', methods=['GET'])
@login_required
def tags_list():
    """Get all unique tags for autocomplete"""
    tags = ImageService.get_all_tags()

    return jsonify({
        'success': True,
        'tags': tags
    })


@bp.route('/images/orphans', methods=['GET'])
@login_required
def images_orphans():
    """Find orphaned images (files on disk not in DB)"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Admin only'}), 403

    orphans = ImageService.get_orphaned_images()

    return jsonify({
        'success': True,
        'orphans': orphans
    })
