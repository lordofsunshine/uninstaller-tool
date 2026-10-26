import logging
import sys
from logging.handlers import RotatingFileHandler

from app.paths import log_dir

LOGGER_NAME = "uninstaller"


def _formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    try:
        handler = RotatingFileHandler(
            log_dir() / "app.log",
            maxBytes=1_500_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(_formatter())
        logger.addHandler(handler)
    except OSError:
        pass

    if sys.stderr is not None:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(_formatter())
        logger.addHandler(stream)

    return logger


def get_logger(name: str = "") -> logging.Logger:
    suffix = f".{name}" if name else ""
    return logging.getLogger(f"{LOGGER_NAME}{suffix}")
