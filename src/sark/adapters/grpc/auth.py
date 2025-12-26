"""
gRPC Authentication Interceptors and Helpers.

This module provides authentication mechanisms for gRPC:
- Token-based authentication (Bearer tokens, API keys)
- Metadata injection for authentication headers
- Support for various auth schemes

Version: 2.0.0
Engineer: ENGINEER-3
"""

from collections.abc import Callable
from typing import Any

import grpc
from grpc import aio
import structlog

logger = structlog.get_logger(__name__)


class TokenAuthInterceptor(aio.UnaryUnaryClientInterceptor):
    """
    gRPC client interceptor for token-based authentication.

    Injects authentication tokens into request metadata automatically.

    Supports:
    - Bearer tokens (OAuth, JWT)
    - API keys (custom header or query param)
    - Custom authentication schemes

    Example:
        >>> interceptor = TokenAuthInterceptor(token="my-bearer-token", scheme="bearer")
        >>> channel = grpc.aio.insecure_channel("localhost:50051")
        >>> channel = grpc.intercept_channel(channel, interceptor)
    """

    def __init__(
        self,
        token: str,
        scheme: str = "bearer",
        header_name: str = "authorization",
    ):
        """
        Initialize token auth interceptor.

        Args:
            token: Authentication token
            scheme: Authentication scheme ("bearer", "apikey", "custom")
            header_name: Metadata header name (default: "authorization")
        """
        self._token = token
        self._scheme = scheme.lower()
        self._header_name = header_name.lower()

        logger.debug(
            "token_auth_interceptor_initialized",
            scheme=self._scheme,
            header=self._header_name,
        )

    async def intercept_unary_unary(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """
        Intercept unary-unary RPC to inject authentication.

        Args:
            continuation: Next interceptor or actual RPC call
            client_call_details: Call details
            request: Request message

        Returns:
            Response from the RPC call
        """
        # Build authentication metadata
        auth_metadata = self._build_auth_metadata()

        # Merge with existing metadata
        metadata = list(client_call_details.metadata or [])
        metadata.extend(auth_metadata)

        # Create new call details with auth metadata
        new_details = grpc.aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )

        logger.debug(
            "injecting_auth_metadata",
            method=client_call_details.method,
            scheme=self._scheme,
        )

        # Continue with augmented call details
        return await continuation(new_details, request)

    def _build_auth_metadata(self) -> list:
        """
        Build authentication metadata based on scheme.

        Returns:
            List of metadata tuples
        """
        if self._scheme == "bearer":
            # Bearer token (OAuth, JWT)
            return [(self._header_name, f"Bearer {self._token}")]

        elif self._scheme == "apikey":
            # API key (plain token)
            return [(self._header_name, self._token)]

        elif self._scheme == "custom":
            # Custom scheme (token as-is)
            return [(self._header_name, self._token)]

        else:
            logger.warning("unknown_auth_scheme", scheme=self._scheme)
            return [(self._header_name, self._token)]


