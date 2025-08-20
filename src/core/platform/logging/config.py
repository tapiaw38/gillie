import os
from typing import Dict, Any
from .logger import LoggerConfig


class EnvironmentLoggerConfig:
    @staticmethod
    def get_development_config() -> Dict[str, Any]:
        base_config = LoggerConfig.get_logging_config()

        base_config["handlers"]["console"]["level"] = "DEBUG"
        base_config["handlers"]["file"]["level"] = "DEBUG"
        base_config["loggers"]["src"]["level"] = "DEBUG"
        base_config["loggers"]["src.core"]["level"] = "DEBUG"
        base_config["loggers"]["src.adapters"]["level"] = "DEBUG"

        return base_config

    @staticmethod
    def get_production_config() -> Dict[str, Any]:
        base_config = LoggerConfig.get_logging_config()

        base_config["handlers"]["console"]["level"] = "WARNING"
        base_config["handlers"]["file"]["level"] = "INFO"
        base_config["loggers"]["src"]["level"] = "INFO"
        base_config["loggers"]["src.core"]["level"] = "INFO"
        base_config["loggers"]["src.adapters"]["level"] = "INFO"

        base_config["handlers"]["file"]["maxBytes"] = 52428800
        base_config["handlers"]["file"]["backupCount"] = 10
        base_config["handlers"]["error_file"]["maxBytes"] = 52428800
        base_config["handlers"]["error_file"]["backupCount"] = 10

        return base_config

    @staticmethod
    def get_testing_config() -> Dict[str, Any]:
        base_config = LoggerConfig.get_logging_config()

        base_config["handlers"]["file"]["level"] = "CRITICAL"
        base_config["handlers"]["error_file"]["level"] = "CRITICAL"
        base_config["loggers"]["src"]["level"] = "DEBUG"

        return base_config

    @staticmethod
    def get_docker_config() -> Dict[str, Any]:
        base_config = LoggerConfig.get_logging_config()

        base_config["handlers"]["file"]["level"] = "CRITICAL"
        base_config["handlers"]["error_file"]["level"] = "CRITICAL"
        base_config["formatters"]["console"] = {
            "format": "%(levelname)s - %(name)s - %(message)s",
        }

        return base_config


def get_environment_config() -> Dict[str, Any]:
    env = os.getenv("ENVIRONMENT", "development").lower()

    if env == "production":
        return EnvironmentLoggerConfig.get_production_config()
    elif env == "testing":
        return EnvironmentLoggerConfig.get_testing_config()
    elif env == "docker":
        return EnvironmentLoggerConfig.get_docker_config()
    else:
        return EnvironmentLoggerConfig.get_development_config()


def get_log_level_from_env() -> str:
    return os.getenv("LOG_LEVEL", LoggerConfig.DEFAULT_LOG_LEVEL).upper()


def should_log_to_file() -> bool:
    env = os.getenv("ENVIRONMENT", "development").lower()
    return env not in ["testing", "docker"]
