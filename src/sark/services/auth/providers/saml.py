"""SAML 2.0 authentication provider.

Supports SAML-based Single Sign-On (SSO) with:
- Azure AD SAML
- Okta SAML
- Any SAML 2.0 compliant Identity Provider
"""

from typing import Any
from urllib.parse import urlparse

from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings
from onelogin.saml2.utils import OneLogin_Saml2_Utils

from .base import AuthProvider, UserInfo


class SAMLProvider(AuthProvider):
    """SAML 2.0 authentication provider.

    Implements SAML-based Single Sign-On with support for major Identity Providers
    including Azure AD, Okta, and any SAML 2.0 compliant IdP.
    """

    def __init__(
        self,
        sp_entity_id: str,
        sp_acs_url: str,
        sp_sls_url: str,
        idp_entity_id: str,
        idp_sso_url: str,
        idp_slo_url: str | None = None,
        idp_x509_cert: str | None = None,
        idp_metadata_url: str | None = None,
        sp_x509_cert: str | None = None,
        sp_private_key: str | None = None,
        name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
        want_assertions_signed: bool = True,
        want_messages_signed: bool = False,
        want_name_id_encrypted: bool = False,
        attribute_mapping: dict[str, str] | None = None,
    ):
        """Initialize SAML provider.

        Args:
            sp_entity_id: Service Provider entity ID (usually your app's URL)
            sp_acs_url: Assertion Consumer Service URL (callback URL)
            sp_sls_url: Single Logout Service URL
            idp_entity_id: Identity Provider entity ID
            idp_sso_url: IdP Single Sign-On URL
            idp_slo_url: IdP Single Logout URL (optional)
            idp_x509_cert: IdP X.509 certificate (PEM format, without headers)
            idp_metadata_url: IdP metadata URL (alternative to manual config)
            sp_x509_cert: SP X.509 certificate for signing (optional)
            sp_private_key: SP private key for signing (optional)
            name_id_format: NameID format
            want_assertions_signed: Require signed assertions
            want_messages_signed: Require signed messages
            want_name_id_encrypted: Require encrypted NameID
            attribute_mapping: Custom attribute mapping (IdP attr -> standard attr)
        """
        self.sp_entity_id = sp_entity_id
        self.sp_acs_url = sp_acs_url
        self.sp_sls_url = sp_sls_url
        self.idp_entity_id = idp_entity_id
        self.idp_sso_url = idp_sso_url
        self.idp_slo_url = idp_slo_url
        self.idp_x509_cert = idp_x509_cert
        self.idp_metadata_url = idp_metadata_url
        self.sp_x509_cert = sp_x509_cert
        self.sp_private_key = sp_private_key
        self.name_id_format = name_id_format
        self.want_assertions_signed = want_assertions_signed
        self.want_messages_signed = want_messages_signed
        self.want_name_id_encrypted = want_name_id_encrypted

        # Default attribute mapping (can be customized per IdP)
        self.attribute_mapping = attribute_mapping or {
            # Azure AD
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": "email",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name": "name",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname": "given_name",
            "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname": "family_name",
            "http://schemas.microsoft.com/ws/2008/06/identity/claims/groups": "groups",
            # Okta
            "email": "email",
            "firstName": "given_name",
            "lastName": "family_name",
            "groups": "groups",
        }

        # Build SAML settings
        self._settings = self._build_saml_settings()

    def _build_saml_settings(self) -> dict[str, Any]:
        """Build python3-saml settings dictionary.

        Returns:
            SAML settings dictionary
        """
        settings = {
            "strict": True,
            "debug": False,
            "sp": {
                "entityId": self.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
                "singleLogoutService": {
                    "url": self.sp_sls_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "NameIDFormat": self.name_id_format,
            },
            "idp": {
                "entityId": self.idp_entity_id,
                "singleSignOnService": {
                    "url": self.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
            },
            "security": {
                "nameIdEncrypted": self.want_name_id_encrypted,
                "authnRequestsSigned": bool(self.sp_private_key),
                "logoutRequestSigned": bool(self.sp_private_key),
                "logoutResponseSigned": bool(self.sp_private_key),
                "signMetadata": bool(self.sp_private_key),
                "wantMessagesSigned": self.want_messages_signed,
                "wantAssertionsSigned": self.want_assertions_signed,
                "wantAssertionsEncrypted": False,
                "wantNameIdEncrypted": self.want_name_id_encrypted,
                "requestedAuthnContext": True,
            },
        }

        # Add Single Logout Service if provided
        if self.idp_slo_url:
            settings["idp"]["singleLogoutService"] = {
                "url": self.idp_slo_url,
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            }

        # Add IdP certificate if provided
        if self.idp_x509_cert:
            settings["idp"]["x509cert"] = self.idp_x509_cert

        # Add SP certificate and key if provided
        if self.sp_x509_cert and self.sp_private_key:
            settings["sp"]["x509cert"] = self.sp_x509_cert
            settings["sp"]["privateKey"] = self.sp_private_key

        return settings

    async def authenticate(self, credentials: dict[str, Any]) -> UserInfo | None:
        """Authenticate user with SAML assertion.

        Args:
            credentials: Dictionary with 'saml_response' and 'relay_state'

        Returns:
            UserInfo object if authentication successful, None otherwise
        """
        saml_response = credentials.get("saml_response")
        if not saml_response:
            return None

        try:
            # Create auth object with mock request data
            req = self._prepare_request(credentials)
            auth = OneLogin_Saml2_Auth(req, self._settings)

            # Process SAML response
            auth.process_response()

            # Check for errors
            if auth.get_errors():
                print(f"SAML authentication errors: {auth.get_errors()}")
                return None

            # Check if authenticated
            if not auth.is_authenticated():
                return None

            # Extract user info from assertion
            return self._extract_user_info_from_auth(auth)

        except Exception as e:
            print(f"SAML authentication failed: {e}")
            return None

    async def validate_token(self, token: str) -> UserInfo | None:
        """Validate SAML session token.

        Note: SAML doesn't use bearer tokens like OIDC. This method is for
        session token validation after initial SAML authentication.

        Args:
            token: Session token (typically stored after SAML authentication)

        Returns:
            UserInfo object if token is valid, None otherwise
        """
        # SAML uses session-based authentication, not stateless tokens
        # This would typically validate a session ID against your session store
        # For now, we'll indicate this needs custom implementation
        raise NotImplementedError(
            "SAML uses session-based authentication. "
            "Implement session validation in your application."
        )

    async def refresh_token(self, refresh_token: str) -> dict[str, str] | None:
        """Refresh SAML session.

        SAML doesn't support token refresh. Users must re-authenticate.

        Args:
            refresh_token: Not applicable for SAML

        Returns:
            None (SAML doesn't support refresh)
        """
        return None

    async def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        """Get SAML SSO URL.

        Args:
            state: RelayState for maintaining application state
            redirect_uri: Not used in SAML (ACS URL is pre-configured)

        Returns:
            SAML SSO URL with embedded AuthnRequest
        """
        try:
            # Create auth object with minimal request
            req = self._prepare_request({"relay_state": state})
            auth = OneLogin_Saml2_Auth(req, self._settings)

            # Generate SSO URL with embedded AuthnRequest
            sso_url = auth.login(return_to=state)
            return sso_url

        except Exception as e:
            print(f"Failed to generate SAML SSO URL: {e}")
            return self.idp_sso_url

    async def handle_callback(
        self, code: str, state: str, redirect_uri: str
    ) -> dict[str, str] | None:
        """Handle SAML callback (ACS).

        Note: SAML uses POST binding, so this method expects the SAML response
        in the 'code' parameter (which should contain the full SAML response).

        Args:
            code: SAML response (SAMLResponse parameter)
            state: RelayState parameter
            redirect_uri: Not used in SAML

        Returns:
            Dictionary with user attributes or None if authentication failed
        """
        credentials = {"saml_response": code, "relay_state": state}
        user_info = await self.authenticate(credentials)

        if user_info:
            # Return user info as dictionary
            return {
                "user_id": user_info.user_id,
                "email": user_info.email,
                "name": user_info.name or "",
                "authenticated": "true",
            }
        return None

    async def health_check(self) -> bool:
        """Check if SAML IdP is reachable.

        Returns:
            True if IdP metadata/SSO endpoint is reachable, False otherwise
        """
        try:
            import httpx

            # Try to fetch IdP metadata if URL provided
            if self.idp_metadata_url:
                async with httpx.AsyncClient() as client:
                    response = await client.get(self.idp_metadata_url, timeout=5.0)
                    return response.status_code == 200

            # Otherwise, basic check if SSO URL is valid
            parsed = urlparse(self.idp_sso_url)
            return bool(parsed.scheme and parsed.netloc)

        except Exception:
            return False

    def get_metadata(self) -> str:
        """Get Service Provider metadata XML.

        Returns:
            SP metadata as XML string
        """
        settings = OneLogin_Saml2_Settings(self._settings)
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)

        if errors:
            raise ValueError(f"Invalid SP metadata: {errors}")

        return metadata

    def _prepare_request(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Prepare request dictionary for python3-saml.

        Args:
            credentials: Request data including SAML response, relay state, etc.

        Returns:
            Request dictionary compatible with python3-saml
        """
        # Extract ACS URL components
        parsed_acs = urlparse(self.sp_acs_url)

        # Build request dict
        req = {
            "https": "on" if parsed_acs.scheme == "https" else "off",
            "http_host": parsed_acs.netloc,
            "script_name": parsed_acs.path,
            "server_port": parsed_acs.port or (443 if parsed_acs.scheme == "https" else 80),
            "get_data": {},
            "post_data": {},
        }

        # Add SAML response if present
        if "saml_response" in credentials:
            req["post_data"]["SAMLResponse"] = credentials["saml_response"]

        # Add RelayState if present
        if "relay_state" in credentials:
            req["post_data"]["RelayState"] = credentials["relay_state"]

        return req

    def _extract_user_info_from_auth(self, auth: OneLogin_Saml2_Auth) -> UserInfo:
        """Extract user information from authenticated SAML response.

        Args:
            auth: Authenticated OneLogin_Saml2_Auth object

        Returns:
            UserInfo object
        """
        # Get NameID (typically email)
        name_id = auth.get_nameid()

        # Get attributes from assertion
        raw_attributes = auth.get_attributes()

        # Map attributes to standard names
        attributes = self._map_attributes(raw_attributes)

        # Extract standard fields
        user_id = name_id or attributes.get("email", "")
        email = attributes.get("email", name_id or "")
        name = attributes.get("name")
        given_name = attributes.get("given_name")
        family_name = attributes.get("family_name")

        # Extract groups (may be list or single value)
        groups = attributes.get("groups")
        if groups and not isinstance(groups, list):
            groups = [groups]

        return UserInfo(
            user_id=user_id,
            email=email,
            name=name,
            given_name=given_name,
            family_name=family_name,
            groups=groups,
            attributes=attributes,
        )

    def _map_attributes(self, raw_attributes: dict[str, list[str]]) -> dict[str, Any]:
        """Map IdP-specific attributes to standard attribute names.

        Args:
            raw_attributes: Raw attributes from SAML assertion

        Returns:
            Dictionary with mapped attribute names
        """
        mapped = {}

        for raw_key, values in raw_attributes.items():
            # Get mapped key or use original
            mapped_key = self.attribute_mapping.get(raw_key, raw_key)

            # Extract value (take first item if list)
            value = values[0] if values and len(values) == 1 else values

            mapped[mapped_key] = value

        return mapped

    async def process_logout_request(self, logout_request: str) -> str:
        """Process SAML logout request from IdP.

        Args:
            logout_request: SAML LogoutRequest XML

        Returns:
            SAML LogoutResponse XML
        """
        try:
            req = self._prepare_request({"saml_request": logout_request})
            auth = OneLogin_Saml2_Auth(req, self._settings)

            # Process logout request and generate response
            def return_to() -> None:
                pass

            url = auth.process_slo(delete_session_cb=return_to)

            # Get the LogoutResponse
            logout_response = req.get("post_data", {}).get("SAMLResponse", "")
            return logout_response

        except Exception as e:
            print(f"Failed to process logout request: {e}")
            return ""

    async def initiate_logout(self, name_id: str, session_index: str | None = None) -> str:
        """Initiate SAML logout (SP-initiated).

        Args:
            name_id: User's NameID from original authentication
            session_index: Session index from authentication (optional)

        Returns:
            SAML logout URL
        """
        try:
            req = self._prepare_request({})
            auth = OneLogin_Saml2_Auth(req, self._settings)

            # Generate logout request
            logout_url = auth.logout(
                name_id=name_id,
                session_index=session_index,
            )
            return logout_url

        except Exception as e:
            print(f"Failed to initiate logout: {e}")
            return self.idp_slo_url or ""
