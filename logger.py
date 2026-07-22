"""
Break Tracker Enterprise
Logger Module

Version: 1.0.0
Author: Jaleel Ahamed

Provides centralized enterprise logging for the application.

Features
--------
- Console logging
- Application log
- Error log
- Rotating log files
- Automatic log folder creation
- Singleton logger manager
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


# ============================================================
# CONFIGURATION
# ============================================================

LOG_DIRECTORY = "logs"
ARCHIVE_DIRECTORY = "archive"

APPLICATION_LOG = "application.log"
ERROR_LOG = "error.log"

MAX_LOG_SIZE = 5 * 1024 * 1024      # 5 MB
BACKUP_COUNT = 5


# ============================================================
# LOGGING MANAGER
# ============================================================

class LoggingManager:
    """
    Central logging manager for Break Tracker Enterprise.

    Responsible for:

    - Creating log folders
    - Configuring handlers
    - Preventing duplicate handlers
    - Providing loggers
    """

    _instance: Optional["LoggingManager"] = None
    _initialized = False

    # --------------------------------------------------------

    def __new__(cls):

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    # --------------------------------------------------------

    def __init__(self):

        if self.__class__._initialized:
            return

        self.base_path = Path(__file__).parent

        self.logs_path = self.base_path / LOG_DIRECTORY

        self.archive_path = self.logs_path / ARCHIVE_DIRECTORY

        self.application_log = self.logs_path / APPLICATION_LOG

        self.error_log = self.logs_path / ERROR_LOG

        self._create_directories()

        self.formatter = self._create_formatter()

        self._configure_root_logger()

        self.__class__._initialized = True

    # --------------------------------------------------------

    def _create_directories(self) -> None:
        """
        Create required folders if they do not already exist.
        """

        self.logs_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.archive_path.mkdir(
            parents=True,
            exist_ok=True,
        )

    # --------------------------------------------------------

    def _create_formatter(self) -> logging.Formatter:
        """
        Creates the standard enterprise formatter.
        """

        return logging.Formatter(
            fmt=(
                "%(asctime)s | "
                "%(levelname)-8s | "
                "%(name)-20s | "
                "%(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # --------------------------------------------------------

    def _configure_root_logger(self) -> None:
        """
        Configure the root application logger.
        """

        self.root_logger = logging.getLogger("BreakTracker")

        self.root_logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if self.root_logger.handlers:
            return

        # Configure handlers
        self._add_console_handler()
        self._add_application_handler()
        self._add_error_handler()
            # --------------------------------------------------------

    def _add_console_handler(self) -> None:
        """
        Adds console logging for development.
        """

        console_handler = logging.StreamHandler()

        console_handler.setLevel(logging.INFO)

        console_handler.setFormatter(self.formatter)

        self.root_logger.addHandler(console_handler)

    # --------------------------------------------------------

    def _add_application_handler(self) -> None:
        """
        Writes INFO and above messages to application.log.
        """

        handler = RotatingFileHandler(
            filename=self.application_log,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )

        handler.setLevel(logging.INFO)

        handler.setFormatter(self.formatter)

        self.root_logger.addHandler(handler)

    # --------------------------------------------------------

    def _add_error_handler(self) -> None:
        """
        Writes ERROR and CRITICAL messages to error.log.
        """

        handler = RotatingFileHandler(
            filename=self.error_log,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )

        handler.setLevel(logging.ERROR)

        handler.setFormatter(self.formatter)

        self.root_logger.addHandler(handler)

    # --------------------------------------------------------

    def get_logger(
        self,
        name: str,
    ) -> logging.Logger:
        """
        Returns a child logger.

        Example
        -------
        logger = get_logger(__name__)
        """

        return self.root_logger.getChild(name)


# ============================================================
# SINGLETON INSTANCE
# ============================================================

_logging_manager = LoggingManager()


# ============================================================
# PUBLIC API
# ============================================================

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for the given module.

    Example
    -------
    from logger import get_logger

    logger = get_logger(__name__)

    logger.info("Application Started")
    """

    return _logging_manager.get_logger(name)


# ============================================================
# SELF TEST
# ============================================================

if __name__ == "__main__":

    logger = get_logger("LoggerTest")

    logger.debug("Debug message")

    logger.info("Application logger initialized.")

    logger.warning("This is a warning.")

    logger.error("This is an error.")

    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Exception captured successfully.")

    print("Logger module test completed.")