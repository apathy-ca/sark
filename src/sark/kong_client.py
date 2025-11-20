"""
Kong API Gateway client for SARK application.

This module provides utilities for interacting with Kong API Gateway,
supporting both managed (Docker Compose) and external enterprise deployments.
"""

import logging
from typing import Any

import httpx

from sark.config import KongConfig

logger = logging.getLogger(__name__)


class KongClient:
    """Client for interacting with Kong Admin API."""

    def __init__(self, config: KongConfig):
        """
        Initialize Kong client.

        Args:
            config: Kong configuration
        """
        self.config = config
        self.admin_url = config.admin_url.rstrip("/")
        self.proxy_url = config.proxy_url.rstrip("/")

        # Setup headers
        headers = {"Content-Type": "application/json"}
        if config.admin_api_key:
            headers["Kong-Admin-Token"] = config.admin_api_key

        # Create HTTP client
        self.client = httpx.Client(
            headers=headers,
            timeout=config.timeout,
            verify=config.verify_ssl,
        )

        logger.info(
            f"Initialized Kong client in {config.mode} mode: admin={self.admin_url}, "
            f"proxy={self.proxy_url}, workspace={config.workspace}"
        )

    def health_check(self) -> bool:
        """
        Check if Kong is healthy and accessible.

        Returns:
            True if Kong is healthy, False otherwise
        """
        try:
            response = self.client.get(f"{self.admin_url}/status")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Kong health check successful: {data}")
            return True
        except Exception as e:
            logger.error(f"Kong health check failed: {e}")
            return False

    def get_services(self) -> list[dict[str, Any]]:
        """
        Get all services registered in Kong.

        Returns:
            List of Kong services

        Raises:
            httpx.HTTPError: If the request fails
        """
        workspace_path = f"/{self.config.workspace}" if self.config.workspace != "default" else ""
        url = f"{self.admin_url}{workspace_path}/services"

        response = self.client.get(url)
        response.raise_for_status()
        return response.json().get("data", [])

    def create_service(
        self, name: str, url: str, protocol: str = "http", retries: int = 5
    ) -> dict[str, Any]:
        """
        Create a new service in Kong.

        Args:
            name: Service name
            url: Backend service URL
            protocol: Protocol (http, https, grpc, grpcs)
            retries: Number of retries

        Returns:
            Created service data

        Raises:
            httpx.HTTPError: If the request fails
        """
        workspace_path = f"/{self.config.workspace}" if self.config.workspace != "default" else ""
        endpoint = f"{self.admin_url}{workspace_path}/services"

        payload = {
            "name": name,
            "url": url,
            "protocol": protocol,
            "retries": retries,
        }

        response = self.client.post(endpoint, json=payload)
        response.raise_for_status()
        logger.info(f"Created Kong service: {name}")
        return response.json()

    def create_route(
        self,
        service_name: str,
        paths: list[str],
        methods: list[str] | None = None,
        strip_path: bool = True,
    ) -> dict[str, Any]:
        """
        Create a route for a service.

        Args:
            service_name: Name of the service to route to
            paths: URL paths for this route
            methods: HTTP methods (GET, POST, etc.)
            strip_path: Whether to strip the path prefix

        Returns:
            Created route data

        Raises:
            httpx.HTTPError: If the request fails
        """
        workspace_path = f"/{self.config.workspace}" if self.config.workspace != "default" else ""
        endpoint = f"{self.admin_url}{workspace_path}/services/{service_name}/routes"

        payload = {
            "paths": paths,
            "strip_path": strip_path,
        }
        if methods:
            payload["methods"] = methods

        response = self.client.post(endpoint, json=payload)
        response.raise_for_status()
        logger.info(f"Created Kong route for service {service_name}: {paths}")
        return response.json()

    def add_plugin(
        self,
        plugin_name: str,
        config: dict[str, Any] | None = None,
        service_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Add a plugin to Kong.

        Args:
            plugin_name: Name of the plugin (e.g., 'rate-limiting', 'jwt')
            config: Plugin configuration
            service_name: If specified, apply plugin to specific service

        Returns:
            Created plugin data

        Raises:
            httpx.HTTPError: If the request fails
        """
        workspace_path = f"/{self.config.workspace}" if self.config.workspace != "default" else ""

        if service_name:
            endpoint = f"{self.admin_url}{workspace_path}/services/{service_name}/plugins"
        else:
            endpoint = f"{self.admin_url}{workspace_path}/plugins"

        payload = {"name": plugin_name}
        if config:
            payload["config"] = config

        response = self.client.post(endpoint, json=payload)
        response.raise_for_status()
        logger.info(f"Added Kong plugin {plugin_name} to {service_name or 'global'}")
        return response.json()

    def get_workspace_info(self) -> dict[str, Any]:
        """
        Get information about the current workspace (Kong Enterprise only).

        Returns:
            Workspace information

        Raises:
            httpx.HTTPError: If the request fails or workspaces not supported
        """
        if self.config.workspace == "default":
            return {"name": "default", "comment": "Default workspace"}

        endpoint = f"{self.admin_url}/workspaces/{self.config.workspace}"
        response = self.client.get(endpoint)
        response.raise_for_status()
        return response.json()

    def test_connection(self) -> dict[str, Any]:
        """
        Test connection to Kong and return diagnostic information.

        Returns:
            Dictionary containing connection test results
        """
        result = {
            "mode": self.config.mode.value,
            "admin_url": self.admin_url,
            "proxy_url": self.proxy_url,
            "workspace": self.config.workspace,
            "healthy": False,
            "version": None,
            "error": None,
        }

        try:
            # Check health
            response = self.client.get(f"{self.admin_url}/status")
            response.raise_for_status()
            result["healthy"] = True

            # Get version info
            response = self.client.get(f"{self.admin_url}/")
            response.raise_for_status()
            data = response.json()
            result["version"] = data.get("version")

            logger.info(f"Kong connection test successful: {result}")
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Kong connection test failed: {e}")

        return result

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "KongClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


def create_kong_client(config: KongConfig | None = None) -> KongClient | None:
    """
    Create a Kong client instance.

    Args:
        config: Kong configuration (if None, loads from environment)

    Returns:
        KongClient instance if Kong is enabled, None otherwise
    """
    if config is None:
        from sark.config import get_config

        app_config = get_config()
        config = app_config.kong

    if not config.enabled:
        logger.info("Kong is not enabled")
        return None

    return KongClient(config)


def verify_kong_connectivity(config: KongConfig | None = None) -> bool:
    """
    Verify connectivity to Kong.

    Args:
        config: Kong configuration (if None, loads from environment)

    Returns:
        True if Kong is accessible, False otherwise
    """
    client = create_kong_client(config)
    if client is None:
        return False

    try:
        return client.health_check()
    finally:
        client.close()
