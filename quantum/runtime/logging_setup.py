"""
Quantum Logging Setup - Bridges quantum.config.yaml logging section to Python logging.

Configures the 'quantum' root logger with colored console output and file logging.
All child loggers (quantum.server, quantum.parser, quantum.runtime, quantum.errors)
inherit the configured handlers.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict


class ColoredFormatter(logging.Formatter):
    """Formatter that adds ANSI color codes based on log level."""

    COLORS = {
        logging.DEBUG: '\033[36m',      # cyan
        logging.INFO: '\033[32m',       # green
        logging.WARNING: '\033[33m',    # yellow
        logging.ERROR: '\033[31m',      # red
        logging.CRITICAL: '\033[41m',   # red background
    }
    RESET = '\033[0m'

    def __init__(self, fmt=None, datefmt=None, use_color=True):
        super().__init__(fmt, datefmt)
        self.use_color = use_color

    def format(self, record):
        if self.use_color:
            color = self.COLORS.get(record.levelno, '')
            reset = self.RESET
            record.levelname = f"{color}{record.levelname:<8}{reset}"
        else:
            record.levelname = f"{record.levelname:<8}"
        return super().format(record)


def _supports_color() -> bool:
    """Detect whether the terminal supports ANSI color codes."""
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('FORCE_COLOR'):
        return True
    if not hasattr(sys.stderr, 'isatty'):
        return False
    if sys.stderr.isatty():
        return True
    # Windows Terminal sets WT_SESSION
    if os.environ.get('WT_SESSION'):
        return True
    return False


def setup_logging(config: Dict[str, Any]) -> logging.Logger:
    """
    Configure the 'quantum' root logger from the config dictionary.

    Reads config['logging'] for level, format, console, file, filename.
    Reads config['paths']['logs'] for the log directory.

    Args:
        config: Full quantum configuration dictionary

    Returns:
        The configured 'quantum' root logger
    """
    log_config = config.get('logging', {})
    paths_config = config.get('paths', {})

    level_name = log_config.get('level', 'INFO').upper()
    level = getattr(logging, level_name, logging.INFO)
    enable_console = log_config.get('console', True)
    enable_file = log_config.get('file', True)
    filename = log_config.get('filename', 'quantum.log')
    log_dir = paths_config.get('logs', './logs')

    # Get or create the quantum root logger and clear existing handlers
    logger = logging.getLogger('quantum')
    logger.setLevel(level)
    logger.handlers.clear()

    datefmt = '%Y-%m-%d %H:%M:%S'
    plain_fmt = '%(asctime)s %(levelname)-8s %(name)s - %(message)s'

    # Console handler with color support
    if enable_console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(level)
        use_color = _supports_color()
        colored_fmt = '%(asctime)s %(levelname)s %(name)s - %(message)s'
        formatter = ColoredFormatter(colored_fmt, datefmt=datefmt, use_color=use_color)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler with plain formatter
    if enable_file:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            str(log_path / filename), encoding='utf-8'
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(plain_fmt, datefmt=datefmt))
        logger.addHandler(file_handler)

    # Suppress werkzeug's noisy default request logging
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    # Inject into LoggingService singleton to prevent duplicate handlers
    try:
        from quantum.core.features.logging.src.runtime import LoggingService
        LoggingService.configure_from_external(logger)
    except Exception:
        pass  # LoggingService may not be available

    return logger


def get_status_color(code: int) -> str:
    """Return ANSI color escape for an HTTP status code."""
    if not _supports_color():
        return ''
    if code < 300:
        return '\033[32m'   # green
    if code < 400:
        return '\033[33m'   # yellow
    if code < 500:
        return '\033[31m'   # red
    return '\033[91m'       # bright red


def get_reset() -> str:
    """Return ANSI reset escape if color is supported."""
    if not _supports_color():
        return ''
    return '\033[0m'
