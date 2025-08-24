"""
Configuration service for managing application configuration.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class OpenAIConfig:
    """OpenAI configuration settings"""
    api_key: str = ""
    base_url: str = "https://api.openai.com"
    model: str = "gpt-3.5-turbo"


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    url: str = ""
    username: str = ""
    password: str = ""
    database: str = ""


@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ConfigurationService:
    """Service for managing application configuration"""
    
    def __init__(self):
        self.openai_config = OpenAIConfig()
        self.database_config = DatabaseConfig()
        self.logging_config = LoggingConfig()
    
    def load_config(self, config_data: dict):
        """Load configuration from dictionary"""
        if "openai" in config_data:
            openai_data = config_data["openai"]
            self.openai_config.api_key = openai_data.get("api_key", "")
            self.openai_config.base_url = openai_data.get("base_url", "https://api.openai.com")
            self.openai_config.model = openai_data.get("model", "gpt-3.5-turbo")
        
        if "database" in config_data:
            db_data = config_data["database"]
            self.database_config.url = db_data.get("url", "")
            self.database_config.username = db_data.get("username", "")
            self.database_config.password = db_data.get("password", "")
            self.database_config.database = db_data.get("database", "")
        
        if "logging" in config_data:
            log_data = config_data["logging"]
            self.logging_config.level = log_data.get("level", "INFO")
            self.logging_config.format = log_data.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    def get_openai_config(self) -> OpenAIConfig:
        """Get OpenAI configuration"""
        return self.openai_config
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration"""
        return self.database_config
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration"""
        return self.logging_config

