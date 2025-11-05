"""
Phase H: File Upload Service

Handles file uploads with validation, storage, and naming strategies.
"""

import os
import uuid
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, List
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage


class FileUploadError(Exception):
    """Raised when file upload fails"""
    pass


class FileUploadService:
    """Service for handling file uploads with validation"""

    # File size constants
    KB = 1024
    MB = 1024 * KB
    GB = 1024 * MB

    def __init__(self):
        """Initialize file upload service"""
        self.max_file_size = 10 * self.MB  # Default 10MB
        self.allowed_extensions = None  # None = allow all

    @staticmethod
    def parse_size(size_str: str) -> int:
        """
        Parse file size string like '5MB', '100KB', '1GB' to bytes

        Args:
            size_str: Size string (e.g., '5MB', '100KB')

        Returns:
            Size in bytes
        """
        size_str = size_str.strip().upper()

        if size_str.endswith('GB'):
            return int(float(size_str[:-2]) * FileUploadService.GB)
        elif size_str.endswith('MB'):
            return int(float(size_str[:-2]) * FileUploadService.MB)
        elif size_str.endswith('KB'):
            return int(float(size_str[:-2]) * FileUploadService.KB)
        elif size_str.endswith('B'):
            return int(size_str[:-1])
        else:
            # Assume bytes if no unit
            return int(size_str)

    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension from filename"""
        return Path(filename).suffix.lower()

    @staticmethod
    def is_allowed_extension(filename: str, allowed: List[str]) -> bool:
        """
        Check if file extension is allowed

        Args:
            filename: Filename to check
            allowed: List of allowed extensions (e.g., ['.jpg', '.png', '.pdf'])

        Returns:
            True if allowed, False otherwise
        """
        if not allowed:
            return True  # No restrictions

        ext = FileUploadService.get_file_extension(filename)
        return ext in [a.lower() for a in allowed]

    @staticmethod
    def is_allowed_mimetype(file: FileStorage, allowed_patterns: List[str]) -> bool:
        """
        Check if file MIME type matches allowed patterns

        Args:
            file: FileStorage object
            allowed_patterns: List of MIME patterns (e.g., ['image/*', 'application/pdf'])

        Returns:
            True if allowed, False otherwise
        """
        if not allowed_patterns:
            return True  # No restrictions

        file_mimetype = file.content_type or mimetypes.guess_type(file.filename)[0]

        if not file_mimetype:
            return False

        for pattern in allowed_patterns:
            if pattern == '*/*':
                return True

            if '*' in pattern:
                # Handle wildcards like 'image/*'
                main_type = pattern.split('/')[0]
                if file_mimetype.startswith(main_type + '/'):
                    return True
            elif file_mimetype == pattern:
                return True

        return False

    def validate_file(
        self,
        file: FileStorage,
        max_size: Optional[str] = None,
        allowed_extensions: Optional[List[str]] = None,
        allowed_mimetypes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate uploaded file

        Args:
            file: FileStorage object from Flask
            max_size: Maximum file size (e.g., '5MB', '100KB')
            allowed_extensions: List of allowed extensions
            allowed_mimetypes: List of allowed MIME types

        Returns:
            Dict with validation result

        Raises:
            FileUploadError: If validation fails
        """
        if not file or not file.filename:
            raise FileUploadError("No file provided")

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # Reset to beginning

        if max_size:
            max_bytes = self.parse_size(max_size)
            if file_size > max_bytes:
                raise FileUploadError(
                    f"File size ({file_size / self.MB:.2f}MB) exceeds maximum ({max_size})"
                )

        # Check extension
        if allowed_extensions and not self.is_allowed_extension(file.filename, allowed_extensions):
            raise FileUploadError(
                f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
            )

        # Check MIME type
        if allowed_mimetypes and not self.is_allowed_mimetype(file, allowed_mimetypes):
            raise FileUploadError(
                f"File MIME type not allowed. Allowed: {', '.join(allowed_mimetypes)}"
            )

        return {
            'valid': True,
            'filename': file.filename,
            'size': file_size,
            'mimetype': file.content_type
        }

    def upload_file(
        self,
        file: FileStorage,
        destination: str,
        name_conflict: str = "error",
        custom_filename: Optional[str] = None,
        max_size: Optional[str] = None,
        allowed_extensions: Optional[List[str]] = None,
        allowed_mimetypes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Upload file to destination

        Args:
            file: FileStorage object from Flask
            destination: Destination directory
            name_conflict: Strategy for naming conflicts (error, overwrite, skip, makeUnique)
            custom_filename: Optional custom filename
            max_size: Maximum file size
            allowed_extensions: Allowed file extensions
            allowed_mimetypes: Allowed MIME types

        Returns:
            Dict with upload result

        Raises:
            FileUploadError: If upload fails
        """
        # Validate file
        validation = self.validate_file(file, max_size, allowed_extensions, allowed_mimetypes)

        # Secure the filename
        original_filename = custom_filename or file.filename
        secure_name = secure_filename(original_filename)

        # Create destination directory if it doesn't exist
        dest_path = Path(destination)
        dest_path.mkdir(parents=True, exist_ok=True)

        # Handle name conflicts
        final_filename = secure_name
        file_path = dest_path / final_filename

        if file_path.exists():
            if name_conflict == "error":
                raise FileUploadError(f"File '{final_filename}' already exists")
            elif name_conflict == "skip":
                return {
                    'success': False,
                    'skipped': True,
                    'filename': final_filename,
                    'message': 'File already exists and was skipped'
                }
            elif name_conflict == "makeUnique":
                # Generate unique filename
                name_part = file_path.stem
                ext_part = file_path.suffix
                unique_id = uuid.uuid4().hex[:8]
                final_filename = f"{name_part}_{unique_id}{ext_part}"
                file_path = dest_path / final_filename
            # elif name_conflict == "overwrite": just use the same filename

        # Save file
        try:
            file.save(str(file_path))
        except Exception as e:
            raise FileUploadError(f"Failed to save file: {e}")

        return {
            'success': True,
            'filename': final_filename,
            'filepath': str(file_path),
            'original_filename': original_filename,
            'size': validation['size'],
            'mimetype': validation['mimetype'],
            'url': f"/uploads/{final_filename}"  # Relative URL
        }

    def delete_file(self, filepath: str) -> Dict[str, Any]:
        """
        Delete a file

        Args:
            filepath: Path to file to delete

        Returns:
            Dict with deletion result
        """
        file_path = Path(filepath)

        if not file_path.exists():
            return {
                'success': False,
                'error': 'File not found'
            }

        try:
            file_path.unlink()
            return {
                'success': True,
                'message': 'File deleted successfully'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
