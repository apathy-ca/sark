"""Configuration management for SARK.

This module provides configuration classes for different deployment profiles:

- Settings: Enterprise deployment (PostgreSQL, Redis, external OPA)
- HomeSettings, HomeDeploymentConfig: Home deployment (SQLite, in-memory, embedded OPA)

Usage:
    # Enterprise deployment
    from sark.config import get_settings
    settings = get_settings()

    # Home deployment
    from sark.config import get_home_config
    config = get_home_config()
"""

from sark.config.home import (
    HomeAuditConfig,
    HomeCacheConfig,
    HomeDatabaseConfig,
    HomeDeploymentConfig,
    HomeEndpointConfig,
    HomeOPAConfig,
    HomeProxyConfig,
    HomeResourceLimits,
    HomeSettings,
    get_home_config,
    get_home_settings,
)
from sark.config.settings import Settings, get_settings

__all__ = [
    # Enterprise settings
    "Settings",
    "get_settings",
    # Home deployment settings
    "HomeSettings",
    "HomeDeploymentConfig",
    "HomeResourceLimits",
    "HomeDatabaseConfig",
    "HomeOPAConfig",
    "HomeAuditConfig",
    "HomeProxyConfig",
    "HomeCacheConfig",
    "HomeEndpointConfig",
    "get_home_settings",
    "get_home_config",
]
