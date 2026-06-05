import logging
import sys

from app.config import settings


def setup_logging() -> None:
    log_level_name = getattr(settings, "LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root_logger.addHandler(handler)
