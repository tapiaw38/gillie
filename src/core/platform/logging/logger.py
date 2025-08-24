import logging
import logging.config
import os
from typing import Optional
from pathlib import Path


class LoggerConfig:
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    LOG_DIR = "logs"
    APP_LOG_FILE = "app.log"
    ERROR_LOG_FILE = "error.log"

    @classmethod
    def get_logging_config(cls) -> dict:
        log_dir = Path(cls.LOG_DIR)
        log_dir.mkdir(exist_ok=True)

        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": cls.DEFAULT_LOG_FORMAT,
                    "datefmt": cls.DEFAULT_DATE_FORMAT,
                },
                "detailed": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                    "datefmt": cls.DEFAULT_DATE_FORMAT,
                },
                "simple": {
                    "format": "%(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "DEBUG",
                    "formatter": "detailed",
                    "filename": str(log_dir / cls.APP_LOG_FILE),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                },
                "error_file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "ERROR",
                    "formatter": "detailed",
                    "filename": str(log_dir / cls.ERROR_LOG_FILE),
                    "maxBytes": 10485760,
                    "backupCount": 5,
                },
            },
            "loggers": {
                "": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "src": {
                    "handlers": ["console", "file"],
                    "level": "DEBUG",
                    "propagate": False,
                },
                "src.core": {
                    "handlers": ["console", "file"],
                    "level": "DEBUG",
                    "propagate": False,
                },
                "src.adapters": {
                    "handlers": ["console", "file"],
                    "level": "DEBUG",
                    "propagate": False,
                },
                "src.routes": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
                "fastapi": {
                    "handlers": ["console", "file"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "root": {
                "handlers": ["console", "file", "error_file"],
                "level": "INFO",
            },
        }


def initialize_logging(config: Optional[dict] = None) -> None:
    if config is None:
        config = LoggerConfig.get_logging_config()

    try:
        logging.config.dictConfig(config)
        logging.info("Logging system initialized successfully")
    except Exception as e:
        logging.basicConfig(
            level=getattr(logging, LoggerConfig.DEFAULT_LOG_LEVEL),
            format=LoggerConfig.DEFAULT_LOG_FORMAT,
            datefmt=LoggerConfig.DEFAULT_DATE_FORMAT,
        )
        logging.error(
            f"Failed to initialize advanced logging config: {e}. Using basic config."
        )


def get_logger(name: Optional[str] = None) -> logging.Logger:
    if name is None:
        return logging.getLogger()

    return logging.getLogger(name)


def set_log_level(level: str) -> None:
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logging.getLogger().setLevel(numeric_level)

    for logger_name in ["src", "src.core", "src.adapters", "src.routes"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(numeric_level)

    logging.info(f"Log level changed to {level}")


try:
    initialize_logging()
except Exception:
    logging.basicConfig(
        level=getattr(logging, LoggerConfig.DEFAULT_LOG_LEVEL),
        format=LoggerConfig.DEFAULT_LOG_FORMAT,
    )
