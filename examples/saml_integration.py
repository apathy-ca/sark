"""Example: SAML 2.0 Integration with Azure AD and Okta.

This example demonstrates how to use the SAML provider for enterprise SSO.
"""

import asyncio

from sark.services.auth.providers.saml import SAMLProvider


async def azure_ad_example():
    """Example: Azure AD SAML integration."""
    print("\n=== Azure AD SAML Example ===")

    # Initialize Azure AD SAML provider
    provider = SAMLProvider(
        # Service Provider (your application) configuration
        sp_entity_id="https://sark.example.com",
        sp_acs_url="https://sark.example.com/api/auth/saml/acs",
        sp_sls_url="https://sark.example.com/api/auth/saml/slo",
        # Identity Provider (Azure AD) configuration
        idp_entity_id="https://sts.windows.net/YOUR-TENANT-ID/",
        idp_sso_url="https://login.microsoftonline.com/YOUR-TENANT-ID/saml2",
        idp_slo_url="https://login.microsoftonline.com/YOUR-TENANT-ID/saml2",
        # IdP certificate (from Azure AD metadata)
        idp_x509_cert="MIIDdTCCAl2gAwIBAgILBAAAAAABFUtaw5QwDQYJKoZI...",  # Full cert here
        # Security settings
        want_assertions_signed=True,
        want_messages_signed=False,
    )

    # Step 1: Get SP metadata to upload to Azure AD
    try:
        metadata_xml = provider.get_metadata()
        print("1. Generated SP metadata (upload this to Azure AD):")
        print(f"   Length: {len(metadata_xml)} bytes")
        print(f"   SP Entity ID: {provider.sp_entity_id}")
        print(f"   ACS URL: {provider.sp_acs_url}")
    except Exception as e:
        print(f"   Error generating metadata: {e}")

    # Step 2: Initiate SSO login
    sso_url = await provider.get_authorization_url(
        state="/dashboard",  # RelayState - where to redirect after auth
        redirect_uri="",  # Not used in SAML
    )
    print(f"\n2. SSO Login URL:")
    print(f"   {sso_url[:100]}...")

    # Step 3: After user authenticates, handle SAML response
    # (In real app, this would be done in your ACS endpoint)
    print(f"\n3. After user authenticates at IdP:")
    print(f"   - IdP POSTs SAML response to: {provider.sp_acs_url}")
    print(f"   - Your app validates the assertion")
    print(f"   - Extract user info (email, name, groups)")
    print(f"   - Create user session")
    print(f"   - Redirect to RelayState URL")

    # Health check
    is_healthy = await provider.health_check()
    print(f"\n4. Provider health: {'OK' if is_healthy else 'FAILED'}")


async def okta_example():
    """Example: Okta SAML integration."""
    print("\n=== Okta SAML Example ===")

    # Initialize Okta SAML provider
    provider = SAMLProvider(
        # Service Provider configuration
        sp_entity_id="https://sark.example.com",
        sp_acs_url="https://sark.example.com/api/auth/saml/acs",
        sp_sls_url="https://sark.example.com/api/auth/saml/slo",
        # Identity Provider (Okta) configuration
        idp_entity_id="http://www.okta.com/YOUR-APP-ID",
        idp_sso_url="https://your-domain.okta.com/app/YOUR-APP-ID/sso/saml",
        idp_slo_url="https://your-domain.okta.com/app/YOUR-APP-ID/slo/saml",
        # Alternative: use metadata URL instead of manual config
        idp_metadata_url="https://your-domain.okta.com/app/YOUR-APP-ID/sso/saml/metadata",
        # IdP certificate
        idp_x509_cert="MIIDpDCCAoygAwIBAgIGAXoTp1KmMA0GCSqGSIb3DQEBCwUA...",
        # Security settings
        want_assertions_signed=True,
        want_messages_signed=False,
    )

    print("1. Okta SAML Provider configured")
    print(f"   IdP Entity ID: {provider.idp_entity_id}")
    print(f"   SSO URL: {provider.idp_sso_url}")
    print(f"   Metadata URL: {provider.idp_metadata_url}")

    # Generate metadata
    try:
        metadata_xml = provider.get_metadata()
        print(f"\n2. SP Metadata generated ({len(metadata_xml)} bytes)")
        print("   Upload this to Okta app configuration")
    except Exception as e:
        print(f"   Error: {e}")

    # Health check
    is_healthy = await provider.health_check()
    print(f"\n3. Provider health: {'OK' if is_healthy else 'FAILED'}")


