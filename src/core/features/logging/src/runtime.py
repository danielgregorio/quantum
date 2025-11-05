"""
Runtime service for q:log - Structured Logging
"""

import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


class LoggingService:
    """
    Service to handle structured logging with multiple severity levels

    Phase 1 Features:
    - Console and file output
    - JSON structured format
    - Multiple log levels
    - Conditional logging
    - Context data

    Phase 2 Features (TODO):
    - Loguru integration
    - External services (Sentry, Datadog)
    - Async logging
    - Log rotation
    - Correlation IDs
    """

    # Map Quantum log levels to Python logging levels
    LEVEL_MAP = {
        'trace': logging.DEBUG - 5,  # Custom level below DEBUG
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }

    _instance: Optional['LoggingService'] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern to ensure one logger instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logging service"""
        if not LoggingService._initialized:
            self._setup_logging()
            LoggingService._initialized = True

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logger
        self.logger = logging.getLogger('quantum')
        self.logger.setLevel(logging.DEBUG)  # Capture all levels

        # Prevent duplicate handlers
        if self.logger.handlers:
            return

        # Console handler - formatted output for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        # File handler - JSON format for production (Phase 1: basic file logging)
        # Phase 2 will add rotation with Loguru
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'quantum_{datetime.now().strftime("%Y%m%d")}.log')

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        # For now, use same format. Phase 2 will use JSON formatter
        file_handler.setFormatter(console_formatter)
        self.logger.addHandler(file_handler)

        # Custom TRACE level
        logging.addLevelName(self.LEVEL_MAP['trace'], 'TRACE')

    def log(
        self,
        level: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Write a log entry

        Args:
            level: Log severity level
            message: Log message (already resolved with databinding)
            context: Optional structured context data
            correlation_id: Optional request tracking ID

        Returns:
            Result dictionary with success status
        """
        try:
            # Get Python logging level
            py_level = self.LEVEL_MAP.get(level, logging.INFO)

            # Build log entry
            log_data = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message
            }

            if context:
                log_data['context'] = context

            if correlation_id:
                log_data['correlation_id'] = correlation_id

            # Log to Python logger
            # For Phase 1, just log the message. Phase 2 will log full JSON
            extra_info = []
            if context:
                extra_info.append(f"context={json.dumps(context)}")
            if correlation_id:
                extra_info.append(f"correlation_id={correlation_id}")

            full_message = message
            if extra_info:
                full_message = f"{message} | {' | '.join(extra_info)}"

            self.logger.log(py_level, full_message)

            return {
                'success': True,
                'timestamp': log_data['timestamp'],
                'level': level,
                'message': message,
                'destination': 'file+console'
            }

        except Exception as e:
            # Logging should never crash the application
            # Silently capture errors and return failure
            return {
                'success': False,
                'error': str(e)
            }

    def should_log(self, condition: Any) -> bool:
        """
        Evaluate if logging should occur based on 'when' condition

        Args:
            condition: Evaluated condition value

        Returns:
            True if should log, False otherwise
        """
        # If no condition, always log
        if condition is None:
            return True

        # Evaluate boolean condition
        if isinstance(condition, bool):
            return condition

        # Truthy evaluation for other types
        return bool(condition)
