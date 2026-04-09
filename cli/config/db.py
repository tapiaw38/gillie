"""
Minimal MongoDB helpers for CLI commands.
Connects directly via pymongo using the URI from config.json.
All operations fail silently with a warning so CLI commands
can still update config.json even if MongoDB is unreachable.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _get_profiles_collection():
    from cli.config.manager import config_exists, load_config
    from pymongo import MongoClient

    if not config_exists():
        return None
    try:
        cfg = load_config()
        client = MongoClient(cfg.services.mongodb.uri, serverSelectionTimeoutMS=3000)
        db = client[cfg.services.mongodb.database]
        return db["profiles"]
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB: {e}")
        return None


def _get_user_id() -> Optional[str]:
    try:
        from cli.config.manager import get_user_id
        return get_user_id()
    except Exception:
        return None


def update_provider(active_provider: str, api_key: str = "") -> bool:
    """Set active_provider and store its key in provider_keys."""
    user_id = _get_user_id()
    if not user_id:
        return False

    col = _get_profiles_collection()
    if col is None:
        return False

    try:
        update: Dict[str, Any] = {
            "active_provider": active_provider,
            "updated_at": datetime.now(timezone.utc),
        }
        if api_key:
            update[f"provider_keys.{active_provider}"] = api_key

        result = col.update_one({"user_id": user_id}, {"$set": update})
        return result.matched_count > 0
    except Exception as e:
        logger.warning(f"Could not update provider in MongoDB: {e}")
        return False


def save_custom_provider(
    name: str,
    base_url: str,
    model: str,
    auth_type: str = "api_key",
    api_key: str = "",
) -> bool:
    """Add or update a custom provider entry in the profile."""
    user_id = _get_user_id()
    if not user_id:
        return False

    col = _get_profiles_collection()
    if col is None:
        return False

    try:
        update: Dict[str, Any] = {
            f"custom_providers.{name}": {
                "base_url": base_url,
                "model": model,
                "auth_type": auth_type,
                "api_key": api_key,
            },
            "updated_at": datetime.now(timezone.utc),
        }
        if api_key:
            update[f"provider_keys.{name}"] = api_key

        result = col.update_one({"user_id": user_id}, {"$set": update})
        return result.matched_count > 0
    except Exception as e:
        logger.warning(f"Could not save custom provider in MongoDB: {e}")
        return False


def get_provider_data() -> Dict[str, Any]:
    """Return provider_keys and custom_providers from the profile."""
    user_id = _get_user_id()
    if not user_id:
        return {}

    col = _get_profiles_collection()
    if col is None:
        return {}

    try:
        doc = col.find_one(
            {"user_id": user_id},
            {"provider_keys": 1, "custom_providers": 1, "active_provider": 1},
        )
        return doc or {}
    except Exception as e:
        logger.warning(f"Could not read provider data from MongoDB: {e}")
        return {}
