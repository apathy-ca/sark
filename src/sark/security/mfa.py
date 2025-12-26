"""
Multi-Factor Authentication (MFA) System

Provides MFA challenges for critical actions using multiple methods:
- TOTP (Time-based One-Time Password)
- SMS (via Twilio or similar)
- Push notifications (via mobile app)
"""

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import hmac
import logging
import secrets
import struct
import time
from typing import Any

logger = logging.getLogger(__name__)


class MFAMethod(str, Enum):
    """MFA authentication methods"""

    TOTP = "totp"
    SMS = "sms"
    PUSH = "push"
    EMAIL = "email"


class MFAStatus(str, Enum):
    """MFA challenge status"""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


@dataclass
class MFAChallenge:
    """Represents an MFA challenge"""

    challenge_id: str
    user_id: str
    method: MFAMethod
    action: str
    created_at: datetime
    expires_at: datetime
    status: MFAStatus
    code: str | None = None  # For TOTP/SMS
    attempts: int = 0
    max_attempts: int = 3


class MFAConfig:
    """Configuration for MFA system"""

    def __init__(
        self,
        default_method: MFAMethod = MFAMethod.TOTP,
        timeout_seconds: int = 120,
        code_length: int = 6,
        max_attempts: int = 3,
        totp_window: int = 1,  # Number of 30s windows to check
    ):
        self.default_method = default_method
        self.timeout_seconds = timeout_seconds
        self.code_length = code_length
        self.max_attempts = max_attempts
        self.totp_window = totp_window


