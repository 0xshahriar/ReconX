"""
ReconX Logging Configuration
Centralized logging setup with rotation and formatting
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

# Log formatters
DETAILED_FORMAT = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

SIMPLE_FORMAT = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)

JSON_FORMAT = logging.Formatter(
    '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", '
    '"function": "%(funcName)s", "line": %(lineno)d, "message": "%(message)s"}',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def setup_logging(
    log_dir: str = "logs",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """Setup centralized logging"""
    
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (log_path / "scans").mkdir(exist_ok=True)
    (log_path / "errors").mkdir(exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(console_level)
    console.setFormatter(SIMPLE_FORMAT)
    root_logger.addHandler(console)
    
    # Main file handler (rotating)
    main_file = logging.handlers.RotatingFileHandler(
        log_path / "api.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    main_file.setLevel(file_level)
    main_file.setFormatter(DETAILED_FORMAT)
    root_logger.addHandler(main_file)
    
    # Error file handler
    error_file = logging.handlers.RotatingFileHandler(
        log_path / "errors" / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    error_file.setLevel(logging.ERROR)
    error_file.setFormatter(DETAILED_FORMAT)
    root_logger.addHandler(error_file)
    
    # Reduce noise from external libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    return root_logger

def get_logger(name: str) -> logging.Logger:
    """Get logger with specified name"""
    return logging.getLogger(name)

def get_scan_logger(scan_id: str) -> logging.Logger:
    """Get dedicated logger for a scan"""
    logger = logging.getLogger(f"scan.{scan_id}")
    
    # Add scan-specific file handler if not already added
    if not any(isinstance(h, logging.FileHandler) and scan_id in str(h.baseFilename) 
               for h in logger.handlers):
        
        log_path = Path("logs/scans") / f"{scan_id}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_path)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(DETAILED_FORMAT)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    
    return logger

def setup_scan_logging(scan_id: str) -> logging.Logger:
    """Setup dedicated logging for a scan"""
    return get_scan_logger(scan_id)