class MetadataInjectorInterceptor(aio.UnaryUnaryClientInterceptor):
    """
    Generic metadata injector for gRPC requests.

    Injects arbitrary metadata headers into all requests.

    Example:
        >>> metadata = {"x-api-version": "v1", "x-client-id": "123"}
        >>> interceptor = MetadataInjectorInterceptor(metadata)
        >>> channel = grpc.intercept_channel(channel, interceptor)
    """

    def __init__(self, metadata: dict[str, str]):
        """
        Initialize metadata injector.

        Args:
            metadata: Dictionary of metadata to inject
        """
        self._metadata = metadata
        logger.debug(
            "metadata_injector_initialized",
            metadata_keys=list(metadata.keys()),
        )

    async def intercept_unary_unary(
        self,
        continuation: Callable,
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        """
        Intercept RPC to inject metadata.

        Args:
            continuation: Next interceptor or actual RPC call
            client_call_details: Call details
            request: Request message

        Returns:
            Response from the RPC call
        """
        # Convert dict to metadata tuples
        injected_metadata = [(key, value) for key, value in self._metadata.items()]

        # Merge with existing metadata
        metadata = list(client_call_details.metadata or [])
        metadata.extend(injected_metadata)

        # Create new call details
        new_details = grpc.aio.ClientCallDetails(
            method=client_call_details.method,
            timeout=client_call_details.timeout,
            metadata=metadata,
            credentials=client_call_details.credentials,
            wait_for_ready=client_call_details.wait_for_ready,
        )

        return await continuation(new_details, request)


class AuthenticationHelper:
    """
    Helper class for managing gRPC authentication.

    Provides utilities for:
    - Creating auth interceptors
    - Building credentials
    - Managing auth tokens
    """

    @staticmethod
    def create_bearer_token_interceptor(token: str) -> TokenAuthInterceptor:
        """
        Create interceptor for Bearer token authentication.

        Args:
            token: Bearer token (JWT, OAuth token, etc.)

        Returns:
            Configured TokenAuthInterceptor
        """
        return TokenAuthInterceptor(token=token, scheme="bearer", header_name="authorization")

    @staticmethod
    def create_api_key_interceptor(
        api_key: str, header_name: str = "x-api-key"
    ) -> TokenAuthInterceptor:
        """
        Create interceptor for API key authentication.

        Args:
            api_key: API key
            header_name: Header name for API key

        Returns:
            Configured TokenAuthInterceptor
        """
        return TokenAuthInterceptor(token=api_key, scheme="apikey", header_name=header_name)

    @staticmethod
    def create_custom_header_interceptor(
        header_name: str, header_value: str
    ) -> TokenAuthInterceptor:
        """
        Create interceptor for custom header authentication.

        Args:
            header_name: Custom header name
            header_value: Header value

        Returns:
            Configured TokenAuthInterceptor
        """
        return TokenAuthInterceptor(token=header_value, scheme="custom", header_name=header_name)

    @staticmethod
    def apply_interceptors(channel: aio.Channel, interceptors: list) -> aio.Channel:
        """
        Apply multiple interceptors to a channel.

        Args:
            channel: Base gRPC channel
            interceptors: List of interceptor instances

        Returns:
            Intercepted channel
        """
        intercepted_channel = channel

        for interceptor in interceptors:
            intercepted_channel = grpc.intercept_channel(intercepted_channel, interceptor)

        logger.info("interceptors_applied", count=len(interceptors))

        return intercepted_channel


def create_authenticated_channel(
    endpoint: str,
    auth_config: dict[str, Any],
    use_tls: bool = False,
    tls_credentials: grpc.ChannelCredentials | None = None,
    channel_options: list | None = None,
) -> aio.Channel:
    """
    Create an authenticated gRPC channel.

    Args:
        endpoint: Server endpoint (host:port)
        auth_config: Authentication configuration
            - type: "bearer", "apikey", "custom", or "none"
            - token: Authentication token
            - header_name: Optional custom header name
        use_tls: Whether to use TLS
        tls_credentials: Optional TLS credentials
        channel_options: Optional channel options

    Returns:
        Configured and authenticated gRPC channel

    Example:
        >>> auth_config = {"type": "bearer", "token": "eyJ..."}
        >>> channel = create_authenticated_channel(
        ...     endpoint="api.example.com:443",
        ...     auth_config=auth_config,
        ...     use_tls=True
        ... )
    """
    # Create base channel
    if use_tls:
        if tls_credentials:
            channel = aio.secure_channel(endpoint, tls_credentials, options=channel_options)
        else:
            channel = aio.secure_channel(
                endpoint,
                grpc.ssl_channel_credentials(),
                options=channel_options,
            )
    else:
        channel = aio.insecure_channel(endpoint, options=channel_options)

    # Apply authentication if configured
    auth_type = auth_config.get("type", "none")

    if auth_type == "none":
        logger.debug("no_authentication_configured", endpoint=endpoint)
        return channel

    # Create appropriate interceptor
    interceptors = []

    if auth_type == "bearer":
        token = auth_config.get("token")
        if token:
            interceptor = AuthenticationHelper.create_bearer_token_interceptor(token)
            interceptors.append(interceptor)

    elif auth_type == "apikey":
        api_key = auth_config.get("token")
        header_name = auth_config.get("header_name", "x-api-key")
        if api_key:
            interceptor = AuthenticationHelper.create_api_key_interceptor(api_key, header_name)
            interceptors.append(interceptor)

    elif auth_type == "custom":
        header_name = auth_config.get("header_name", "authorization")
        header_value = auth_config.get("token")
        if header_name and header_value:
            interceptor = AuthenticationHelper.create_custom_header_interceptor(
                header_name, header_value
            )
            interceptors.append(interceptor)

    # Apply additional metadata if provided
    if "metadata" in auth_config and isinstance(auth_config["metadata"], dict):
        metadata_interceptor = MetadataInjectorInterceptor(auth_config["metadata"])
        interceptors.append(metadata_interceptor)

    # Apply all interceptors
    if interceptors:
        channel = AuthenticationHelper.apply_interceptors(channel, interceptors)
        logger.info(
            "authenticated_channel_created",
            endpoint=endpoint,
            auth_type=auth_type,
            interceptor_count=len(interceptors),
        )
    else:
        logger.warning(
            "no_interceptors_configured",
            endpoint=endpoint,
            auth_type=auth_type,
        )

    return channel


__all__ = [
    "AuthenticationHelper",
    "MetadataInjectorInterceptor",
    "TokenAuthInterceptor",
    "create_authenticated_channel",
]
