"""
Centralized Logging Configuration for Aviation RAG.
Provides structured, leveled logging with JSON support for production observability.
"""

import logging
import sys
import json
import uuid
from contextvars import ContextVar
from datetime import datetime
from app.core.config import settings

# Context variable to store request ID across the async context
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="system")

class JsonFormatter(logging.Formatter):
    """
    Custom JSON formatter for production-ready logs.
    Includes timestamp, level, message, module, and correlation IDs.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "request_id": request_id_ctx.get()
        }
        
        # Include extra fields if present
        if hasattr(record, "extra_data"):
            log_payload.update(record.extra_data)
            
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_payload)

def setup_logger(name: str = "aviation_rag") -> logging.Logger:
    """
    Industry-standard logging setup with environment-aware formatting.
    """
    _logger = logging.getLogger(name)

    if _logger.hasHandlers():
        return _logger

    _logger.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    
    if settings.APP_ENV == "prod":
        handler.setFormatter(JsonFormatter())
    else:
        # Professional standard format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - [%(request_id)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        # Customizing record factory to include request_id in non-json logs
        old_factory = logging.getLogRecordFactory()
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.request_id = request_id_ctx.get()
            return record
        logging.setLogRecordFactory(record_factory)
        handler.setFormatter(formatter)

    _logger.addHandler(handler)
    return _logger

# Default singleton logger
logger = setup_logger()
