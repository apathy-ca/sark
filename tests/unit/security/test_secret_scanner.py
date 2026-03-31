"""
Unit tests for Secret Scanner (merged implementation).

Tests both dict-oriented and text-oriented scanning, redaction,
entropy detection, context awareness, and performance.
"""

import time

import pytest

from src.sark.security.secret_scanner import SecretFinding, SecretScanner, SecretType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def scanner():
    return SecretScanner()


# ---------------------------------------------------------------------------
# Dict API — pattern detection
# ---------------------------------------------------------------------------


class TestDictScanning:
    """Test scan(dict) for each secret type."""

    def test_openai_api_key(self, scanner):
        data = {"response": {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.OPENAI_API_KEY for f in findings)
        assert findings[0].confidence == 1.0

    def test_openai_project_key(self, scanner):
        data = {"key": "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.OPENAI_PROJECT_KEY for f in findings)

    def test_anthropic_key(self, scanner):
        data = {
            "api_key": "sk-ant-api03-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqr"
        }
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.ANTHROPIC_API_KEY for f in findings)

    def test_github_pat(self, scanner):
        data = {"token": "ghp_1234567890abcdefghijklmnopqrstuvwx"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.GITHUB_PAT for f in findings)

    def test_github_oauth(self, scanner):
        data = {"auth": "gho_1234567890abcdefghijklmnopqrstuvwx"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.GITHUB_OAUTH for f in findings)

    def test_aws_access_key(self, scanner):
        data = {"credentials": {"access_key": "AKIAIOSFODNN7EXAMPLE"}}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.AWS_ACCESS_KEY for f in findings)

    def test_google_api_key(self, scanner):
        data = {"key": "AIzaSyA1234567890abcdefghijklmnopqrstuv"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.GOOGLE_API_KEY for f in findings)

    def test_slack_token(self, scanner):
        data = {"slack_token": "xox" + "b-" + "0000000000-0000000000-TESTINGTESTINGTESTING"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.SLACK_TOKEN for f in findings)

    def test_stripe_secret_key(self, scanner):
        data = {"stripe": "sk_" + "live" + "_00000000000000000000000000"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.STRIPE_KEY for f in findings)

    def test_rsa_private_key(self, scanner):
        data = {"key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJ\n-----END RSA PRIVATE KEY-----"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.PRIVATE_KEY for f in findings)

    def test_openssh_private_key(self, scanner):
        data = {"ssh_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXk"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.PRIVATE_KEY for f in findings)

    def test_jwt_token(self, scanner):
        data = {
            "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        }
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.JWT_TOKEN for f in findings)

    def test_password_field(self, scanner):
        data = {"config": "password=MySecretPass123!"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.GENERIC_PASSWORD for f in findings)

    def test_generic_api_key(self, scanner):
        data = {"settings": "api_key=abcd1234efgh5678ijkl"}
        findings = scanner.scan(data)
        assert len(findings) > 0

    def test_postgres_connection(self, scanner):
        data = {"db": "postgres://user:password@localhost:5432/mydb"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.DATABASE_URL for f in findings)

    def test_mysql_connection(self, scanner):
        data = {"connection": "mysql://admin:secret@db.example.com/prod"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.DATABASE_URL for f in findings)

    def test_azure_storage_key(self, scanner):
        data = {
            "connection_string": "DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrst+/ab=="
        }
        findings = scanner.scan(data)
        assert any(
            f.secret_type in (SecretType.AZURE_STORAGE_KEY, SecretType.AZURE_CONNECTION_STRING)
            for f in findings
        )

    def test_heroku_key(self, scanner):
        data = {"config": "HEROKU_API_KEY=12345678-1234-1234-1234-123456789abc"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.HEROKU_API_KEY for f in findings)

    def test_bare_uuid_not_flagged_as_heroku(self, scanner):
        data = {"request_id": "12345678-1234-1234-1234-123456789abc"}
        findings = scanner.scan(data)
        assert not any(f.secret_type == SecretType.HEROKU_API_KEY for f in findings)

    def test_mailgun_key(self, scanner):
        data = {"mailgun_key": "key-1234567890abcdef1234567890abcdef"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.MAILGUN_API_KEY for f in findings)

    def test_sendgrid_key(self, scanner):
        data = {"key": "SG.abcdefghijklmnopqrstuv.ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqr"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.SENDGRID_API_KEY for f in findings)

    def test_npm_token(self, scanner):
        data = {"token": "npm_abcdefghijklmnopqrstuvwxyz123456"}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.NPM_TOKEN for f in findings)

    def test_digitalocean_token(self, scanner):
        data = {"token": "dop_v1_" + "a1b2c3d4" * 8}
        findings = scanner.scan(data)
        assert any(f.secret_type == SecretType.DIGITALOCEAN_TOKEN for f in findings)


