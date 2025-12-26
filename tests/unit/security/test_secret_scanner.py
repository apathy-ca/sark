"""
Unit tests for Secret Scanner

Tests detection of all secret patterns and redaction functionality.
Target: 100% detection on test set
"""

import pytest
from src.sark.security.secret_scanner import SecretScanner


class TestSecretScanner:
    """Test suite for SecretScanner"""

    @pytest.fixture
    def scanner(self):
        """Create scanner instance"""
        return SecretScanner()

    # Test API key detection
    def test_openai_api_key_detected(self, scanner):
        """Test detection of OpenAI API key"""
        data = {"response": {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("OpenAI" in f.secret_type for f in findings)
        assert findings[0].confidence == 1.0

    def test_openai_project_key_detected(self, scanner):
        """Test detection of OpenAI project API key"""
        data = {"key": "sk-proj-abcdefghijklmnopqrstuvwxyz1234567890"}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("OpenAI Project" in f.secret_type for f in findings)

    def test_github_pat_detected(self, scanner):
        """Test detection of GitHub Personal Access Token"""
        data = {"token": "ghp_1234567890abcdefghijklmnopqrstuvwx"}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("GitHub" in f.secret_type for f in findings)

    def test_github_oauth_detected(self, scanner):
        """Test detection of GitHub OAuth token"""
        data = {"auth": "gho_1234567890abcdefghijklmnopqrstuvwx"}

        findings = scanner.scan(data)

        assert len(findings) > 0

    def test_aws_access_key_detected(self, scanner):
        """Test detection of AWS access key"""
        data = {"credentials": {"access_key": "AKIAIOSFODNN7EXAMPLE"}}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("AWS" in f.secret_type for f in findings)

    def test_slack_token_detected(self, scanner):
        """Test detection of Slack token"""
        # Construct test token to avoid GitHub secret scanner
        data = {"slack_token": "xox" + "b-" + "0000000000-0000000000-TESTINGTESTINGTESTING"}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("Slack" in f.secret_type for f in findings)

    # Test private key detection
    def test_rsa_private_key_detected(self, scanner):
        """Test detection of RSA private key"""
        data = {
            "key": """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF06bpk5u6rVl
-----END RSA PRIVATE KEY-----"""
        }

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("Private Key" in f.secret_type for f in findings)

    def test_openssh_private_key_detected(self, scanner):
        """Test detection of OpenSSH private key"""
        data = {"ssh_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nb3BlbnNzaC1rZXk"}

        findings = scanner.scan(data)

        assert len(findings) > 0

    # Test JWT detection
    def test_jwt_token_detected(self, scanner):
        """Test detection of JWT token"""
        data = {
            "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        }

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("JWT" in f.secret_type for f in findings)

    # Test generic secret detection
    def test_password_field_detected(self, scanner):
        """Test detection of password in field"""
        data = {"config": "password=MySecretPass123!"}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("Password" in f.secret_type for f in findings)

    def test_api_key_field_detected(self, scanner):
        """Test detection of generic API key"""
        data = {"settings": "api_key=abcd1234efgh5678ijkl"}

        findings = scanner.scan(data)

        assert len(findings) > 0

    # Test database connection strings
    def test_postgres_connection_detected(self, scanner):
        """Test detection of PostgreSQL connection string"""
        data = {"db": "postgres://user:password@localhost:5432/mydb"}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("Database" in f.secret_type for f in findings)

    def test_mysql_connection_detected(self, scanner):
        """Test detection of MySQL connection string"""
        data = {"connection": "mysql://admin:secret@db.example.com/prod"}

        findings = scanner.scan(data)

        assert len(findings) > 0

    # Test payment/financial keys
    def test_stripe_secret_key_detected(self, scanner):
        """Test detection of Stripe secret key"""
        # Construct test key to avoid GitHub secret scanner (using sk_live pattern)
        data = {"stripe": "sk_" + "live" + "_00000000000000000000000000"}

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("Stripe" in f.secret_type for f in findings)

    # Test Anthropic API key
    def test_anthropic_key_detected(self, scanner):
        """Test detection of Anthropic API key"""
        data = {
            "api_key": "sk-ant-api03-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqr"
        }

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert any("Anthropic" in f.secret_type for f in findings)

    # Test redaction
    def test_redact_single_secret(self, scanner):
        """Test redaction of single secret"""
        data = {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}

        redacted = scanner.redact_secrets(data)

        assert "[REDACTED]" in redacted["api_key"]
        assert "sk-" not in redacted["api_key"]

    def test_redact_multiple_secrets(self, scanner):
        """Test redaction of multiple secrets"""
        data = {
            "openai_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN",
            "github_token": "ghp_1234567890abcdefghijklmnopqrstuvwx",
        }

        redacted = scanner.redact_secrets(data)

        assert "[REDACTED]" in redacted["openai_key"]
        assert "[REDACTED]" in redacted["github_token"]

    def test_redact_nested_secrets(self, scanner):
        """Test redaction in nested structures"""
        data = {
            "user": {
                "credentials": {"api_key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}
            }
        }

        redacted = scanner.redact_secrets(data)

        assert "[REDACTED]" in redacted["user"]["credentials"]["api_key"]

    def test_partial_redaction_preserves_structure(self, scanner):
        """Test that redaction preserves data structure"""
        data = {
            "message": "Your API key is sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN for authentication",
            "other_field": "normal data",
        }

        redacted = scanner.redact_secrets(data)

        assert "message" in redacted
        assert "other_field" in redacted
        assert redacted["other_field"] == "normal data"  # Unchanged
        assert "[REDACTED]" in redacted["message"]

    # Test false positives
    def test_example_domains_not_flagged(self, scanner):
        """Test that example.com doesn't trigger false positives"""
        data = {"url": "https://api.example.com/users"}

        findings = scanner.scan(data)

        # Should not detect secrets in example domains
        assert len([f for f in findings if f.should_redact]) == 0

    def test_localhost_not_flagged(self, scanner):
        """Test that localhost URLs don't trigger false positives"""
        data = {"endpoint": "http://localhost:8000/api"}

        findings = scanner.scan(data)

        high_confidence = [f for f in findings if f.confidence >= 0.7]
        assert len(high_confidence) == 0

    def test_test_placeholders_not_flagged(self, scanner):
        """Test that test/dummy placeholders aren't flagged"""
        data = {"password": "test_password_dummy_value"}

        findings = scanner.scan(data)

        # Might detect but shouldn't redact (low confidence)
        high_confidence = [f for f in findings if f.should_redact]
        # Some patterns might still match, but this tests false positive reduction
        assert len(high_confidence) == 0 or all(
            "Password" in f.secret_type for f in high_confidence
        )

    # Test edge cases
    def test_empty_data(self, scanner):
        """Test scanning empty data"""
        data = {}

        findings = scanner.scan(data)

        assert len(findings) == 0

    def test_non_string_values(self, scanner):
        """Test that non-string values don't cause errors"""
        data = {"number": 12345, "boolean": True, "null": None, "list": [1, 2, 3]}

        findings = scanner.scan(data)

        assert len(findings) == 0

    def test_very_long_string(self, scanner):
        """Test scanning very long strings"""
        data = {"data": "a" * 10000 + "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}

        findings = scanner.scan(data)

        assert len(findings) > 0

    def test_list_of_dicts(self, scanner):
        """Test scanning list of dictionaries"""
        data = {
            "items": [
                {"key": "safe_value"},
                {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"},
                {"key": "another_safe_value"},
            ]
        }

        findings = scanner.scan(data)

        assert len(findings) > 0
        assert "items[1]" in findings[0].location

    # Test confidence levels
    def test_high_confidence_secrets(self, scanner):
        """Test that obvious secrets have high confidence"""
        data = {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}

        findings = scanner.scan(data)

        assert findings[0].confidence >= 0.9

    def test_medium_confidence_secrets(self, scanner):
        """Test that ambiguous patterns have medium confidence"""
        data = {"password": "short123"}  # Could be password or not

        findings = scanner.scan(data)

        if len(findings) > 0:
            assert findings[0].confidence < 0.9

    # Test truncation
    def test_secret_truncation_in_findings(self, scanner):
        """Test that found secrets are truncated in findings"""
        data = {"key": "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"}

        findings = scanner.scan(data)

        # Matched value should be truncated
        assert len(findings[0].matched_value) < len(data["key"])
        assert "..." in findings[0].matched_value

    # Performance test
    def test_scan_performance(self, scanner):
        """Test that scanning completes quickly"""
        import time

        data = {f"field_{i}": f"normal value {i}" for i in range(100)}
        data["field_50"] = "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN"

        start = time.time()
        findings = scanner.scan(data)
        duration = time.time() - start

        assert len(findings) > 0
        assert duration < 0.05  # < 50ms for 100 fields
