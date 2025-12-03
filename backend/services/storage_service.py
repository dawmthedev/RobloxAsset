"""
Storage Service for file management and URL generation.
Handles file storage, retrieval, and URL generation for assets.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from config import STORAGE_DIR, IMAGES_DIR, PROTOTYPES_DIR, FINAL_DIR


class StorageService:
    """
    Service class for file storage operations.
    Manages local file storage and provides URL generation.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize storage service.
        
        Args:
            base_url: Base URL for generating file URLs
        """
        self.base_url = base_url.rstrip("/")
        self.storage_dir = STORAGE_DIR
        self.images_dir = IMAGES_DIR
        self.prototypes_dir = PROTOTYPES_DIR
        self.final_dir = FINAL_DIR
        
        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create storage directories if they don't exist."""
        for directory in [self.images_dir, self.prototypes_dir, self.final_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def get_file_url(self, file_path: str) -> str:
        """
        Generate a URL for accessing a stored file.
        
        Args:
            file_path: Absolute or relative path to the file
            
        Returns:
            URL for accessing the file
        """
        # Convert to Path object
        path = Path(file_path)
        
        # Get relative path from storage directory
        try:
            relative_path = path.relative_to(self.storage_dir)
        except ValueError:
            # If not relative to storage dir, use the filename
            relative_path = path.name
        
        return f"{self.base_url}/storage/{relative_path}"

    def get_image_url(self, filename: str) -> str:
        """
        Generate URL for an image file.
        
        Args:
            filename: Name of the image file
            
        Returns:
            URL for accessing the image
        """
        return f"{self.base_url}/storage/images/{filename}"

    def get_prototype_url(self, filename: str) -> str:
        """
        Generate URL for a prototype file.
        
        Args:
            filename: Name of the prototype file
            
        Returns:
            URL for accessing the prototype
        """
        return f"{self.base_url}/storage/prototypes/{filename}"

    def get_final_url(self, filename: str) -> str:
        """
        Generate URL for a final model file.
        
        Args:
            filename: Name of the final model file
            
        Returns:
            URL for accessing the final model
        """
        return f"{self.base_url}/storage/final/{filename}"

    def save_image(self, source_path: str, filename: Optional[str] = None) -> str:
        """
        Save an image to the images directory.
        
        Args:
            source_path: Path to the source image
            filename: Optional custom filename
            
        Returns:
            Path to the saved image
        """
        source = Path(source_path)
        if filename is None:
            filename = source.name
        
        dest_path = self.images_dir / filename
        shutil.copy2(source, dest_path)
        
        return str(dest_path)

    def save_prototype(self, source_path: str, filename: Optional[str] = None) -> str:
        """
        Save a prototype file to the prototypes directory.
        
        Args:
            source_path: Path to the source file
            filename: Optional custom filename
            
        Returns:
            Path to the saved prototype
        """
        source = Path(source_path)
        if filename is None:
            filename = source.name
        
        dest_path = self.prototypes_dir / filename
        shutil.copy2(source, dest_path)
        
        return str(dest_path)

    def save_final(self, source_path: str, filename: Optional[str] = None) -> str:
        """
        Save a final model file to the final directory.
        
        Args:
            source_path: Path to the source file
            filename: Optional custom filename
            
        Returns:
            Path to the saved final model
        """
        source = Path(source_path)
        if filename is None:
            filename = source.name
        
        dest_path = self.final_dir / filename
        shutil.copy2(source, dest_path)
        
        return str(dest_path)

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                return True
            return False
        except Exception:
            return False

    def list_images(self) -> List[str]:
        """
        List all image files in storage.
        
        Returns:
            List of image filenames
        """
        return [f.name for f in self.images_dir.iterdir() if f.is_file()]

    def list_prototypes(self) -> List[str]:
        """
        List all prototype files in storage.
        
        Returns:
            List of prototype filenames
        """
        return [f.name for f in self.prototypes_dir.iterdir() if f.is_file()]

    def list_finals(self) -> List[str]:
        """
        List all final model files in storage.
        
        Returns:
            List of final model filenames
        """
        return [f.name for f in self.final_dir.iterdir() if f.is_file()]

    def get_file_info(self, file_path: str) -> Optional[dict]:
        """
        Get information about a stored file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file info or None if file doesn't exist
        """
        path = Path(file_path)
        if not path.exists():
            return None
        
        stat = path.stat()
        return {
            "name": path.name,
            "path": str(path),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": path.suffix,
        }

    def cleanup_old_files(self, max_age_days: int = 30) -> int:
        """
        Clean up files older than the specified age.
        
        Args:
            max_age_days: Maximum age in days for files to keep
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        cutoff = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
        
        for directory in [self.images_dir, self.prototypes_dir, self.final_dir]:
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff:
                    file_path.unlink()
                    deleted_count += 1
        
        return deleted_count


# Singleton instance
_storage_service: Optional[StorageService] = None


def get_storage_service(base_url: str = "http://localhost:8000") -> StorageService:
    """
    Get or create the storage service singleton.
    
    Args:
        base_url: Base URL for file URL generation
        
    Returns:
        StorageService instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService(base_url)
    return _storage_service
