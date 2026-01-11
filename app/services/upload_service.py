"""Upload service for file handling"""
import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app
from app.utils.validators import validate_file_upload


class UploadService:
    """Service for handling file uploads"""

    @staticmethod
    def save_uploaded_file(file, user):
        """
        Save uploaded file with validation and security checks.

        Args:
            file: FileStorage object from request
            user: Current user object

        Returns:
            tuple: (success, url_or_error_message)
        """
        # Validate file
        is_valid, error, ext = validate_file_upload(
            file,
            user,
            current_app.config
        )

        if not is_valid:
            return False, error

        # Generate secure filename
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4()}.{ext}"

        # Save file
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        filepath = os.path.join(upload_folder, filename)

        try:
            file.save(filepath)
            # Return URL path
            url = f"/static/uploads/{filename}"
            return True, url
        except Exception as e:
            return False, f"Failed to save file: {str(e)}"

    @staticmethod
    def list_uploaded_files():
        """
        List all uploaded files.

        Returns:
            list: List of file URLs
        """
        upload_folder = current_app.config['UPLOAD_FOLDER']

        if not os.path.exists(upload_folder):
            return []

        files = []
        for filename in os.listdir(upload_folder):
            if os.path.isfile(os.path.join(upload_folder, filename)):
                files.append({
                    'name': filename,
                    'url': f"/static/uploads/{filename}"
                })

        return files
