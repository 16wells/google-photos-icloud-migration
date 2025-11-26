"""
Logging configuration utilities with structured logging and log rotation.
"""
import json
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any


def setup_logging(
    log_file: str = "migration.log",
    level: str = "INFO",
    enable_json: bool = False,
    enable_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    separate_error_log: bool = True
) -> None:
    """
    Set up logging with rotation and optional structured output.
    
    Args:
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: If True, use JSON format for structured logging
        enable_rotation: If True, enable log rotation
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup log files to keep
        separate_error_log: If True, create separate error log file
    """
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Set logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Create formatters
    if enable_json:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Console handler with rich formatting
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    if enable_rotation:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
    else:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
    
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Separate error log file
    if separate_error_log:
        error_log_file = log_path.parent / f"{log_path.stem}_error{log_path.suffix}"
        error_handler = logging.handlers.RotatingFileHandler(
            str(error_log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)
    
    # Debug log file (only if level is DEBUG)
    if log_level == logging.DEBUG:
        debug_log_file = log_path.parent / f"{log_path.stem}_debug{log_path.suffix}"
        debug_handler = logging.handlers.RotatingFileHandler(
            str(debug_log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        root_logger.addHandler(debug_handler)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: Dict[str, Any] = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)
        
        return json.dumps(log_obj)