# ---------------------------------------------------------------------------
# Text API — pattern detection
# ---------------------------------------------------------------------------


class TestTextScanning:
    """Test scan_text(str) for secrets in raw text."""

    def test_openai_key_in_text(self, scanner):
        text = "My API key is sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        findings = scanner.scan_text(text)
        assert len(findings) > 0
        assert findings[0].secret_type == SecretType.OPENAI_API_KEY
        assert findings[0].start_pos is not None
        assert findings[0].line_number == 1

    def test_multiline_text_line_numbers(self, scanner):
        text = "line 1\nline 2\napi_key=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN\nline 4"
        findings = scanner.scan_text(text)
        assert len(findings) > 0
        assert findings[0].line_number == 3

    def test_slack_webhook_in_text(self, scanner):
        # Construct webhook URL to avoid GitHub push protection
        text = "Webhook URL: " + "https://hooks.slack.com/services/" + "T01234567/B01234567/abcdefghijklmnopqrstuvwx"
        findings = scanner.scan_text(text)
        assert any(f.secret_type == SecretType.SLACK_WEBHOOK for f in findings)

    def test_multiple_secrets_in_text(self, scanner):
        text = (
            "OPENAI_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN\n"
            "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwx\n"
        )
        findings = scanner.scan_text(text)
        types = {f.secret_type for f in findings}
        assert SecretType.OPENAI_API_KEY in types
        assert SecretType.GITHUB_PAT in types

    def test_sorted_by_position(self, scanner):
        text = (
            "first: ghp_1234567890abcdefghijklmnopqrstuvwx "
            "second: sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        )
        findings = scanner.scan_text(text)
        assert len(findings) >= 2
        positions = [f.start_pos for f in findings]
        assert positions == sorted(positions)

    def test_skip_test_fixture(self, scanner):
        findings = scanner.scan_text(
            "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN",
            file_path="/tests/fixtures/sample_data.py",
        )
        assert len(findings) == 0

    def test_skip_test_fixture_disabled(self):
        scanner = SecretScanner(skip_test_fixtures=False)
        findings = scanner.scan_text(
            "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN",
            file_path="/tests/fixtures/sample_data.py",
        )
        assert len(findings) > 0


# ---------------------------------------------------------------------------
# Dict redaction
# ---------------------------------------------------------------------------


class TestDictRedaction:
    """Test redact_secrets(dict) for secret removal."""

    def test_redact_single(self, scanner):
        data = {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        redacted = scanner.redact_secrets(data)
        assert "[REDACTED]" in redacted["api_key"]
        assert "sk-" not in redacted["api_key"]

    def test_redact_multiple(self, scanner):
        data = {
            "openai_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN",
            "github_token": "ghp_1234567890abcdefghijklmnopqrstuvwx",
        }
        redacted = scanner.redact_secrets(data)
        assert "[REDACTED]" in redacted["openai_key"]
        assert "[REDACTED]" in redacted["github_token"]

    def test_redact_nested(self, scanner):
        data = {
            "user": {
                "credentials": {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
            }
        }
        redacted = scanner.redact_secrets(data)
        assert "[REDACTED]" in redacted["user"]["credentials"]["api_key"]

    def test_preserves_structure(self, scanner):
        data = {
            "message": "Your API key is sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN for authentication",
            "other_field": "normal data",
        }
        redacted = scanner.redact_secrets(data)
        assert redacted["other_field"] == "normal data"
        assert "[REDACTED]" in redacted["message"]

    def test_does_not_modify_original(self, scanner):
        data = {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        original_value = data["api_key"]
        scanner.redact_secrets(data)
        assert data["api_key"] == original_value


# ---------------------------------------------------------------------------
# Polymorphic redaction — redact(Any)
# ---------------------------------------------------------------------------


class TestPolymorphicRedaction:
    """Test redact(Any) which handles str, dict, list, tuple."""

    def test_redact_string(self, scanner):
        text = "My key is sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        redacted, findings = scanner.redact(text)
        assert isinstance(redacted, str)
        assert "[REDACTED]" in redacted
        assert len(findings) > 0

    def test_redact_dict(self, scanner):
        data = {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        redacted, findings = scanner.redact(data)
        assert isinstance(redacted, dict)
        assert "[REDACTED]" in redacted["api_key"]

    def test_redact_nested_dict(self, scanner):
        data = {"outer": {"inner": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}}
        redacted, findings = scanner.redact(data)
        assert "[REDACTED]" in redacted["outer"]["inner"]

    def test_redact_list(self, scanner):
        data = ["safe", "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN", "safe"]
        redacted, findings = scanner.redact(data)
        assert isinstance(redacted, list)
        assert "[REDACTED]" in redacted[1]
        assert redacted[0] == "safe"

    def test_redact_tuple(self, scanner):
        data = ("safe", "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN")
        redacted, findings = scanner.redact(data)
        assert isinstance(redacted, tuple)
        assert "[REDACTED]" in redacted[1]

    def test_redact_non_string_passthrough(self, scanner):
        data = {"count": 42, "flag": True, "nothing": None}
        redacted, findings = scanner.redact(data)
        assert redacted == data
        assert len(findings) == 0

    def test_custom_placeholder(self):
        scanner = SecretScanner(redaction_placeholder="***REMOVED***")
        text = "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"
        redacted, _ = scanner.redact(text)
        assert "***REMOVED***" in redacted


# ---------------------------------------------------------------------------
# High entropy detection
# ---------------------------------------------------------------------------


class TestHighEntropyDetection:
    """Test Shannon entropy-based secret detection (text mode only)."""

    def test_high_entropy_with_context(self, scanner):
        # Base64-like string with secret keyword nearby
        b64 = "A" * 15 + "bCdEfGhIjK1234567890" * 3 + "lMnOpQrStU" * 2
        # Need a genuinely high-entropy string (>4.8 bits/char)
        import string
        import random

        random.seed(42)
        high_entropy = "".join(random.choices(string.ascii_letters + string.digits, k=80))
        text = f"secret_key = {high_entropy}"
        findings = scanner.scan_text(text)
        # Should find either a generic secret or high entropy match
        assert len(findings) > 0

    def test_low_entropy_ignored(self, scanner):
        # Repeated pattern — low entropy, no secret context
        text = "data = " + "AAAA" * 20
        findings = scanner.scan_text(text)
        assert not any(f.secret_type == SecretType.HIGH_ENTROPY_SECRET for f in findings)

    def test_uuid_not_flagged_as_entropy(self, scanner):
        text = "request_id = 12345678-1234-1234-1234-123456789abc"
        findings = scanner.scan_text(text)
        assert not any(f.secret_type == SecretType.HIGH_ENTROPY_SECRET for f in findings)

    def test_sha256_not_flagged_as_entropy(self, scanner):
        text = "hash = " + "a" * 64
        findings = scanner.scan_text(text)
        assert not any(f.secret_type == SecretType.HIGH_ENTROPY_SECRET for f in findings)


# ---------------------------------------------------------------------------
# Context-aware scanning
# ---------------------------------------------------------------------------


class TestContextAwareScanning:
    """Test code block skipping, suppression annotations."""

    def test_skip_code_block(self, scanner):
        text = (
            "Here is an example:\n"
            "```python\n"
            "api_key = sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN\n"
            "```\n"
        )
        findings = scanner.scan_text(text)
        assert not any(f.secret_type == SecretType.OPENAI_API_KEY for f in findings)

    def test_code_block_skipping_disabled(self):
        scanner = SecretScanner(skip_code_blocks=False)
        text = (
            "```python\n"
            "api_key = sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN\n"
            "```\n"
        )
        findings = scanner.scan_text(text)
        assert any(f.secret_type == SecretType.OPENAI_API_KEY for f in findings)

    def test_inline_suppression(self, scanner):
        text = "api_key = sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN  # sark-secret-scanner: ignore"
        findings = scanner.scan_text(text)
        assert not any(f.secret_type == SecretType.OPENAI_API_KEY for f in findings)

    def test_nosecret_annotation(self, scanner):
        text = "api_key = sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN  # nosecret"
        findings = scanner.scan_text(text)
        assert not any(f.secret_type == SecretType.OPENAI_API_KEY for f in findings)

    def test_block_suppression(self, scanner):
        text = (
            "# sark-secret-scanner: ignore-start\n"
            "OPENAI_KEY=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN\n"
            "GITHUB_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwx\n"
            "# sark-secret-scanner: ignore-end\n"
        )
        findings = scanner.scan_text(text)
        assert len(findings) == 0

    def test_suppression_disabled(self):
        scanner = SecretScanner(enable_suppressions=False)
        text = "api_key = sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN  # nosecret"
        findings = scanner.scan_text(text)
        assert any(f.secret_type == SecretType.OPENAI_API_KEY for f in findings)

    def test_secret_outside_suppressed_block_still_detected(self, scanner):
        text = (
            "# sark-secret-scanner: ignore-start\n"
            "safe_key=sk-ignored12345678901234567890ABCDE\n"
            "# sark-secret-scanner: ignore-end\n"
            "leaked_key=sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN\n"
        )
        findings = scanner.scan_text(text)
        assert any(f.secret_type == SecretType.OPENAI_API_KEY for f in findings)


# ---------------------------------------------------------------------------
# False positives
# ---------------------------------------------------------------------------


class TestFalsePositives:
    """Test that common non-secrets don't trigger false positives."""

    def test_localhost_not_flagged(self, scanner):
        data = {"endpoint": "http://localhost:8000/api"}
        findings = scanner.scan(data)
        high_confidence = [f for f in findings if f.confidence >= 0.7]
        assert len(high_confidence) == 0

    def test_example_domain_not_flagged(self, scanner):
        data = {"url": "https://api.example.com/users"}
        findings = scanner.scan(data)
        assert len([f for f in findings if f.should_redact]) == 0

    def test_dummy_placeholder_not_flagged(self, scanner):
        data = {"password": "test_password_dummy_value"}
        findings = scanner.scan(data)
        high_confidence = [f for f in findings if f.should_redact]
        assert len(high_confidence) == 0 or all(
            f.secret_type == SecretType.GENERIC_PASSWORD for f in high_confidence
        )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:

    def test_empty_dict(self, scanner):
        assert scanner.scan({}) == []

    def test_non_string_values(self, scanner):
        data = {"number": 12345, "boolean": True, "null": None, "list": [1, 2, 3]}
        assert scanner.scan(data) == []

    def test_empty_string_text(self, scanner):
        assert scanner.scan_text("") == []

    def test_very_long_string(self, scanner):
        data = {"data": "a" * 10000 + "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        findings = scanner.scan(data)
        assert len(findings) > 0

    def test_list_of_dicts(self, scanner):
        data = {
            "items": [
                {"key": "safe_value_that_is_long_enough"},
                {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"},
                {"key": "another_safe_value_long_enough"},
            ]
        }
        findings = scanner.scan(data)
        assert len(findings) > 0
        assert "items[1]" in findings[0].location

    def test_secret_truncation_in_findings(self, scanner):
        data = {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        findings = scanner.scan(data)
        assert len(findings[0].matched_value) < len(data["key"])
        assert "..." in findings[0].matched_value

    def test_findings_have_positions(self, scanner):
        data = {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        findings = scanner.scan(data)
        assert findings[0].start_pos is not None
        assert findings[0].end_pos is not None
        assert findings[0].end_pos > findings[0].start_pos

    def test_confidence_levels(self, scanner):
        # High confidence
        data = {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        findings = scanner.scan(data)
        assert findings[0].confidence >= 0.9

    def test_secret_type_is_enum(self, scanner):
        data = {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
        findings = scanner.scan(data)
        assert isinstance(findings[0].secret_type, SecretType)
        assert findings[0].secret_type.value == "openai_api_key"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:

    def test_dict_scan_100_fields(self, scanner):
        data = {f"field_{i}": f"normal value {i} with enough length" for i in range(100)}
        data["field_50"] = "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"

        start = time.time()
        findings = scanner.scan(data)
        duration = time.time() - start

        assert len(findings) > 0
        assert duration < 0.1  # < 100ms for 100 fields

    def test_text_scan_performance(self, scanner):
        text = "\n".join(f"line {i}: normal content here" for i in range(1000))
        text += "\nsk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN\n"

        start = time.time()
        findings = scanner.scan_text(text)
        duration = time.time() - start

        assert len(findings) > 0
        assert duration < 0.5  # < 500ms for 1000 lines

    def test_redact_performance(self, scanner):
        data = {f"field_{i}": f"value {i} that is long enough for scanning" for i in range(50)}
        data["field_25"] = "ghp_1234567890abcdefghijklmnopqrstuvwx"

        start = time.time()
        redacted, findings = scanner.redact(data)
        duration = time.time() - start

        assert len(findings) > 0
        assert duration < 0.5
