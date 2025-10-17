"""
Scope Configuration Utilities

Note: These functions use os.getenv() as they are low-level helpers
that may be called before ConfigurationService is initialized.

For application code, prefer using:
    from src.core.platform.config.service import get_config_service
    config = get_config_service()
    scope = config.logging_config.scope
"""

import os

PROD_SCOPE = "prod"
TEST_SCOPE = "test"

def get_scope() -> str:
    """Get current scope from environment (prod/test/local)"""
    return os.getenv("SCOPE", "")

def is_prod_scope() -> bool:
    """Check if running in production scope"""
    return get_scope() == PROD_SCOPE

def is_test_scope() -> bool:
    """Check if running in test scope"""
    return get_scope() == TEST_SCOPE

def is_local_scope() -> bool:
    """Check if running in local scope"""
    return get_scope() == ""