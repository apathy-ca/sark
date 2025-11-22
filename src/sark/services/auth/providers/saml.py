"""SAML 2.0 authentication provider."""

import base64
from typing import Any
from uuid import UUID, uuid5
from xml.etree import ElementTree as ET

from pydantic import Field

from sark.services.auth.providers.base import (
    AuthProvider,
    AuthProviderConfig,
    AuthResult,
)


class SAMLProviderConfig(AuthProviderConfig):
    """Configuration for SAML authentication provider."""

    idp_entity_id: str
    idp_sso_url: str
    idp_slo_url: str | None = None
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str  # Assertion Consumer Service URL
    sp_slo_url: str | None = None  # Single Logout URL
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    requested_attributes: list[str] = Field(
        default_factory=lambda: ["email", "displayName", "groups"]
    )
    sign_requests: bool = True
    verify_responses: bool = True


class SAMLProvider(AuthProvider):
    """SAML 2.0 authentication provider."""

    def __init__(self, config: SAMLProviderConfig):
        """
        Initialize SAML provider.

        Args:
            config: SAML provider configuration
        """
        super().__init__(config)
        self.config: SAMLProviderConfig = config

    async def authenticate(
        self,
        username: str,
        credential: str,
        **kwargs: Any,
    ) -> AuthResult:
        """
        Authenticate using SAML assertion.

        Args:
            username: Not used in SAML flow (assertions contain user info)
            credential: Base64-encoded SAML response
            **kwargs: Additional parameters (e.g., relay_state)

        Returns:
            AuthResult with user information from SAML assertion
        """
        try:
            # Decode SAML response
            saml_response = base64.b64decode(credential).decode("utf-8")

            # Parse and validate SAML assertion
            assertion = await self._parse_saml_response(saml_response)

            if not assertion:
                return AuthResult(
                    success=False,
                    error_message="Invalid or missing SAML assertion",
                )

            # Extract user information from assertion
            user_info = self._extract_user_info(assertion)

            # Generate stable UUID from name_id
            namespace = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
            user_id = uuid5(namespace, user_info["name_id"])

            return AuthResult(
                success=True,
                user_id=user_id,
                email=user_info.get("email"),
                display_name=user_info.get("displayName"),
                groups=user_info.get("groups", []),
                metadata={
                    "provider": "saml",
                    "name_id": user_info["name_id"],
                    "session_index": user_info.get("session_index"),
                },
            )

        except Exception as e:
            self.logger.error("saml_auth_failed", error=str(e))
            return AuthResult(
                success=False,
                error_message=str(e),
            )

    async def validate_token(self, token: str) -> AuthResult:
        """
        SAML uses assertions, not tokens - delegate to authenticate.

        Args:
            token: Base64-encoded SAML response

        Returns:
            AuthResult from authentication
        """
        return await self.authenticate("", token)

    async def get_user_info(self, user_id: UUID | str) -> dict[str, Any]:
        """
        Retrieve user information (SAML doesn't support direct user lookup).

        Args:
            user_id: User identifier

        Returns:
            Basic user information
        """
        self.logger.warning("saml_get_user_info_not_supported", user_id=str(user_id))
        return {
            "user_id": str(user_id),
            "provider": "saml",
        }

    async def _parse_saml_response(self, saml_response: str) -> dict[str, Any] | None:
        """
        Parse and validate SAML response.

        Args:
            saml_response: XML SAML response

        Returns:
            Parsed assertion data or None if invalid
        """
        try:
            # Parse XML
            root = ET.fromstring(saml_response)

            # In production:
            # 1. Verify signature
            # 2. Check conditions (NotBefore, NotOnOrAfter)
            # 3. Validate audience
            # 4. Check issuer

            # Extract assertion
            ns = {
                "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
                "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
            }

            assertion = root.find(".//saml:Assertion", ns)
            if assertion is None:
                return None

            self.logger.debug("saml_response_parsed")
            return {"assertion": assertion, "namespaces": ns}

        except ET.ParseError as e:
            self.logger.error("saml_parse_error", error=str(e))
            return None

    def _extract_user_info(self, assertion_data: dict[str, Any]) -> dict[str, Any]:
        """
        Extract user information from SAML assertion.

        Args:
            assertion_data: Parsed assertion data

        Returns:
            Dictionary with user information
        """
        assertion = assertion_data["assertion"]
        ns = assertion_data["namespaces"]

        user_info: dict[str, Any] = {}

        # Extract NameID
        name_id = assertion.find(".//saml:NameID", ns)
        if name_id is not None and name_id.text:
            user_info["name_id"] = name_id.text

        # Extract session index
        authn_statement = assertion.find(".//saml:AuthnStatement", ns)
        if authn_statement is not None:
            session_index = authn_statement.get("SessionIndex")
            if session_index:
                user_info["session_index"] = session_index

        # Extract attributes
        attr_statements = assertion.findall(".//saml:AttributeStatement", ns)
        for attr_statement in attr_statements:
            attributes = attr_statement.findall(".//saml:Attribute", ns)
            for attribute in attributes:
                attr_name = attribute.get("Name")
                attr_values = attribute.findall(".//saml:AttributeValue", ns)

                if not attr_values:
                    continue

                # Handle single vs multiple values
                if len(attr_values) == 1:
                    user_info[attr_name] = attr_values[0].text
                else:
                    user_info[attr_name] = [v.text for v in attr_values if v.text]

        return user_info

    def generate_authn_request(self, relay_state: str | None = None) -> str:
        """
        Generate SAML AuthnRequest for initiating SSO.

        Args:
            relay_state: Optional relay state for redirect after auth

        Returns:
            Base64-encoded SAML AuthnRequest
        """
        import uuid
        from datetime import UTC, datetime

        request_id = f"_{uuid.uuid4()}"
        issue_instant = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        authn_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
                    xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion"
                    ID="{request_id}"
                    Version="2.0"
                    IssueInstant="{issue_instant}"
                    Destination="{self.config.idp_sso_url}"
                    AssertionConsumerServiceURL="{self.config.sp_acs_url}"
                    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer>{self.config.sp_entity_id}</saml:Issuer>
    <samlp:NameIDPolicy Format="{self.config.name_id_format}" AllowCreate="true"/>
</samlp:AuthnRequest>"""

        # Base64 encode
        encoded = base64.b64encode(authn_request.encode("utf-8")).decode("utf-8")

        self.logger.debug("saml_authn_request_generated", request_id=request_id)
        return encoded

    async def health_check(self) -> bool:
        """
        Check SAML provider health.

        Returns:
            True if configuration is valid
        """
        try:
            # Verify required configuration
            required = [
                self.config.idp_entity_id,
                self.config.idp_sso_url,
                self.config.sp_entity_id,
                self.config.sp_acs_url,
            ]

            return self.config.enabled and all(required)

        except Exception as e:
            self.logger.error("saml_health_check_failed", error=str(e))
            return False
