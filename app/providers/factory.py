"""
Factory for creating search provider instances based on configuration.
"""

import logging
from typing import List

from app.providers.base import SearchProvider
from app.providers.algolia_provider import AlgoliaProvider
from app.providers.typesense_provider import TypesenseProvider
from app.config import Settings
from app.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


def get_providers(
    settings: Settings, settings_manager: SettingsManager
) -> List[SearchProvider]:
    """
    Get list of enabled search providers based on configuration.

    Checks both Settings class (for credentials) and SettingsManager (for enable/disable flags).
    A provider is enabled only if:
    1. It has required configuration in Settings (app_id, api_key, etc.)
    2. It is enabled in AppSetting model (provider.{name}.enabled)

    Args:
        settings: Application settings (from environment variables)
        settings_manager: Settings manager for reading AppSetting model

    Returns:
        List[SearchProvider]: List of enabled provider instances
    """
    providers: List[SearchProvider] = []

    # Check Algolia
    if is_provider_enabled("algolia", settings, settings_manager):
        try:
            providers.append(AlgoliaProvider(settings))
            logger.info("Algolia provider enabled")
        except Exception as e:
            logger.error(f"Failed to initialize Algolia provider: {e}")

    # Check Typesense
    if is_provider_enabled("typesense", settings, settings_manager):
        try:
            providers.append(TypesenseProvider(settings))
            logger.info("Typesense provider enabled")
        except Exception as e:
            logger.error(f"Failed to initialize Typesense provider: {e}")

    return providers


def is_provider_enabled(
    provider_name: str, settings: Settings, settings_manager: SettingsManager
) -> bool:
    """
    Check if a provider is enabled.

    A provider is enabled if:
    1. It has required configuration in Settings
    2. The enable flag in AppSetting is "true" (or not set, defaults to enabled if configured)

    Args:
        provider_name: Name of the provider (e.g., "algolia")
        settings: Application settings
        settings_manager: Settings manager

    Returns:
        bool: True if provider should be enabled
    """
    # Check if provider has required configuration
    has_config = False
    if provider_name == "algolia":
        has_config = bool(settings.algolia_app_id and settings.algolia_api_key)
    elif provider_name == "typesense":
        has_config = bool(settings.typesense_host and settings.typesense_api_key)
    else:
        return False

    if not has_config:
        return False

    # Check enable/disable flag in AppSetting
    enabled_flag = settings_manager.get(f"provider.{provider_name}.enabled")
    if enabled_flag is None:
        # If not set, default to enabled if configuration is present
        return True

    # Convert string to boolean
    return (
        enabled_flag.lower() == "true"
        if isinstance(enabled_flag, str)
        else bool(enabled_flag)
    )
