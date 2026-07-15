"""Per-receiver file logging for JDE/POS webhook synchronization.

Each receiver endpoint (product, item-branch, base-price, customer-master) gets
its own log folder and a daily log file (``<receiver>-YYYY-MM-DD.log``) so logs
don't pile up in a single file. A fresh file is created every day and old files
are pruned after a configurable number of days.
"""

from datetime import datetime
from pathlib import Path

import logging
import logging.handlers

# backend/ (the directory that contains src/)
BACKEND_DIR = Path(__file__).resolve().parents[3]
LOGS_DIR = BACKEND_DIR / "logs"

RECEIVER_LOG_BACKUP_DAYS = 30
RECEIVER_LOG_FORMAT = "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s"

_DATE_FMT = "%Y-%m-%d"


class DailyFileHandler(logging.handlers.TimedRotatingFileHandler):
    """File handler that writes to ``<basename>-YYYY-MM-DD.log``.

    A new dated file is created whenever the date changes (rolling over at
    midnight for long-running processes). Old dated files beyond ``backup_days``
    are removed.
    """

    def __init__(
        self,
        log_dir: Path,
        basename: str,
        backup_days: int = RECEIVER_LOG_BACKUP_DAYS,
        encoding: str | None = "utf-8",
    ) -> None:
        self._log_dir = log_dir
        self._basename = basename
        self._backup_days = backup_days
        self._date = datetime.now().strftime(_DATE_FMT)
        super().__init__(
            self._filename_for(self._date),
            when="midnight",
            interval=1,
            backupCount=backup_days,
            encoding=encoding,
            delay=True,
        )

    def _filename_for(self, date_str: str) -> str:
        return str(self._log_dir / f"{self._basename}-{date_str}.log")

    def _prune_old_logs(self) -> None:
        if self._backup_days <= 0:
            return
        keep_after = datetime.now().strftime(_DATE_FMT)
        dated = (self._log_dir / f"{self._basename}-{keep_after}.log").exists()
        files = sorted(self._log_dir.glob(f"{self._basename}-*.log"))
        # Keep the most recent ``backup_days`` files (including today).
        for old in files[: max(0, len(files) - self._backup_days)]:
            try:
                old.unlink()
            except OSError:
                pass

    def shouldRollover(self, record: logging.LogRecord) -> int:
        today = datetime.now().strftime(_DATE_FMT)
        return 1 if today != self._date else 0

    def doRollover(self, record: logging.LogRecord) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None
        self._date = datetime.now().strftime(_DATE_FMT)
        self.baseFilename = self._filename_for(self._date)
        self.mode = "a"
        self.stream = self._open()
        self._prune_old_logs()


def get_receiver_logger(
    receiver: str,
    filename: str | None = None,
    backup_days: int = RECEIVER_LOG_BACKUP_DAYS,
    level: int = logging.INFO,
) -> logging.Logger:
    """Return a daily file logger for a specific receiver endpoint.

    Args:
        receiver: Folder name under ``logs/`` (one per receiver endpoint).
        filename: Log file base name (without extension/date). Defaults to ``receiver``.
        backup_days: Number of daily files to retain.
        level: Logging level for the file handler.

    Returns:
        A configured ``logging.Logger`` writing to
        ``logs/<receiver>/<filename>-YYYY-MM-DD.log`` with daily rotation.
    """
    if filename is None:
        filename = receiver

    log_dir = LOGS_DIR / receiver

    logger_name = f"receiver.{receiver}.{filename}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    logger.propagate = False

    if not any(isinstance(h, DailyFileHandler) for h in logger.handlers):
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            handler = DailyFileHandler(log_dir, filename, backup_days=backup_days, encoding="utf-8")
            handler.setFormatter(logging.Formatter(RECEIVER_LOG_FORMAT))
            handler.setLevel(level)
            logger.addHandler(handler)
        except OSError as exc:
            # Never let a logging failure crash the application (e.g. when the
            # logs directory isn't writable inside a container).
            logging.getLogger(__name__).warning(
                f"Tidak dapat membuat receiver log '{log_dir}': {exc}. "
                f"Logging ke file dilewati untuk receiver '{receiver}'."
            )

    return logger
