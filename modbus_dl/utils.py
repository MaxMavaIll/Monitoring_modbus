import logging
import os

from logging.handlers import TimedRotatingFileHandler

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_FORMAT = "%(asctime)s [%(levelname)s] " \
                "%(filename)s:%(funcName)s:%(lineno)d: %(message)s"

def setup_logging(
        file_w_level: logging.FileHandler = logging.DEBUG,
        comsole_level: logging.StreamHandler = logging.INFO,
) -> logging.Logger:
    logger = logging.getLogger("octo")
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:

        file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", interval=1,
                                                backupCount=7, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        file_handler.setLevel(file_w_level)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        console_handler.setLevel(comsole_level)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

def initialize_environment(
        LOG_DIR: str = 'logs'
):
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

