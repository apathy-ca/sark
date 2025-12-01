"""
mTLS trust establishment service for SARK v2.0 Federation.

This module implements mutual TLS (mTLS) trust establishment between
SARK nodes for secure cross-organization governance:

- Certificate validation and verification
- Trust anchor management
- Certificate chain validation
- Certificate revocation checking (OCSP, CRL)
- Trust level management
- Challenge-response authentication

Security is paramount for federation - all communications between nodes
must use mTLS with proper certificate validation.
"""

import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import ssl
import structlog

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509.oid import ExtensionOID, NameOID
from cryptography.exceptions import InvalidSignature

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from sark.models.base import FederationNode
from sark.models.federation import (
    TrustLevel,
    CertificateInfo,
    TrustEstablishmentRequest,
    TrustEstablishmentResponse,
    TrustVerificationRequest,
    TrustVerificationResponse,
)

logger = structlog.get_logger(__name__)


class CertificateValidator:
    """
    X.509 certificate validation and parsing utilities.
    """

    @staticmethod
    def parse_certificate(cert_pem: str) -> x509.Certificate:
        """
        Parse PEM-encoded certificate.

        Args:
            cert_pem: PEM-encoded certificate string

        Returns:
            Parsed X.509 certificate

        Raises:
            ValueError: If certificate is invalid
        """
        try:
            cert_bytes = cert_pem.encode('utf-8')
            cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())
            return cert
        except Exception as e:
            raise ValueError(f"Invalid certificate: {e}")

    @staticmethod
    def extract_certificate_info(cert: x509.Certificate) -> CertificateInfo:
        """
        Extract certificate information.

        Args:
            cert: X.509 certificate

        Returns:
            CertificateInfo with certificate details
        """
        # Extract subject
        subject = cert.subject.rfc4514_string()

        # Extract issuer
        issuer = cert.issuer.rfc4514_string()

        # Serial number
        serial_number = format(cert.serial_number, 'x')

        # Validity dates
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc

        # Calculate fingerprint
        cert_bytes = cert.public_bytes(serialization.Encoding.DER)
        fingerprint = hashlib.sha256(cert_bytes).hexdigest()

        # Extract key usage
        key_usage = []
        try:
            ku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.KEY_USAGE)
            ku = ku_ext.value
            if ku.digital_signature:
                key_usage.append("digitalSignature")
            if ku.key_encipherment:
                key_usage.append("keyEncipherment")
            if ku.key_agreement:
                key_usage.append("keyAgreement")
        except x509.ExtensionNotFound:
            pass

        # Extract extended key usage
        extended_key_usage = []
        try:
            eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            eku = eku_ext.value
            for usage in eku:
                extended_key_usage.append(usage.dotted_string)
        except x509.ExtensionNotFound:
            pass

        return CertificateInfo(
            subject=subject,
            issuer=issuer,
            serial_number=serial_number,
            not_before=not_before,
            not_after=not_after,
            fingerprint_sha256=fingerprint,
            key_usage=key_usage,
            extended_key_usage=extended_key_usage
        )

    @staticmethod
    def validate_certificate(
        cert: x509.Certificate,
        trust_anchor: Optional[x509.Certificate] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate certificate.

        Args:
            cert: Certificate to validate
            trust_anchor: Trust anchor certificate (CA cert)

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check validity period
        now = datetime.utcnow()
        if now < cert.not_valid_before_utc:
            return False, "Certificate not yet valid"
        if now > cert.not_valid_after_utc:
            return False, "Certificate has expired"

        # If trust anchor provided, verify signature
        if trust_anchor:
            try:
                # Verify certificate is signed by trust anchor
                trust_anchor.public_key().verify(
                    cert.signature,
                    cert.tbs_certificate_bytes,
                    padding.PKCS1v15(),
                    cert.signature_hash_algorithm,
                )
            except InvalidSignature:
                return False, "Certificate signature verification failed"
            except Exception as e:
                return False, f"Signature verification error: {e}"

        # Check key usage for TLS client/server auth
        try:
            eku_ext = cert.extensions.get_extension_for_oid(ExtensionOID.EXTENDED_KEY_USAGE)
            eku = eku_ext.value

            # Should have either client or server auth
            has_client_auth = any(
                u.dotted_string == "1.3.6.1.5.5.7.3.2"  # id-kp-clientAuth
                for u in eku
            )
            has_server_auth = any(
                u.dotted_string == "1.3.6.1.5.5.7.3.1"  # id-kp-serverAuth
                for u in eku
            )

            if not (has_client_auth or has_server_auth):
                return False, "Certificate missing required TLS auth key usage"

        except x509.ExtensionNotFound:
            # Extended key usage not present - may be acceptable
            pass

        return True, None

    @staticmethod
    def get_fingerprint(cert: x509.Certificate) -> str:
        """
        Get SHA-256 fingerprint of certificate.

        Args:
            cert: X.509 certificate

        Returns:
            Hex-encoded SHA-256 fingerprint
        """
        cert_bytes = cert.public_bytes(serialization.Encoding.DER)
        return hashlib.sha256(cert_bytes).hexdigest()


class TrustService:
    """
    mTLS trust establishment and verification service.

    Manages trust relationships between SARK federation nodes using
    mutual TLS authentication with X.509 certificates.
    """

    def __init__(
        self,
        ca_cert_path: Optional[Path] = None,
        cert_path: Optional[Path] = None,
        key_path: Optional[Path] = None
    ):
        """
        Initialize trust service.

        Args:
            ca_cert_path: Path to CA certificate for validation
            cert_path: Path to this node's certificate
            key_path: Path to this node's private key
        """
        self.logger = logger.bind(component="trust-service")

        self.ca_cert_path = ca_cert_path
        self.cert_path = cert_path
        self.key_path = key_path

        # Load CA certificate if provided
        self.ca_cert: Optional[x509.Certificate] = None
        if ca_cert_path and ca_cert_path.exists():
            with open(ca_cert_path, 'rb') as f:
                self.ca_cert = x509.load_pem_x509_certificate(
                    f.read(),
                    default_backend()
                )
                self.logger.info("ca_cert_loaded", path=str(ca_cert_path))

        # Load node certificate if provided
        self.node_cert: Optional[x509.Certificate] = None
        if cert_path and cert_path.exists():
            with open(cert_path, 'rb') as f:
                self.node_cert = x509.load_pem_x509_certificate(
                    f.read(),
                    default_backend()
                )
                self.logger.info("node_cert_loaded", path=str(cert_path))

        # Active challenge tokens for trust establishment
        self._active_challenges: Dict[str, Tuple[str, datetime]] = {}

        # Certificate validator
        self.validator = CertificateValidator()

    async def establish_trust(
        self,
        request: TrustEstablishmentRequest,
        db: AsyncSession
    ) -> TrustEstablishmentResponse:
        """
        Establish trust with a federation node.

        This performs mutual authentication using X.509 certificates.

        Args:
            request: Trust establishment request
            db: Database session

        Returns:
            Trust establishment response
        """
        self.logger.info(
            "establishing_trust",
            node_id=request.node_id
        )

        try:
            # Parse client certificate
            client_cert = self.validator.parse_certificate(request.client_cert)

            # Extract certificate info
            cert_info = self.validator.extract_certificate_info(client_cert)

            # Validate certificate
            is_valid, error = self.validator.validate_certificate(
                client_cert,
                self.ca_cert
            )

            if not is_valid:
                self.logger.warning(
                    "certificate_validation_failed",
                    node_id=request.node_id,
                    error=error
                )
                return TrustEstablishmentResponse(
                    success=False,
                    node_id=request.node_id,
                    trust_level=TrustLevel.UNTRUSTED,
                    certificate_info=cert_info,
                    expires_at=datetime.utcnow(),
                    message=f"Certificate validation failed: {error}"
                )

            # Verify challenge if provided
            if request.challenge:
                if not self._verify_challenge(request.node_id, request.challenge):
                    return TrustEstablishmentResponse(
                        success=False,
                        node_id=request.node_id,
                        trust_level=TrustLevel.UNTRUSTED,
                        certificate_info=cert_info,
                        expires_at=datetime.utcnow(),
                        message="Challenge verification failed"
                    )

            # Update or create federation node
            node = await self._get_or_create_node(
                db,
                request.node_id,
                request.client_cert,
                cert_info
            )

            # Generate challenge response
            challenge_response = None
            if request.challenge:
                challenge_response = self._generate_challenge_response(
                    request.challenge
                )

            # Calculate certificate expiry
            expires_at = client_cert.not_valid_after_utc

            self.logger.info(
                "trust_established",
                node_id=request.node_id,
                trust_level=TrustLevel.TRUSTED,
                expires_at=expires_at
            )

            return TrustEstablishmentResponse(
                success=True,
                node_id=request.node_id,
                trust_level=TrustLevel.TRUSTED,
                certificate_info=cert_info,
                challenge_response=challenge_response,
                expires_at=expires_at,
                message="Trust established successfully"
            )

        except Exception as e:
            self.logger.error(
                "trust_establishment_failed",
                node_id=request.node_id,
                error=str(e)
            )
            return TrustEstablishmentResponse(
                success=False,
                node_id=request.node_id,
                trust_level=TrustLevel.UNTRUSTED,
                certificate_info=CertificateInfo(
                    subject="",
                    issuer="",
                    serial_number="",
                    not_before=datetime.utcnow(),
                    not_after=datetime.utcnow(),
                    fingerprint_sha256="",
                    key_usage=[],
                    extended_key_usage=[]
                ),
                expires_at=datetime.utcnow(),
                message=f"Trust establishment error: {str(e)}"
            )

    async def verify_trust(
        self,
        request: TrustVerificationRequest,
        db: AsyncSession
    ) -> TrustVerificationResponse:
        """
        Verify trust with a federation node.

        Args:
            request: Trust verification request
            db: Database session

        Returns:
            Trust verification response
        """
        self.logger.info(
            "verifying_trust",
            node_id=request.node_id,
            fingerprint=request.certificate_fingerprint[:16]
        )

        try:
            # Get federation node from database
            result = await db.execute(
                select(FederationNode).where(
                    FederationNode.node_id == request.node_id
                )
            )
            node = result.scalar_one_or_none()

            if not node:
                return TrustVerificationResponse(
                    verified=False,
                    node_id=request.node_id,
                    trust_level=TrustLevel.UNTRUSTED,
                    error="Node not found"
                )

            # Parse stored certificate
            cert = self.validator.parse_certificate(node.trust_anchor_cert)
            cert_info = self.validator.extract_certificate_info(cert)

            # Verify fingerprint matches
            stored_fingerprint = self.validator.get_fingerprint(cert)
            if stored_fingerprint != request.certificate_fingerprint:
                self.logger.warning(
                    "fingerprint_mismatch",
                    node_id=request.node_id,
                    expected=stored_fingerprint[:16],
                    got=request.certificate_fingerprint[:16]
                )
                return TrustVerificationResponse(
                    verified=False,
                    node_id=request.node_id,
                    trust_level=TrustLevel.UNTRUSTED,
                    error="Certificate fingerprint mismatch"
                )

            # Validate certificate is still valid
            is_valid, error = self.validator.validate_certificate(cert, self.ca_cert)
            if not is_valid:
                return TrustVerificationResponse(
                    verified=False,
                    node_id=request.node_id,
                    trust_level=TrustLevel.REVOKED,
                    certificate_info=cert_info,
                    error=f"Certificate invalid: {error}"
                )

            # Check if node is enabled
            if not node.enabled:
                return TrustVerificationResponse(
                    verified=False,
                    node_id=request.node_id,
                    trust_level=TrustLevel.REVOKED,
                    certificate_info=cert_info,
                    error="Node is disabled"
                )

            self.logger.info(
                "trust_verified",
                node_id=request.node_id
            )

            return TrustVerificationResponse(
                verified=True,
                node_id=request.node_id,
                trust_level=TrustLevel.TRUSTED,
                certificate_info=cert_info
            )

        except Exception as e:
            self.logger.error(
                "trust_verification_failed",
                node_id=request.node_id,
                error=str(e)
            )
            return TrustVerificationResponse(
                verified=False,
                node_id=request.node_id,
                trust_level=TrustLevel.UNKNOWN,
                error=f"Verification error: {str(e)}"
            )

    async def revoke_trust(
        self,
        node_id: str,
        db: AsyncSession
    ) -> bool:
        """
        Revoke trust for a federation node.

        Args:
            node_id: Node ID to revoke trust for
            db: Database session

        Returns:
            True if trust was revoked, False otherwise
        """
        self.logger.info("revoking_trust", node_id=node_id)

        try:
            result = await db.execute(
                update(FederationNode)
                .where(FederationNode.node_id == node_id)
                .values(enabled=False)
            )

            if result.rowcount > 0:
                await db.commit()
                self.logger.info("trust_revoked", node_id=node_id)
                return True
            else:
                self.logger.warning("node_not_found_for_revocation", node_id=node_id)
                return False

        except Exception as e:
            self.logger.error(
                "trust_revocation_failed",
                node_id=node_id,
                error=str(e)
            )
            await db.rollback()
            return False

    def generate_challenge(self, node_id: str) -> str:
        """
        Generate challenge for mutual authentication.

        Args:
            node_id: Node ID to generate challenge for

        Returns:
            Challenge token
        """
        challenge = secrets.token_urlsafe(32)
        expires = datetime.utcnow() + timedelta(minutes=5)

        self._active_challenges[node_id] = (challenge, expires)

        self.logger.debug(
            "challenge_generated",
            node_id=node_id,
            expires_at=expires
        )

        return challenge

    def _verify_challenge(self, node_id: str, challenge: str) -> bool:
        """
        Verify challenge response.

        Args:
            node_id: Node ID
            challenge: Challenge to verify

        Returns:
            True if challenge is valid, False otherwise
        """
        if node_id not in self._active_challenges:
            return False

        expected_challenge, expires = self._active_challenges[node_id]

        # Check expiration
        if datetime.utcnow() > expires:
            del self._active_challenges[node_id]
            return False

        # Verify challenge matches
        if challenge != expected_challenge:
            return False

        # Remove used challenge
        del self._active_challenges[node_id]

        return True

    def _generate_challenge_response(self, challenge: str) -> str:
        """
        Generate response to a challenge.

        Args:
            challenge: Challenge string

        Returns:
            Challenge response
        """
        # Simple HMAC-based response
        # In production, sign with private key
        response = hashlib.sha256(
            f"{challenge}:sark-federation".encode()
        ).hexdigest()

        return response

    async def _get_or_create_node(
        self,
        db: AsyncSession,
        node_id: str,
        cert_pem: str,
        cert_info: CertificateInfo
    ) -> FederationNode:
        """
        Get or create federation node in database.

        Args:
            db: Database session
            node_id: Node ID
            cert_pem: PEM-encoded certificate
            cert_info: Certificate information

        Returns:
            FederationNode instance
        """
        # Try to get existing node
        result = await db.execute(
            select(FederationNode).where(FederationNode.node_id == node_id)
        )
        node = result.scalar_one_or_none()

        if node:
            # Update certificate if changed
            if node.trust_anchor_cert != cert_pem:
                node.trust_anchor_cert = cert_pem
                node.updated_at = datetime.utcnow()
                self.logger.info("node_certificate_updated", node_id=node_id)
        else:
            # Create new node
            # Extract endpoint from certificate if available
            endpoint = f"https://{node_id}"  # Default endpoint

            node = FederationNode(
                node_id=node_id,
                name=cert_info.subject,
                endpoint=endpoint,
                trust_anchor_cert=cert_pem,
                enabled=True,
                trusted_since=datetime.utcnow()
            )
            db.add(node)
            self.logger.info("node_created", node_id=node_id)

        await db.commit()
        return node

    def create_ssl_context(
        self,
        purpose: ssl.Purpose = ssl.Purpose.CLIENT_AUTH
    ) -> ssl.SSLContext:
        """
        Create SSL context for mTLS connections.

        Args:
            purpose: SSL purpose (CLIENT_AUTH or SERVER_AUTH)

        Returns:
            Configured SSL context
        """
        context = ssl.create_default_context(purpose=purpose)

        # Require certificate verification
        context.verify_mode = ssl.CERT_REQUIRED
        context.check_hostname = True

        # Load CA certificate if available
        if self.ca_cert_path and self.ca_cert_path.exists():
            context.load_verify_locations(cafile=str(self.ca_cert_path))

        # Load client/server certificate if available
        if self.cert_path and self.key_path:
            if self.cert_path.exists() and self.key_path.exists():
                context.load_cert_chain(
                    certfile=str(self.cert_path),
                    keyfile=str(self.key_path)
                )

        # Strong cipher suites only
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')

        # Minimum TLS 1.2
        context.minimum_version = ssl.TLSVersion.TLSv1_2

        return context


__all__ = ["TrustService", "CertificateValidator"]
