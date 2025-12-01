"""
Security utilities for input validation and path sanitization.
"""
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def validate_config_path(config_path: str, project_root: Optional[Path] = None) -> Path:
    """
    Validate and sanitize config path to prevent path traversal attacks.
    
    Args:
        config_path: User-provided config path
        project_root: Root directory to restrict paths to (defaults to project root)
        
    Returns:
        Validated Path object
        
    Raises:
        ValueError: If path is invalid or outside allowed directory
    """
    if not config_path:
        raise ValueError("Config path cannot be empty")
    
    # Resolve to absolute path
    resolved = Path(config_path).resolve()
    
    # Determine project root if not provided
    if project_root is None:
        # Get project root (parent of google_photos_icloud_migration package)
        project_root = Path(__file__).parent.parent.parent.resolve()
    
    # Ensure path is within project directory
    try:
        resolved.relative_to(project_root.resolve())
    except ValueError:
        raise ValueError(
            f"Config path must be within project directory. "
            f"Got: {config_path}, resolved to: {resolved}"
        )
    
    # Ensure it's a YAML file
    if resolved.suffix not in ['.yaml', '.yml']:
        raise ValueError(f"Config file must be a YAML file, got: {resolved.suffix}")
    
    return resolved


def validate_file_path(file_path: str, base_dir: Path) -> Path:
    """
    Validate file path is within base directory to prevent path traversal.
    
    Args:
        file_path: User-provided file path (can be relative)
        base_dir: Base directory that file must be within
        
    Returns:
        Validated absolute Path object
        
    Raises:
        ValueError: If path is outside base directory
    """
    if not file_path:
        raise ValueError("File path cannot be empty")
    
    # Resolve to absolute path
    base_dir_resolved = base_dir.resolve()
    resolved = (base_dir_resolved / file_path).resolve()
    
    # Ensure path is within base directory
    if not str(resolved).startswith(str(base_dir_resolved)):
        raise ValueError(
            f"File path must be within base directory. "
            f"Base: {base_dir_resolved}, Got: {resolved}"
        )
    
    return resolved


def is_safe_zip_path(zip_path: Path, extract_to: Path) -> bool:
    """
    Check if a path from a zip file is safe to extract (prevents zip slip).
    
    Args:
        zip_path: Path within zip file
        extract_to: Destination directory for extraction
        
    Returns:
        True if path is safe, False otherwise
    """
    # Resolve both paths
    extract_to_resolved = extract_to.resolve()
    target_path = (extract_to_resolved / zip_path).resolve()
    
    # Check if target is within extract directory
    try:
        target_path.relative_to(extract_to_resolved)
        return True
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and other attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove dangerous characters
    dangerous_chars = [';', '|', '&', '$', '`', '(', ')', '<', '>', '\n', '\r']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext
    
    return filename


def validate_subprocess_path(file_path: Path) -> None:
    """
    Validate file path before passing to subprocess to prevent command injection.
    
    Note: When using subprocess.run() with a list of arguments (not shell=True),
    parentheses and most characters are safe. This validation is conservative
    but allows common filename characters like parentheses.
    
    Args:
        file_path: Path to validate
        
    Raises:
        ValueError: If path contains dangerous characters
    """
    path_str = str(file_path)
    
    # Check for truly dangerous characters that could cause issues even with list args
    # Note: Parentheses () are safe when using subprocess.run() with list arguments
    # as Python handles them properly. Only reject characters that could cause
    # actual problems (null bytes, newlines in paths, shell metacharacters if shell=True)
    dangerous_chars = ['\x00', '\n', '\r']  # Null bytes and newlines are problematic
    
    # Also check for characters that could be dangerous if shell=True is used
    # (though we don't use shell=True, this is a safety measure)
    shell_dangerous = [';', '|', '&', '$', '`', '<', '>']
    
    for char in dangerous_chars:
        if char in path_str:
            raise ValueError(f"Invalid character in file path: {char}")
    
    # Warn about shell-dangerous characters but don't fail (they're safe with list args)
    for char in shell_dangerous:
        if char in path_str:
            logger.warning(f"File path contains potentially problematic character '{char}': {file_path}")
            # Don't raise - these are safe with subprocess.run(list) but log for awareness
    
    # Ensure path is absolute and normalized
    if not file_path.is_absolute():
        file_path = file_path.resolve()
    
    # Ensure it's a file (not directory)
    if not file_path.is_file():
        raise ValueError(f"Path must be a file: {file_path}")










