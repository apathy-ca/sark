"""
Unit tests for Multi-Factor Authentication (MFA) system

Tests cover:
- TOTP generation and verification (RFC 6238 compliance)
- MFA challenge lifecycle
- Multiple authentication methods (TOTP, SMS, Email, Push)
- Timeout enforcement
- Rate limiting (max attempts)
- Storage integration
- Service integration (SMS, Email, Push)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
import time
import secrets

from sark.security.mfa import (
    MFAChallengeSystem,
    MFAChallenge,
    MFAConfig,
    MFAMethod,
    MFAStatus,
    TOTPGenerator,
)


class TestMFAConfig:
    """Test MFAConfig class"""

    def test_default_config(self):
        """Test creating config with defaults"""
        config = MFAConfig()

        assert config.default_method == MFAMethod.TOTP
        assert config.timeout_seconds == 120
        assert config.code_length == 6
        assert config.max_attempts == 3
        assert config.totp_window == 1

    def test_custom_config(self):
        """Test creating config with custom values"""
        config = MFAConfig(
            default_method=MFAMethod.SMS,
            timeout_seconds=300,
            code_length=8,
            max_attempts=5,
            totp_window=2,
        )

        assert config.default_method == MFAMethod.SMS
        assert config.timeout_seconds == 300
        assert config.code_length == 8
        assert config.max_attempts == 5
        assert config.totp_window == 2


class TestMFAChallenge:
    """Test MFAChallenge dataclass"""

    def test_create_challenge_minimal(self):
        """Test creating challenge with required fields"""
        now = datetime.now()
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.TOTP,
            action="delete_resource",
            created_at=now,
            expires_at=now + timedelta(seconds=120),
            status=MFAStatus.PENDING,
        )

        assert challenge.challenge_id == "chal-123"
        assert challenge.user_id == "user123"
        assert challenge.method == MFAMethod.TOTP
        assert challenge.action == "delete_resource"
        assert challenge.status == MFAStatus.PENDING
        assert challenge.code is None
        assert challenge.attempts == 0
        assert challenge.max_attempts == 3

    def test_create_challenge_with_code(self):
        """Test creating challenge with code (SMS/Email)"""
        now = datetime.now()
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete_resource",
            created_at=now,
            expires_at=now + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
            attempts=1,
            max_attempts=5,
        )

        assert challenge.code == "123456"
        assert challenge.attempts == 1
        assert challenge.max_attempts == 5


class TestTOTPGenerator:
    """Test TOTP generator"""

    def test_generate_secret(self):
        """Test that generator creates valid secret if none provided"""
        generator = TOTPGenerator()

        assert generator.secret is not None
        assert len(generator.secret) > 0
        # Should be valid base32
        import base64

        decoded = base64.b32decode(generator.secret)
        assert len(decoded) == 20

    def test_use_provided_secret(self):
        """Test that generator uses provided secret"""
        import base64

        random_bytes = secrets.token_bytes(20)
        secret = base64.b32encode(random_bytes).decode("utf-8")

        generator = TOTPGenerator(secret=secret)
        assert generator.secret == secret

    def test_generate_code_format(self):
        """Test that generated codes are 6 digits"""
        generator = TOTPGenerator()
        code = generator.generate_code()

        assert len(code) == 6
        assert code.isdigit()

    def test_generate_code_deterministic(self):
        """Test that same timestamp generates same code"""
        generator = TOTPGenerator()
        timestamp = 1704067200  # Fixed timestamp

        code1 = generator.generate_code(timestamp)
        code2 = generator.generate_code(timestamp)

        assert code1 == code2

    def test_generate_code_changes_over_time(self):
        """Test that codes change with different timestamps"""
        generator = TOTPGenerator()

        code1 = generator.generate_code(1704067200)  # Time step 1
        code2 = generator.generate_code(1704067200 + 30)  # Time step 2 (30s later)

        # Codes should be different for different time steps
        assert code1 != code2

    def test_verify_code_valid(self):
        """Test verifying a valid code"""
        generator = TOTPGenerator()
        timestamp = int(time.time())

        code = generator.generate_code(timestamp)
        is_valid = generator.verify_code(code, timestamp)

        assert is_valid

    def test_verify_code_invalid(self):
        """Test verifying an invalid code"""
        generator = TOTPGenerator()
        timestamp = int(time.time())

        is_valid = generator.verify_code("999999", timestamp)

        assert not is_valid

    def test_verify_code_with_time_window(self):
        """Test that codes from adjacent time windows are accepted"""
        generator = TOTPGenerator()
        timestamp = 1704067200

        # Generate code for previous time step
        code = generator.generate_code(timestamp - 30)

        # Should be valid with window=1
        is_valid = generator.verify_code(code, timestamp, window=1)
        assert is_valid

        # Generate code for next time step
        code = generator.generate_code(timestamp + 30)
        is_valid = generator.verify_code(code, timestamp, window=1)
        assert is_valid

    def test_verify_code_outside_window(self):
        """Test that codes outside window are rejected"""
        generator = TOTPGenerator()
        timestamp = 1704067200

        # Generate code 2 time steps ago
        code = generator.generate_code(timestamp - 60)

        # Should be invalid with window=1 (only checks ±30s)
        is_valid = generator.verify_code(code, timestamp, window=1)
        assert not is_valid

    def test_verify_code_uses_constant_time_comparison(self):
        """Test that verification uses secrets.compare_digest"""
        generator = TOTPGenerator()
        timestamp = int(time.time())

        with patch("sark.security.mfa.secrets.compare_digest") as mock_compare:
            mock_compare.return_value = True

            generator.verify_code("123456", timestamp)

            # Should have called compare_digest
            assert mock_compare.called

    def test_totp_rfc6238_compliance(self):
        """Test TOTP implementation against RFC 6238 test vectors"""
        # RFC 6238 test vector
        # Secret: "12345678901234567890" (ASCII)
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # Base32 of above
        generator = TOTPGenerator(secret=secret)

        # RFC 6238 test case: timestamp 59, expected code 94287082
        # Time step = 59 // 30 = 1
        code = generator.generate_code(59)

        # Note: RFC uses 8-digit codes, we use 6-digit
        # So we check the last 6 digits
        assert code == "287082"

    def test_different_secrets_generate_different_codes(self):
        """Test that different secrets generate different codes"""
        gen1 = TOTPGenerator()
        gen2 = TOTPGenerator()

        timestamp = int(time.time())

        code1 = gen1.generate_code(timestamp)
        code2 = gen2.generate_code(timestamp)

        # With different secrets, codes should be different
        assert code1 != code2


class TestMFAChallengeSystem:
    """Test MFA challenge system"""

    @pytest.fixture
    def mock_storage(self):
        """Create mock storage"""
        storage = AsyncMock()
        storage.get.return_value = None
        storage.set.return_value = None
        return storage

    @pytest.fixture
    def mock_services(self):
        """Create mock service dependencies"""
        return {
            "sms_service": AsyncMock(),
            "push_service": AsyncMock(),
            "email_service": AsyncMock(),
            "audit_logger": AsyncMock(),
        }

    @pytest.fixture
    def mfa_system(self, mock_storage, mock_services):
        """Create MFA system with mocks"""
        return MFAChallengeSystem(
            storage=mock_storage,
            sms_service=mock_services["sms_service"],
            push_service=mock_services["push_service"],
            email_service=mock_services["email_service"],
            audit_logger=mock_services["audit_logger"],
        )

    # Challenge Creation Tests

    @pytest.mark.asyncio
    async def test_create_totp_challenge(self, mfa_system):
        """Test creating TOTP challenge"""
        challenge = await mfa_system._create_challenge(
            "user123", "delete_resource", MFAMethod.TOTP
        )

        assert challenge.user_id == "user123"
        assert challenge.action == "delete_resource"
        assert challenge.method == MFAMethod.TOTP
        assert challenge.status == MFAStatus.PENDING
        assert challenge.code is None  # TOTP doesn't use codes
        assert challenge.attempts == 0
        assert challenge.expires_at > challenge.created_at

    @pytest.mark.asyncio
    async def test_create_sms_challenge(self, mfa_system):
        """Test creating SMS challenge with code"""
        challenge = await mfa_system._create_challenge(
            "user123", "delete_resource", MFAMethod.SMS
        )

        assert challenge.method == MFAMethod.SMS
        assert challenge.code is not None
        assert len(challenge.code) == 6
        assert challenge.code.isdigit()

    @pytest.mark.asyncio
    async def test_create_email_challenge(self, mfa_system):
        """Test creating Email challenge with code"""
        challenge = await mfa_system._create_challenge(
            "user123", "delete_resource", MFAMethod.EMAIL
        )

        assert challenge.method == MFAMethod.EMAIL
        assert challenge.code is not None
        assert len(challenge.code) == 6

    @pytest.mark.asyncio
    async def test_create_push_challenge(self, mfa_system):
        """Test creating Push challenge"""
        challenge = await mfa_system._create_challenge(
            "user123", "delete_resource", MFAMethod.PUSH
        )

        assert challenge.method == MFAMethod.PUSH
        assert challenge.code is None  # Push doesn't use codes

    @pytest.mark.asyncio
    async def test_challenge_saved_to_storage(self, mfa_system, mock_storage):
        """Test that challenge is saved to storage"""
        challenge = await mfa_system._create_challenge(
            "user123", "delete_resource", MFAMethod.TOTP
        )

        # Verify storage.set was called
        mock_storage.set.assert_called_once()
        call_args = mock_storage.set.call_args
        assert f"mfa:challenge:{challenge.challenge_id}" in call_args[0][0]
        assert call_args[0][1] == challenge
        assert call_args[1]["ex"] == 120  # Default timeout

    @pytest.mark.asyncio
    async def test_challenge_expiration_time(self, mfa_system):
        """Test that challenge has correct expiration"""
        config = MFAConfig(timeout_seconds=300)
        system = MFAChallengeSystem(config=config)

        challenge = await system._create_challenge(
            "user123", "action", MFAMethod.TOTP
        )

        time_diff = (challenge.expires_at - challenge.created_at).total_seconds()
        assert time_diff == 300

    # Challenge Sending Tests

    @pytest.mark.asyncio
    async def test_send_sms_challenge(self, mfa_system, mock_services):
        """Test sending SMS challenge"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
        )

        await mfa_system._send_challenge(
            challenge, user_contact={"phone": "+1234567890"}
        )

        # Verify SMS was sent
        mock_services["sms_service"].send_sms.assert_called_once()
        call_args = mock_services["sms_service"].send_sms.call_args
        assert call_args[1]["to"] == "+1234567890"
        assert "123456" in call_args[1]["message"]

    @pytest.mark.asyncio
    async def test_send_email_challenge(self, mfa_system, mock_services):
        """Test sending Email challenge"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.EMAIL,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
        )

        await mfa_system._send_challenge(
            challenge, user_contact={"email": "user@example.com"}
        )

        # Verify email was sent
        mock_services["email_service"].send_email.assert_called_once()
        call_args = mock_services["email_service"].send_email.call_args
        assert call_args[1]["to"] == "user@example.com"
        assert "123456" in call_args[1]["body"]

    @pytest.mark.asyncio
    async def test_send_push_challenge(self, mfa_system, mock_services):
        """Test sending Push notification"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.PUSH,
            action="delete_resource",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
        )

        await mfa_system._send_challenge(challenge, user_contact={})

        # Verify push was sent
        mock_services["push_service"].send_push.assert_called_once()
        call_args = mock_services["push_service"].send_push.call_args
        assert call_args[1]["user_id"] == "user123"
        assert "delete_resource" in call_args[1]["body"]
        assert call_args[1]["data"]["challenge_id"] == "chal-123"

    @pytest.mark.asyncio
    async def test_send_totp_challenge_no_action(self, mfa_system, mock_services):
        """Test TOTP challenge doesn't send anything"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.TOTP,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
        )

        await mfa_system._send_challenge(challenge, user_contact={})

        # No services should be called for TOTP
        mock_services["sms_service"].send_sms.assert_not_called()
        mock_services["email_service"].send_email.assert_not_called()
        mock_services["push_service"].send_push.assert_not_called()

        # TOTP doesn't send anything, just logs internally

    @pytest.mark.asyncio
    async def test_send_challenge_missing_contact_info(
        self, mfa_system, mock_services, caplog
    ):
        """Test sending challenge without contact info logs warning"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
        )

        # No phone number provided
        await mfa_system._send_challenge(challenge, user_contact={})

        # Should log warning
        assert "Cannot send SMS" in caplog.text

    @pytest.mark.asyncio
    async def test_send_challenge_handles_service_error(
        self, mfa_system, mock_services, caplog
    ):
        """Test that send errors are caught and logged"""
        mock_services["sms_service"].send_sms.side_effect = Exception("SMS service down")

        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
        )

        # Should not raise exception
        await mfa_system._send_challenge(
            challenge, user_contact={"phone": "+1234567890"}
        )

        assert "Failed to send MFA challenge" in caplog.text

    # Code Verification Tests

    @pytest.mark.asyncio
    async def test_verify_totp_code_valid(self, mfa_system, mock_storage):
        """Test verifying valid TOTP code"""
        # Set up TOTP secret
        secret = mfa_system.get_totp_secret("user123")
        generator = TOTPGenerator(secret)
        code = generator.generate_code()

        # Create challenge
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.TOTP,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
        )

        mock_storage.get.return_value = challenge

        is_valid = await mfa_system.verify_code("user123", "chal-123", code)

        assert is_valid
        assert mock_storage.set.called  # Challenge updated
        # Verify final status
        final_challenge = mock_storage.set.call_args[0][1]
        assert final_challenge.status == MFAStatus.APPROVED

    @pytest.mark.asyncio
    async def test_verify_sms_code_valid(self, mfa_system, mock_storage):
        """Test verifying valid SMS code"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
        )

        mock_storage.get.return_value = challenge

        is_valid = await mfa_system.verify_code("user123", "chal-123", "123456")

        assert is_valid
        final_challenge = mock_storage.set.call_args[0][1]
        assert final_challenge.status == MFAStatus.APPROVED

    @pytest.mark.asyncio
    async def test_verify_code_invalid(self, mfa_system, mock_storage):
        """Test verifying invalid code"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
        )

        mock_storage.get.return_value = challenge

        is_valid = await mfa_system.verify_code("user123", "chal-123", "999999")

        assert not is_valid
        final_challenge = mock_storage.set.call_args[0][1]
        assert final_challenge.status == MFAStatus.PENDING  # Still pending after 1 attempt

    @pytest.mark.asyncio
    async def test_verify_code_challenge_not_found(self, mfa_system, mock_storage, caplog):
        """Test verifying code for non-existent challenge"""
        mock_storage.get.return_value = None

        is_valid = await mfa_system.verify_code("user123", "invalid-id", "123456")

        assert not is_valid
        assert "Challenge invalid-id not found" in caplog.text

    @pytest.mark.asyncio
    async def test_verify_code_wrong_user(self, mfa_system, mock_storage, caplog):
        """Test verifying code with wrong user ID"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
        )

        mock_storage.get.return_value = challenge

        is_valid = await mfa_system.verify_code("user456", "chal-123", "123456")

        assert not is_valid
        assert "attempted to verify challenge for" in caplog.text

    @pytest.mark.asyncio
    async def test_verify_code_expired(self, mfa_system, mock_storage):
        """Test verifying code for expired challenge"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now() - timedelta(seconds=200),
            expires_at=datetime.now() - timedelta(seconds=10),  # Expired
            status=MFAStatus.PENDING,
            code="123456",
        )

        mock_storage.get.return_value = challenge

        is_valid = await mfa_system.verify_code("user123", "chal-123", "123456")

        assert not is_valid
        final_challenge = mock_storage.set.call_args[0][1]
        assert final_challenge.status == MFAStatus.EXPIRED

    @pytest.mark.asyncio
    async def test_verify_code_max_attempts_exceeded(self, mfa_system, mock_storage, caplog):
        """Test that max attempts are enforced"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
            attempts=3,  # Already at max
            max_attempts=3,
        )

        mock_storage.get.return_value = challenge

        is_valid = await mfa_system.verify_code("user123", "chal-123", "999999")

        assert not is_valid
        assert "Max attempts exceeded" in caplog.text
        final_challenge = mock_storage.set.call_args[0][1]
        assert final_challenge.status == MFAStatus.DENIED

    @pytest.mark.asyncio
    async def test_verify_code_increments_attempts(self, mfa_system, mock_storage):
        """Test that attempts counter is incremented"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
            code="123456",
            attempts=0,
            max_attempts=3,
        )

        mock_storage.get.return_value = challenge

        # First attempt - wrong code
        await mfa_system.verify_code("user123", "chal-123", "999999")
        updated = mock_storage.set.call_args[0][1]
        assert updated.attempts == 1

    @pytest.mark.asyncio
    async def test_verify_push_approval(self, mfa_system, mock_storage):
        """Test verifying push notification approval"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.PUSH,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.APPROVED,  # User approved via push
        )

        mock_storage.get.return_value = challenge

        # For push, code doesn't matter
        is_valid = await mfa_system.verify_code("user123", "chal-123", "")

        assert is_valid

    # TOTP Secret Management Tests

    def test_get_totp_secret_creates_new(self, mfa_system):
        """Test that get_totp_secret creates secret for new user"""
        secret = mfa_system.get_totp_secret("user123")

        assert secret is not None
        assert len(secret) > 0
        # Verify it's stored
        assert "user123" in mfa_system._totp_secrets
        assert mfa_system._totp_secrets["user123"] == secret

    def test_get_totp_secret_returns_existing(self, mfa_system):
        """Test that get_totp_secret returns existing secret"""
        secret1 = mfa_system.get_totp_secret("user123")
        secret2 = mfa_system.get_totp_secret("user123")

        # Should return same secret
        assert secret1 == secret2

    # Storage Integration Tests

    @pytest.mark.asyncio
    async def test_get_challenge_from_storage(self, mfa_system, mock_storage):
        """Test retrieving challenge from storage"""
        expected_challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.TOTP,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.PENDING,
        )

        mock_storage.get.return_value = expected_challenge

        challenge = await mfa_system._get_challenge("chal-123")

        assert challenge == expected_challenge
        mock_storage.get.assert_called_once_with("mfa:challenge:chal-123")

    @pytest.mark.asyncio
    async def test_get_challenge_not_found(self, mfa_system, mock_storage):
        """Test retrieving non-existent challenge"""
        mock_storage.get.return_value = None

        challenge = await mfa_system._get_challenge("nonexistent")

        assert challenge is None

    @pytest.mark.asyncio
    async def test_update_challenge_in_storage(self, mfa_system, mock_storage):
        """Test updating challenge in storage"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.TOTP,
            action="delete",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.APPROVED,
        )

        await mfa_system._update_challenge(challenge)

        mock_storage.set.assert_called_once()
        call_args = mock_storage.set.call_args
        assert call_args[0][0] == "mfa:challenge:chal-123"
        assert call_args[0][1] == challenge

    @pytest.mark.asyncio
    async def test_storage_operations_without_storage(self):
        """Test that system works without storage backend"""
        system = MFAChallengeSystem(storage=None)

        # Should not raise errors
        challenge = await system._get_challenge("test")
        assert challenge is None

        await system._update_challenge(
            MFAChallenge(
                challenge_id="test",
                user_id="user",
                method=MFAMethod.TOTP,
                action="test",
                created_at=datetime.now(),
                expires_at=datetime.now(),
                status=MFAStatus.PENDING,
            )
        )  # No error

    # Audit Logging Tests

    @pytest.mark.asyncio
    async def test_log_mfa_success(self, mfa_system, mock_services):
        """Test logging successful MFA"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.TOTP,
            action="delete_resource",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.APPROVED,
            attempts=1,
        )

        await mfa_system._log_mfa_event(challenge, result=True)

        mock_services["audit_logger"].log_event.assert_called_once()
        call_args = mock_services["audit_logger"].log_event.call_args[1]
        assert call_args["event_type"] == "mfa_completed"
        assert call_args["user_id"] == "user123"
        assert call_args["result"] == "success"
        assert call_args["attempts"] == 1

    @pytest.mark.asyncio
    async def test_log_mfa_failure(self, mfa_system, mock_services):
        """Test logging failed MFA"""
        challenge = MFAChallenge(
            challenge_id="chal-123",
            user_id="user123",
            method=MFAMethod.SMS,
            action="delete_resource",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(seconds=120),
            status=MFAStatus.DENIED,
            attempts=3,
        )

        await mfa_system._log_mfa_event(challenge, result=False)

        call_args = mock_services["audit_logger"].log_event.call_args[1]
        assert call_args["event_type"] == "mfa_failed"
        assert call_args["result"] == "failure"

    @pytest.mark.asyncio
    async def test_log_mfa_without_audit_logger(self):
        """Test that logging works without audit logger"""
        system = MFAChallengeSystem(audit_logger=None)

        challenge = MFAChallenge(
            challenge_id="test",
            user_id="user",
            method=MFAMethod.TOTP,
            action="test",
            created_at=datetime.now(),
            expires_at=datetime.now(),
            status=MFAStatus.APPROVED,
        )

        # Should not raise error
        await system._log_mfa_event(challenge, True)

    @pytest.mark.asyncio
    async def test_log_mfa_handles_error(self, mfa_system, mock_services, caplog):
        """Test that logging errors are caught"""
        mock_services["audit_logger"].log_event.side_effect = Exception("Logging failed")

        challenge = MFAChallenge(
            challenge_id="test",
            user_id="user",
            method=MFAMethod.TOTP,
            action="test",
            created_at=datetime.now(),
            expires_at=datetime.now(),
            status=MFAStatus.APPROVED,
        )

        await mfa_system._log_mfa_event(challenge, True)

        assert "Failed to log MFA event" in caplog.text

    # Integration Tests

    @pytest.mark.asyncio
    async def test_require_mfa_complete_flow_totp(self, mfa_system, mock_storage, mock_services):
        """Test complete MFA flow with TOTP"""
        # Mock the wait_for_response to return immediately
        async def mock_wait(challenge, poll_interval=2.0):
            # Simulate user entering correct code
            challenge.status = MFAStatus.APPROVED
            await mfa_system._update_challenge(challenge)
            return True

        mfa_system._wait_for_response = mock_wait

        result = await mfa_system.require_mfa(
            "user123", "delete_resource", method=MFAMethod.TOTP
        )

        assert result is True
        # Verify audit log was called
        mock_services["audit_logger"].log_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_require_mfa_uses_default_method(self, mfa_system, mock_storage):
        """Test that require_mfa uses default method when not specified"""
        async def mock_wait(challenge, poll_interval=2.0):
            return True

        mfa_system._wait_for_response = mock_wait

        await mfa_system.require_mfa("user123", "action")

        # Check that TOTP challenge was created (default)
        challenge_created = mock_storage.set.call_args[0][1]
        assert challenge_created.method == MFAMethod.TOTP

    # Performance Tests

    def test_totp_generation_performance(self):
        """Test that TOTP generation is fast"""
        import time

        generator = TOTPGenerator()

        start = time.time()
        for _ in range(100):
            code = generator.generate_code()
        elapsed = time.time() - start

        assert code is not None
        # TOTP generation should be very fast (100 iterations)
        assert elapsed < 0.1  # 100ms for 100 iterations = 1ms per operation

    def test_totp_verification_performance(self):
        """Test that TOTP verification is fast"""
        import time

        generator = TOTPGenerator()
        code = generator.generate_code()

        start = time.time()
        for _ in range(100):
            result = generator.verify_code(code)
        elapsed = time.time() - start

        assert result is True
        # Verification should be fast (100 iterations, checks 3 windows each)
        assert elapsed < 0.3  # 300ms for 100 iterations = 3ms per operation
