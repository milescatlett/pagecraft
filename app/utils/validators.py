"""Input validation utilities"""
import magic
import os


def validate_page_data(data):
    """
    Validate page creation/update data.

    Args:
        data (dict): Page data from request

    Returns:
        tuple: (is_valid, error_message)
    """
    title = data.get('title', '').strip()
    slug = data.get('slug', '').strip()

    if not title:
        return False, "Title is required"

    if len(title) > 200:
        return False, "Title must be 200 characters or less"

    if slug and not validate_slug_format(slug):
        return False, "Slug can only contain lowercase letters, numbers, and hyphens"

    return True, None


def validate_slug_format(slug):
    """
    Validate that slug is URL-safe.

    Args:
        slug (str): The slug to validate

    Returns:
        bool: True if valid
    """
    import re
    if not slug:
        return False

    # Slug should only contain lowercase letters, numbers, and hyphens
    # Must not start or end with hyphen
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    return bool(re.match(pattern, slug.lower()))


def validate_json_structure(data, max_depth=10, current_depth=0):
    """
    Validate JSON structure to prevent deeply nested objects (DoS attack).

    Args:
        data: JSON data to validate
        max_depth (int): Maximum nesting depth allowed
        current_depth (int): Current recursion depth

    Returns:
        bool: True if valid depth
    """
    if current_depth > max_depth:
        return False

    if isinstance(data, dict):
        for value in data.values():
            if not validate_json_structure(value, max_depth, current_depth + 1):
                return False
    elif isinstance(data, list):
        for item in data:
            if not validate_json_structure(item, max_depth, current_depth + 1):
                return False

    return True


def validate_file_upload(file, user=None, app_config=None):
    """
    Validate uploaded file for security.
    Checks file type using magic bytes, not just extension.

    Args:
        file: FileStorage object from request
        user: Current user (for permission checks)
        app_config: Flask app config for settings

    Returns:
        tuple: (is_valid, error_message, file_ext)
    """
    if not file or not file.filename:
        return False, "No file provided", None

    # Check file extension
    filename = file.filename.lower()
    if '.' not in filename:
        return False, "File must have an extension", None

    ext = filename.rsplit('.', 1)[1]

    # Get allowed extensions from config or use default
    if app_config and 'ALLOWED_EXTENSIONS' in app_config:
        allowed_extensions = app_config['ALLOWED_EXTENSIONS']
    else:
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

    if ext not in allowed_extensions:
        return False, f"File type .{ext} not allowed", None

    # Special handling for SVG - admin only
    if ext == 'svg':
        if not user or not getattr(user, 'is_admin', False):
            return False, "SVG uploads are restricted to administrators", None

    # Read first 2KB to check magic bytes
    file.seek(0)
    header = file.read(2048)
    file.seek(0)

    try:
        mime_type = magic.from_buffer(header, mime=True)
    except Exception as e:
        return False, f"Could not determine file type: {str(e)}", None

    # Map extensions to expected MIME types
    allowed_mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'svg': 'image/svg+xml'
    }

    expected_mime = allowed_mime_types.get(ext)
    if expected_mime and mime_type != expected_mime:
        # Some tolerance for JPEG variations
        if ext in ['jpg', 'jpeg'] and 'image/jpeg' not in mime_type:
            return False, f"File content doesn't match .{ext} extension", None
        elif ext not in ['jpg', 'jpeg']:
            return False, f"File content doesn't match .{ext} extension", None

    return True, None, ext


def validate_username(username):
    """
    Validate username format.

    Args:
        username (str): Username to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not username:
        return False, "Username is required"

    if len(username) < 3:
        return False, "Username must be at least 3 characters"

    if len(username) > 80:
        return False, "Username must be 80 characters or less"

    # Username should only contain alphanumeric and underscores
    import re
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"

    return True, None


def validate_password(password):
    """
    Validate password strength.

    Args:
        password (str): Password to validate

    Returns:
        tuple: (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 6:
        return False, "Password must be at least 6 characters"

    return True, None
