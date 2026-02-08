import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(app_name, log_dir="logs", level="INFO", max_bytes=5_000_000, backup_count=3):
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    os.makedirs(log_dir, exist_ok=True)
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(levelname)s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_path = os.path.join(log_dir, f"{app_name}.log")
    file_handler = RotatingFileHandler(
        file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