class TOTPGenerator:
    """Generate and verify TOTP codes"""

    def __init__(self, secret: str | None = None):
        """
        Initialize TOTP generator

        Args:
            secret: Base32-encoded secret key (generates one if not provided)
        """
        if secret:
            self.secret = secret
        else:
            # Generate random secret
            random_bytes = secrets.token_bytes(20)
            self.secret = base64.b32encode(random_bytes).decode("utf-8")

    def generate_code(self, timestamp: int | None = None) -> str:
        """
        Generate TOTP code

        Args:
            timestamp: Unix timestamp (uses current time if not provided)

        Returns:
            6-digit TOTP code
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Calculate time step (30 second intervals)
        time_step = timestamp // 30

        # Convert to bytes
        time_bytes = struct.pack(">Q", time_step)

        # Decode secret
        secret_bytes = base64.b32decode(self.secret)

        # Generate HMAC
        hmac_hash = hmac.new(secret_bytes, time_bytes, hashlib.sha1).digest()

        # Dynamic truncation
        offset = hmac_hash[-1] & 0x0F
        code_bytes = hmac_hash[offset : offset + 4]
        code_int = struct.unpack(">I", code_bytes)[0] & 0x7FFFFFFF

        # Generate 6-digit code
        code = str(code_int % 1000000).zfill(6)

        return code

    def verify_code(self, code: str, timestamp: int | None = None, window: int = 1) -> bool:
        """
        Verify TOTP code

        Args:
            code: Code to verify
            timestamp: Unix timestamp (uses current time if not provided)
            window: Number of time steps to check (allows for time drift)

        Returns:
            True if code is valid
        """
        if timestamp is None:
            timestamp = int(time.time())

        # Check current time step and surrounding windows
        for i in range(-window, window + 1):
            check_timestamp = timestamp + (i * 30)
            expected_code = self.generate_code(check_timestamp)

            if secrets.compare_digest(code, expected_code):
                return True

        return False


class MFAChallengeSystem:
    """MFA challenge system"""

    def __init__(
        self,
        storage: Any | None = None,
        sms_service: Any | None = None,
        push_service: Any | None = None,
        email_service: Any | None = None,
        audit_logger: Any | None = None,
        config: MFAConfig | None = None,
    ):
        """
        Initialize MFA challenge system

        Args:
            storage: Storage backend for challenges (Redis recommended)
            sms_service: SMS delivery service (e.g., Twilio)
            push_service: Push notification service
            email_service: Email delivery service
            audit_logger: Audit logging service
            config: MFA configuration
        """
        self.storage = storage
        self.sms_service = sms_service
        self.push_service = push_service
        self.email_service = email_service
        self.audit_logger = audit_logger
        self.config = config or MFAConfig()

        # TOTP generators per user (in production, store in database)
        self._totp_secrets: dict[str, str] = {}

    async def require_mfa(
        self,
        user_id: str,
        action: str,
        method: MFAMethod | None = None,
        user_contact: dict[str, str] | None = None,
    ) -> bool:
        """
        Require MFA for an action

        Args:
            user_id: User ID requiring MFA
            action: Action being authorized
            method: MFA method to use (uses default if not specified)
            user_contact: User contact info (phone, email, etc.)

        Returns:
            True if MFA passed, False if failed
        """
        method = method or self.config.default_method

        # Create challenge
        challenge = await self._create_challenge(user_id, action, method)

        # Send challenge
        await self._send_challenge(challenge, user_contact)

        # Wait for response
        result = await self._wait_for_response(challenge)

        # Log result
        await self._log_mfa_event(challenge, result)

        return result

    async def verify_code(self, user_id: str, challenge_id: str, code: str) -> bool:
        """
        Verify MFA code

        Args:
            user_id: User ID
            challenge_id: Challenge ID
            code: Code provided by user

        Returns:
            True if code is valid
        """
        # Get challenge
        challenge = await self._get_challenge(challenge_id)

        if not challenge:
            logger.warning(f"Challenge {challenge_id} not found")
            return False

        # Verify user
        if challenge.user_id != user_id:
            logger.warning(f"User {user_id} attempted to verify challenge for {challenge.user_id}")
            return False

        # Check expiration
        if datetime.now() > challenge.expires_at:
            challenge.status = MFAStatus.EXPIRED
            await self._update_challenge(challenge)
            return False

        # Check max attempts
        challenge.attempts += 1
        if challenge.attempts > challenge.max_attempts:
            challenge.status = MFAStatus.DENIED
            await self._update_challenge(challenge)
            logger.warning(f"Max attempts exceeded for challenge {challenge_id}")
            return False

        # Verify code based on method
        is_valid = False

        if challenge.method == MFAMethod.TOTP:
            is_valid = await self._verify_totp(user_id, code)
        elif challenge.method in [MFAMethod.SMS, MFAMethod.EMAIL]:
            is_valid = secrets.compare_digest(code, challenge.code or "")
        elif challenge.method == MFAMethod.PUSH:
            # Push notifications are approved via separate endpoint
            is_valid = challenge.status == MFAStatus.APPROVED

        # Update challenge
        if is_valid:
            challenge.status = MFAStatus.APPROVED
        else:
            challenge.status = (
                MFAStatus.DENIED
                if challenge.attempts >= challenge.max_attempts
                else MFAStatus.PENDING
            )

        await self._update_challenge(challenge)

        return is_valid

    async def _create_challenge(self, user_id: str, action: str, method: MFAMethod) -> MFAChallenge:
        """Create new MFA challenge"""
        challenge_id = secrets.token_urlsafe(32)
        now = datetime.now()

        # Generate code for SMS/Email
        code = None
        if method in [MFAMethod.SMS, MFAMethod.EMAIL]:
            code = "".join(str(secrets.randbelow(10)) for _ in range(self.config.code_length))

        challenge = MFAChallenge(
            challenge_id=challenge_id,
            user_id=user_id,
            method=method,
            action=action,
            created_at=now,
            expires_at=now + timedelta(seconds=self.config.timeout_seconds),
            status=MFAStatus.PENDING,
            code=code,
            max_attempts=self.config.max_attempts,
        )

        # Store challenge
        if self.storage:
            await self.storage.set(
                f"mfa:challenge:{challenge_id}", challenge, ex=self.config.timeout_seconds
            )

        return challenge

    async def _send_challenge(self, challenge: MFAChallenge, user_contact: dict[str, str] | None):
        """Send MFA challenge to user"""
        try:
            if challenge.method == MFAMethod.SMS:
                if self.sms_service and user_contact and user_contact.get("phone"):
                    await self.sms_service.send_sms(
                        to=user_contact["phone"],
                        message=f"Your SARK verification code is: {challenge.code}",
                    )
                else:
                    logger.warning(f"Cannot send SMS for challenge {challenge.challenge_id}")

            elif challenge.method == MFAMethod.EMAIL:
                if self.email_service and user_contact and user_contact.get("email"):
                    await self.email_service.send_email(
                        to=user_contact["email"],
                        subject="SARK MFA Verification",
                        body=f"Your verification code is: {challenge.code}\n\nThis code expires in {self.config.timeout_seconds} seconds.",
                    )
                else:
                    logger.warning(f"Cannot send email for challenge {challenge.challenge_id}")

            elif challenge.method == MFAMethod.PUSH:
                if self.push_service:
                    await self.push_service.send_push(
                        user_id=challenge.user_id,
                        title="MFA Required",
                        body=f"Approve action: {challenge.action}",
                        data={"challenge_id": challenge.challenge_id},
                    )
                else:
                    logger.warning(f"Cannot send push for challenge {challenge.challenge_id}")

            elif challenge.method == MFAMethod.TOTP:
                # TOTP doesn't require sending - user checks their authenticator app
                logger.info(f"TOTP challenge created for user {challenge.user_id}")

        except Exception as e:
            logger.error(f"Failed to send MFA challenge: {e}")

    async def _wait_for_response(self, challenge: MFAChallenge, poll_interval: float = 2.0) -> bool:
        """
        Wait for MFA response (for automated flows)

        Args:
            challenge: MFA challenge
            poll_interval: How often to check status (seconds)

        Returns:
            True if approved, False if denied/expired
        """
        start_time = time.time()

        while time.time() - start_time < self.config.timeout_seconds:
            # Get current challenge status
            current_challenge = await self._get_challenge(challenge.challenge_id)

            if not current_challenge:
                return False

            if current_challenge.status == MFAStatus.APPROVED:
                return True

            if current_challenge.status in [MFAStatus.DENIED, MFAStatus.EXPIRED]:
                return False

            # Wait before polling again
            await self._sleep(poll_interval)

        # Timeout - mark as expired
        challenge.status = MFAStatus.EXPIRED
        await self._update_challenge(challenge)

        return False

    async def _verify_totp(self, user_id: str, code: str) -> bool:
        """Verify TOTP code"""
        # Get or create TOTP secret for user
        if user_id not in self._totp_secrets:
            # In production, retrieve from database
            self._totp_secrets[user_id] = TOTPGenerator().secret

        generator = TOTPGenerator(self._totp_secrets[user_id])
        return generator.verify_code(code, window=self.config.totp_window)

    def get_totp_secret(self, user_id: str) -> str:
        """Get TOTP secret for user (for QR code generation)"""
        if user_id not in self._totp_secrets:
            self._totp_secrets[user_id] = TOTPGenerator().secret

        return self._totp_secrets[user_id]

    async def _get_challenge(self, challenge_id: str) -> MFAChallenge | None:
        """Retrieve challenge from storage"""
        if not self.storage:
            return None

        return await self.storage.get(f"mfa:challenge:{challenge_id}")

    async def _update_challenge(self, challenge: MFAChallenge):
        """Update challenge in storage"""
        if not self.storage:
            return

        await self.storage.set(
            f"mfa:challenge:{challenge.challenge_id}", challenge, ex=self.config.timeout_seconds
        )

    async def _log_mfa_event(self, challenge: MFAChallenge, result: bool):
        """Log MFA event"""
        if not self.audit_logger:
            return

        try:
            await self.audit_logger.log_event(
                event_type="mfa_completed" if result else "mfa_failed",
                user_id=challenge.user_id,
                challenge_id=challenge.challenge_id,
                method=challenge.method.value,
                action=challenge.action,
                status=challenge.status.value,
                attempts=challenge.attempts,
                result="success" if result else "failure",
            )
        except Exception as e:
            logger.error(f"Failed to log MFA event: {e}")

    async def _sleep(self, seconds: float):
        """Async sleep"""
        import asyncio

        await asyncio.sleep(seconds)