async def attribute_mapping_example():
    """Example: Custom SAML attribute mapping."""
    print("\n=== Custom Attribute Mapping Example ===")

    # Custom attribute mapping for non-standard IdP
    custom_mapping = {
        # Map IdP-specific attributes to standard names
        "urn:oid:0.9.2342.19200300.100.1.3": "email",  # emailAddress
        "urn:oid:2.5.4.42": "given_name",  # givenName
        "urn:oid:2.5.4.4": "family_name",  # surname
        "urn:oid:2.16.840.1.113730.3.1.241": "name",  # displayName
        "memberOf": "groups",
    }

    provider = SAMLProvider(
        sp_entity_id="https://sark.example.com",
        sp_acs_url="https://sark.example.com/api/auth/saml/acs",
        sp_sls_url="https://sark.example.com/api/auth/saml/slo",
        idp_entity_id="https://custom-idp.example.com",
        idp_sso_url="https://custom-idp.example.com/sso",
        idp_x509_cert="MIIDCertificate...",
        attribute_mapping=custom_mapping,
    )

    print("Custom attribute mapping configured:")
    for idp_attr, std_attr in custom_mapping.items():
        print(f"  {idp_attr} -> {std_attr}")


async def signed_requests_example():
    """Example: SAML with signed requests."""
    print("\n=== Signed SAML Requests Example ===")

    # For production: generate X.509 certificate and private key
    # openssl req -new -x509 -days 3652 -nodes -out sp.crt -keyout sp.key

    sp_certificate = """MIIDXTCCAkWgAwIBAgIJALmVVuDWu4NYMA0GCSqGSIb3DQEBCw..."""

    sp_private_key = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC7VJTUt9Us8cKj
...
-----END PRIVATE KEY-----"""

    provider = SAMLProvider(
        sp_entity_id="https://sark.example.com",
        sp_acs_url="https://sark.example.com/api/auth/saml/acs",
        sp_sls_url="https://sark.example.com/api/auth/saml/slo",
        idp_entity_id="https://idp.example.com",
        idp_sso_url="https://idp.example.com/sso",
        idp_x509_cert="MIIDCertificate...",
        # SP signing configuration
        sp_x509_cert=sp_certificate,
        sp_private_key=sp_private_key,
        # Enable message signing
        want_assertions_signed=True,
        want_messages_signed=True,
    )

    print("SAML provider configured with request signing:")
    print(f"  - Assertions must be signed: {provider.want_assertions_signed}")
    print(f"  - Messages must be signed: {provider.want_messages_signed}")
    print(f"  - SP certificate configured: {bool(provider.sp_x509_cert)}")
    print(f"  - SP private key configured: {bool(provider.sp_private_key)}")


async def logout_example():
    """Example: SAML logout flows."""
    print("\n=== SAML Logout Example ===")

    provider = SAMLProvider(
        sp_entity_id="https://sark.example.com",
        sp_acs_url="https://sark.example.com/api/auth/saml/acs",
        sp_sls_url="https://sark.example.com/api/auth/saml/slo",
        idp_entity_id="https://idp.example.com",
        idp_sso_url="https://idp.example.com/sso",
        idp_slo_url="https://idp.example.com/slo",
        idp_x509_cert="MIIDCertificate...",
    )

    print("SAML supports two logout flows:")
    print("\n1. SP-Initiated Logout:")
    print("   - User clicks logout in your app")
    print("   - Your app calls initiate_logout()")
    print("   - User is redirected to IdP logout URL")
    print("   - IdP logs user out and redirects back")

    # Example SP-initiated logout
    logout_url = await provider.initiate_logout(
        name_id="user@example.com",
        session_index="session-abc123",
    )
    print(f"   Logout URL: {logout_url[:80]}...")

    print("\n2. IdP-Initiated Logout:")
    print("   - User logs out at IdP")
    print("   - IdP sends LogoutRequest to your SLS URL")
    print("   - Your app processes request with process_logout_request()")
    print("   - Your app destroys user session")
    print("   - Your app returns LogoutResponse to IdP")


async def main():
    """Run all examples."""
    print("SARK SAML 2.0 Provider Examples")
    print("=" * 70)

    await azure_ad_example()
    await okta_example()
    await attribute_mapping_example()
    await signed_requests_example()
    await logout_example()

    print("\n" + "=" * 70)
    print("✓ All examples completed!")
    print("\nProduction Setup Steps:")
    print("1. Generate SP metadata: GET /api/auth/saml/metadata")
    print("2. Upload metadata to your IdP (Azure AD, Okta, etc.)")
    print("3. Configure IdP settings in environment variables")
    print("4. Test SSO login: GET /api/auth/saml/login")
    print("5. Verify ACS endpoint receives assertions")
    print("6. Test logout flows")
    print("\nSecurity Checklist:")
    print("✓ Validate SAML assertions are signed")
    print("✓ Verify assertion timestamps (NotBefore, NotOnOrAfter)")
    print("✓ Check SubjectConfirmation recipient matches ACS URL")
    print("✓ Validate Audience restriction matches SP Entity ID")
    print("✓ Use HTTPS for all SAML endpoints")
    print("✓ Protect SP private key if using signed requests")


if __name__ == "__main__":
    asyncio.run(main())
