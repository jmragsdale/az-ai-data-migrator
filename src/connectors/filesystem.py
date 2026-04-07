"""Filesystem connector for discovering and streaming files."""

import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class FileSystemConnector:
    """Discover and stream files from filesystem."""

    # File type categories
    DOCUMENT_TYPES = {".pdf", ".docx", ".doc", ".txt", ".xlsx", ".csv", ".json"}
    IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
    VIDEO_TYPES = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m3u8"}
    AUDIO_TYPES = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"}

    def __init__(self, root_path: str):
        """Initialize filesystem connector.

        Args:
            root_path: Root directory path for scanning

        Raises:
            FileNotFoundError: If root path does not exist
        """
        self.root_path = Path(root_path)
        if not self.root_path.exists():
            raise FileNotFoundError(f"Root path not found: {root_path}")

        if not self.root_path.is_dir():
            raise ValueError(f"Root path must be a directory: {root_path}")

        logger.info(f"Initialized filesystem connector at {root_path}")

    def scan_directory(self) -> Dict[str, Any]:
        """Scan directory and categorize files.

        Returns:
            Directory scan results with file categorization
        """
        files_by_category = {
            "documents": [],
            "images": [],
            "videos": [],
            "audio": [],
            "other": [],
        }

        total_size = 0
        file_count = 0

        for file_path in self.root_path.rglob("*"):
            if not file_path.is_file():
                continue

            file_count += 1
            file_size = file_path.stat().st_size
            total_size += file_size

            suffix = file_path.suffix.lower()
            file_info = {
                "path": str(file_path),
                "name": file_path.name,
                "size_bytes": file_size,
                "modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
                "mime_type": mimetypes.guess_type(file_path)[0],
            }

            if suffix in self.DOCUMENT_TYPES:
                files_by_category["documents"].append(file_info)
            elif suffix in self.IMAGE_TYPES:
                files_by_category["images"].append(file_info)
            elif suffix in self.VIDEO_TYPES:
                files_by_category["videos"].append(file_info)
            elif suffix in self.AUDIO_TYPES:
                files_by_category["audio"].append(file_info)
            else:
                files_by_category["other"].append(file_info)

        return {
            "root_path": str(self.root_path),
            "total_files": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "files_by_category": files_by_category,
        }

    def list_files(
        self, file_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """List files, optionally filtered by type.

        Args:
            file_types: Optional list of file extensions to filter (.pdf, .docx, etc.)

        Returns:
            List of file information dictionaries
        """
        files = []

        for file_path in self.root_path.rglob("*"):
            if not file_path.is_file():
                continue

            if file_types and file_path.suffix.lower() not in file_types:
                continue

            files.append({
                "path": str(file_path),
                "name": file_path.name,
                "size_bytes": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
                "mime_type": mimetypes.guess_type(file_path)[0],
            })

        return files

    def stream_files(
        self,
        batch_size: int = 10,
        file_types: Optional[List[str]] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Stream files in batches.

        Args:
            batch_size: Number of files per batch
            file_types: Optional list of file extensions to filter

        Yields:
            Batches of file information
        """
        batch = []

        for file_path in self.root_path.rglob("*"):
            if not file_path.is_file():
                continue

            if file_types and file_path.suffix.lower() not in file_types:
                continue

            file_info = {
                "path": str(file_path),
                "name": file_path.name,
                "size_bytes": file_path.stat().st_size,
                "modified": datetime.fromtimestamp(
                    file_path.stat().st_mtime
                ).isoformat(),
                "mime_type": mimetypes.guess_type(file_path)[0],
            }

            batch.append(file_info)

            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch

    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """Get detailed metadata for a single file.

        Args:
            file_path: Path to file

        Returns:
            File metadata dictionary

        Raises:
            FileNotFoundError: If file not found
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        stat = path.stat()
        return {
            "path": str(path.absolute()),
            "name": path.name,
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "mime_type": mimetypes.guess_type(path)[0],
            "is_readable": os.access(path, os.R_OK),
            "is_writable": os.access(path, os.W_OK),
        }

    def read_text_file(self, file_path: str, encoding: str = "utf-8") -> str:
        """Read text file content.

        Args:
            file_path: Path to file
            encoding: File encoding

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file not found
            ValueError: If file is not readable as text
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except (UnicodeDecodeError, IOError) as e:
            raise ValueError(f"Cannot read file {file_path}: {e}")

    def get_directory_structure(self) -> Dict[str, Any]:
        """Get directory tree structure.

        Returns:
            Nested dictionary representing directory structure
        """
        def build_tree(path: Path) -> Dict[str, Any]:
            """Recursively build directory tree."""
            tree = {
                "name": path.name or str(path),
                "type": "directory",
                "children": [],
            }

            try:
                for item in sorted(path.iterdir()):
                    if item.is_dir():
                        tree["children"].append(build_tree(item))
                    else:
                        tree["children"].append({
                            "name": item.name,
                            "type": "file",
                            "size_bytes": item.stat().st_size,
                        })
            except PermissionError:
                tree["error"] = "Permission denied"

            return tree

        return build_tree(self.root_path)
