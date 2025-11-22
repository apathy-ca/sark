"""SAML authentication endpoints.

Provides SAML 2.0 authentication endpoints:
- Service Provider metadata
- Assertion Consumer Service (ACS) - callback endpoint
- Single Logout Service (SLS)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from sark.config.settings import Settings, get_settings
from sark.services.auth.providers.saml import SAMLProvider

router = APIRouter(prefix="/api/auth/saml", tags=["SAML Authentication"])


def get_saml_provider(settings: Annotated[Settings, Depends(get_settings)]) -> SAMLProvider:
    """Get configured SAML provider.

    Args:
        settings: Application settings

    Returns:
        Configured SAMLProvider instance

    Raises:
        HTTPException: If SAML is not enabled
    """
    if not settings.saml_enabled:
        raise HTTPException(status_code=503, detail="SAML authentication is not enabled")

    # Build SAML provider from settings
    provider = SAMLProvider(
        sp_entity_id=settings.saml_sp_entity_id,
        sp_acs_url=settings.saml_sp_acs_url,
        sp_sls_url=settings.saml_sp_sls_url,
        idp_entity_id=settings.saml_idp_entity_id,
        idp_sso_url=settings.saml_idp_sso_url,
        idp_slo_url=settings.saml_idp_slo_url,
        idp_x509_cert=settings.saml_idp_x509_cert,
        idp_metadata_url=settings.saml_idp_metadata_url,
        sp_x509_cert=settings.saml_sp_x509_cert,
        sp_private_key=settings.saml_sp_private_key,
        name_id_format=settings.saml_name_id_format,
        want_assertions_signed=settings.saml_want_assertions_signed,
        want_messages_signed=settings.saml_want_messages_signed,
    )

    return provider


@router.get("/metadata", response_class=Response)
async def get_metadata(
    provider: Annotated[SAMLProvider, Depends(get_saml_provider)],
) -> Response:
    """Get Service Provider SAML metadata.

    This endpoint returns the SP metadata XML that should be registered
    with the Identity Provider.

    Returns:
        XML metadata response
    """
    try:
        metadata_xml = provider.get_metadata()
        return Response(
            content=metadata_xml,
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="sp_metadata.xml"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate metadata: {str(e)}")


@router.get("/login")
async def saml_login(
    provider: Annotated[SAMLProvider, Depends(get_saml_provider)],
    relay_state: str = Query(default="/", description="Return URL after authentication"),
) -> RedirectResponse:
    """Initiate SAML SSO login.

    Redirects user to Identity Provider for authentication.

    Args:
        relay_state: Application URL to return to after authentication

    Returns:
        Redirect to IdP SSO URL
    """
    try:
        # Generate SSO URL with AuthnRequest
        sso_url = await provider.get_authorization_url(
            state=relay_state,
            redirect_uri="",  # Not used in SAML
        )

        return RedirectResponse(url=sso_url, status_code=302)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate login: {str(e)}")


@router.post("/acs", response_class=HTMLResponse)
async def assertion_consumer_service(
    request: Request,
    provider: Annotated[SAMLProvider, Depends(get_saml_provider)],
    SAMLResponse: Annotated[str, Form()],
    RelayState: str = Form(default="/"),
) -> HTMLResponse:
    """Assertion Consumer Service (ACS) endpoint.

    This endpoint receives SAML assertions from the Identity Provider
    after successful authentication.

    Args:
        SAMLResponse: Base64-encoded SAML response
        RelayState: Application state to maintain

    Returns:
        HTML response with authentication result
    """
    try:
        # Authenticate with SAML response
        user_info = await provider.authenticate(
            {"saml_response": SAMLResponse, "relay_state": RelayState}
        )

        if not user_info:
            raise HTTPException(status_code=401, detail="SAML authentication failed")

        # In a real application, you would:
        # 1. Create a session for the user
        # 2. Set session cookie
        # 3. Redirect to the RelayState URL
        #
        # For this example, we'll return user info
        return HTMLResponse(
            content=f"""
            <html>
                <head><title>SAML Authentication Success</title></head>
                <body>
                    <h1>Authentication Successful</h1>
                    <p><strong>User ID:</strong> {user_info.user_id}</p>
                    <p><strong>Email:</strong> {user_info.email}</p>
                    <p><strong>Name:</strong> {user_info.name or 'N/A'}</p>
                    <p><strong>Groups:</strong> {', '.join(user_info.groups or [])}</p>
                    <hr>
                    <p>In production, you would be redirected to: {RelayState}</p>
                    <p><a href="{RelayState}">Continue to application</a></p>
                </body>
            </html>
            """,
            status_code=200,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process SAML response: {str(e)}"
        )


@router.get("/slo")
@router.post("/slo")
async def single_logout_service(
    request: Request,
    provider: Annotated[SAMLProvider, Depends(get_saml_provider)],
    SAMLRequest: str | None = Query(default=None),
    SAMLResponse: str | None = Query(default=None),
    RelayState: str = Query(default="/"),
) -> Response:
    """Single Logout Service (SLS) endpoint.

    Handles both IdP-initiated and SP-initiated logout requests.

    Args:
        SAMLRequest: SAML logout request (IdP-initiated)
        SAMLResponse: SAML logout response (SP-initiated response)
        RelayState: Application state

    Returns:
        Redirect or response based on logout flow
    """
    try:
        # IdP-initiated logout
        if SAMLRequest:
            # Process logout request and generate response
            logout_response = await provider.process_logout_request(SAMLRequest)

            # In production, destroy user session here

            # Return logout response
            return Response(
                content=logout_response,
                media_type="application/xml",
            )

        # SP-initiated logout response
        elif SAMLResponse:
            # Process logout response
            # In production, confirm session destruction

            return HTMLResponse(
                content="""
                <html>
                    <head><title>Logged Out</title></head>
                    <body>
                        <h1>You have been logged out</h1>
                        <p><a href="/api/auth/saml/login">Login again</a></p>
                    </body>
                </html>
                """,
                status_code=200,
            )

        else:
            raise HTTPException(status_code=400, detail="No logout request or response provided")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@router.post("/logout/initiate")
async def initiate_logout(
    provider: Annotated[SAMLProvider, Depends(get_saml_provider)],
    name_id: str = Form(..., description="User's NameID from authentication"),
    session_index: str | None = Form(default=None, description="Session index (optional)"),
) -> RedirectResponse:
    """Initiate SP-initiated logout.

    Args:
        name_id: User's NameID from SAML authentication
        session_index: Session index from authentication

    Returns:
        Redirect to IdP logout URL
    """
    try:
        logout_url = await provider.initiate_logout(
            name_id=name_id,
            session_index=session_index,
        )

        return RedirectResponse(url=logout_url, status_code=302)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate logout: {str(e)}")


@router.get("/health")
async def saml_health_check(
    provider: Annotated[SAMLProvider, Depends(get_saml_provider)],
) -> dict[str, Any]:
    """Check SAML provider health.

    Returns:
        Health status
    """
    is_healthy = await provider.health_check()

    return {
        "service": "saml",
        "status": "healthy" if is_healthy else "unhealthy",
        "idp_entity_id": provider.idp_entity_id,
        "idp_sso_url": provider.idp_sso_url,
    }
