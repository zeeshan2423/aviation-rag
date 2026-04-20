"""
Centralized Logging Configuration for Aviation RAG.
Provides structured, leveled logging for all system components (Production Hardened).
"""

import logging
import sys
from app.core.config import settings


def setup_logger(name: str = "aviation_rag") -> logging.Logger:
    """
    Industry-standard logging setup with stream handlers and structured formatting.
    """
    _logger = logging.getLogger(name)

    # Avoid duplicate handlers if setup multiple times
    if _logger.hasHandlers():
        return _logger

    _logger.setLevel(settings.LOG_LEVEL)

    # Create console handler with a professional format
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    _logger.addHandler(handler)
    return _logger


# Default singleton logger for root-level usage
logger = setup_logger()
