"""Custom logging handlers for different output destinations."""

import logging
import logging.handlers
import sys
from pathlib import Path

from .formatters import get_formatter


class ColoredConsoleHandler(logging.StreamHandler):
    """Enhanced console handler with color support."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def __init__(self, stream=None):
        super().__init__(stream or sys.stdout)
        self.use_colors = self._should_use_colors()

    def _should_use_colors(self) -> bool:
        return hasattr(self.stream, "isatty") and self.stream.isatty() and sys.platform != "win32"

    def format(self, record: logging.LogRecord) -> str:
        formatted = super().format(record)
        if self.use_colors and record.levelname in self.COLORS:
            color = self.COLORS[record.levelname]
            formatted = formatted.replace(f"[{record.levelname}]", f"[{color}{record.levelname}{self.RESET}]")
        return formatted


class RotatingFileHandler(logging.handlers.RotatingFileHandler):
    """Enhanced rotating file handler with automatic directory creation."""

    def __init__(self, filename: str, max_bytes: int = 10485760, backup_count: int = 5, encoding: str = "utf-8"):
        log_path = Path(filename)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename=filename, maxBytes=max_bytes, backupCount=backup_count, encoding=encoding)


class DailyFileHandler(logging.FileHandler):
    """Enhanced file handler that writes to daily files and switches at midnight.

    This avoids multi-process file rotation conflicts.
    """

    def __init__(self, filename: str, encoding: str = "utf-8"):
        import os
        import datetime
        self.filename_base = filename
        self.current_date = datetime.date.today()

        log_path = Path(self._get_filename())
        log_path.parent.mkdir(parents=True, exist_ok=True)
        super().__init__(filename=str(log_path), encoding=encoding)

    def _get_filename(self) -> str:
        import datetime
        path = Path(self.filename_base)
        dir_name = path.parent
        base_name = path.stem
        ext = path.suffix
        date_str = self.current_date.strftime("%Y-%m-%d")
        return str(dir_name / f"{base_name}_{date_str}{ext}")

    def emit(self, record: logging.LogRecord) -> None:
        import os
        import datetime
        today = datetime.date.today()
        if today != self.current_date:
            self.current_date = today
            self.stream.close()
            self.baseFilename = os.path.abspath(self._get_filename())
            self.stream = self._open()
        super().emit(record)


def create_console_handler(
    format_type: str = "detailed", level: int = logging.INFO, use_colors: bool = True
) -> logging.Handler:
    """Create a configured console handler."""
    handler: logging.Handler
    if use_colors:
        handler = ColoredConsoleHandler()
    else:
        handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(get_formatter(format_type))
    return handler


def create_file_handler(
    filepath: str,
    format_type: str = "structured",
    level: int = logging.DEBUG,
    max_bytes: int = 10485760,
    backup_count: int = 5,
) -> logging.Handler:
    """Create a configured daily file handler."""
    handler = DailyFileHandler(filename=filepath)
    handler.setLevel(level)
    handler.setFormatter(get_formatter(format_type))
    return handler


def create_null_handler() -> logging.Handler:
    """Create a null handler that discards all log records."""
    return logging.NullHandler()
