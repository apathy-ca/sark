"""
Secret Scanner

Detects accidentally exposed secrets in tool responses:
- API keys (OpenAI, GitHub, AWS, etc.)
- Private keys
- Passwords
- Tokens
- Base64-encoded secrets
"""

import copy
from dataclasses import dataclass
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SecretFinding:
    """Represents a detected secret"""

    secret_type: str
    location: str
    matched_value: str  # Truncated for security
    confidence: float  # 0.0 to 1.0
    should_redact: bool = True
    _full_match: str = ""  # Full secret for redaction (internal use)


class SecretScanner:
    """Scan tool responses for accidentally exposed secrets"""

    # Performance tuning
    CHUNK_SIZE = 10000  # Process strings in 10KB chunks to prevent backtracking
    CHUNK_OVERLAP = 200  # Overlap to catch secrets at chunk boundaries
    MAX_STRING_LENGTH = 1_000_000  # 1MB max to prevent catastrophic backtracking

    # Secret detection patterns (pattern, name, confidence)
    SECRET_PATTERNS: list[tuple[str, str, float]] = [
        # API Keys
        (r"sk-[a-zA-Z0-9]{20,}", "OpenAI API Key", 1.0),
        (r"sk-proj-[a-zA-Z0-9\-_]{20,}", "OpenAI Project API Key", 1.0),
        (r"ghp_[a-zA-Z0-9]{20,}", "GitHub Personal Access Token", 1.0),
        (r"gho_[a-zA-Z0-9]{20,}", "GitHub OAuth Token", 1.0),
        (r"github_pat_[a-zA-Z0-9_]{82}", "GitHub Fine-Grained PAT", 1.0),
        (r"ghs_[a-zA-Z0-9]{36}", "GitHub App Token", 1.0),
        (r"glpat-[a-zA-Z0-9\-_]{20,}", "GitLab Personal Access Token", 1.0),
        (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID", 1.0),
        (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key", 0.95),
        (r"ya29\.[0-9A-Za-z\-_]+", "Google OAuth Token", 0.95),
        (r"xox[baprs]-[0-9a-zA-Z]{10,48}", "Slack Token", 1.0),
        # Private Keys
        (r"-----BEGIN[ A-Z]*PRIVATE KEY-----", "Private Key (PEM)", 1.0),
        (r"-----BEGIN RSA PRIVATE KEY-----", "RSA Private Key", 1.0),
        (r"-----BEGIN EC PRIVATE KEY-----", "EC Private Key", 1.0),
        (r"-----BEGIN OPENSSH PRIVATE KEY-----", "OpenSSH Private Key", 1.0),
        # JWT Tokens
        (r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+", "JWT Token", 0.9),
        # Generic secrets
        (
            r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:,.<>?]{8,}['\"]?",
            "Password",
            0.7,
        ),
        (
            r"(?i)(api[_\-]?key|apikey)\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}['\"]?",
            "Generic API Key",
            0.8,
        ),
        (r"(?i)(secret|token)\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}['\"]?", "Generic Secret/Token", 0.7),
        # Database connection strings
        (r"(?i)(postgres|mysql|mongodb)://[^:]+:[^@]+@[^/]+", "Database Connection String", 0.95),
        # Stripe
        (r"sk_live_[0-9a-zA-Z]{24,}", "Stripe Secret Key", 1.0),
        (r"rk_live_[0-9a-zA-Z]{24,}", "Stripe Restricted Key", 1.0),
        # Twilio
        (r"SK[0-9a-fA-F]{32}", "Twilio API Key", 0.85),
        # Anthropic
        (r"sk-ant-[a-zA-Z0-9\-_]{70,}", "Anthropic API Key", 1.0),
        # Azure Storage
        (r"AccountKey=[A-Za-z0-9+/]{86,90}={0,2}", "Azure Storage Account Key", 0.95),
        # Heroku
        (r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", "Heroku API Key", 0.75),
        # Mailgun
        (r"key-[0-9a-zA-Z]{32}", "Mailgun API Key", 0.95),
        # Potential base64 encoded secrets (long base64 strings - minimum 64 chars)
        (
            r"(?:[A-Za-z0-9+/]{4}){16,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?",
            "Potential Base64 Secret",
            0.5,
        ),
    ]

    # Patterns that should never be redacted (false positive reduction)
    FALSE_POSITIVE_PATTERNS = [
        r"127\.0\.0\.1",
        r"0\.0\.0\.0",
        r"test@test\.com",
        r"(?i)dummy",
        r"(?i)sample",
        r"(?i)placeholder",
    ]

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize secret scanner

        Args:
            config: Optional configuration (custom patterns, thresholds, etc.)
        """
        self.config = config or {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        self.compiled_secret_patterns = [
            (re.compile(pattern), name, confidence)
            for pattern, name, confidence in self.SECRET_PATTERNS
        ]

        self.compiled_fp_patterns = [
            re.compile(pattern) for pattern in self.FALSE_POSITIVE_PATTERNS
        ]

    def scan(self, data: dict[str, Any]) -> list[SecretFinding]:
        """
        Scan data for exposed secrets

        Args:
            data: Dictionary to scan (typically tool response)

        Returns:
            List of secret findings
        """
        findings = []

        # Batch candidate strings to reduce iteration overhead
        # Use min_str_len=16 as a balance between performance and detection
        # (Most API keys are 20+ chars, but some tokens can be 16+)
        candidates = [
            (loc, val)
            for loc, val in self._flatten_dict_generator(data, min_str_len=16)
            if self._could_contain_secret(val)
        ]

        # Scan all candidates
        for location, value in candidates:
            findings.extend(self._scan_value(value, location))

        return findings

    def redact_secrets(
        self, data: dict[str, Any], findings: list[SecretFinding] | None = None
    ) -> dict[str, Any]:
        """
        Redact secrets from data

        Args:
            data: Data to redact
            findings: Optional pre-computed findings (scans if not provided)

        Returns:
            Redacted copy of data
        """
        if findings is None:
            findings = self.scan(data)

        if not findings:
            return data

        # Deep copy to avoid modifying original
        redacted = copy.deepcopy(data)

        # Redact each finding
        for finding in findings:
            if finding.should_redact:
                redacted = self._redact_location(redacted, finding.location, finding._full_match)

        return redacted

    def _scan_value(self, value: str, location: str) -> list[SecretFinding]:
        """Scan a single string value for secrets"""
        # Truncate extremely long strings to prevent catastrophic backtracking
        if len(value) > self.MAX_STRING_LENGTH:
            logger.warning(
                f"String at {location} exceeds max length ({len(value)} > {self.MAX_STRING_LENGTH}), truncating"
            )
            value = value[: self.MAX_STRING_LENGTH]

        # Use chunked processing for large strings to prevent backtracking
        if len(value) > self.CHUNK_SIZE:
            return self._scan_value_chunked(value, location)
        else:
            return self._scan_value_direct(value, location)

    def _scan_value_direct(self, value: str, location: str) -> list[SecretFinding]:
        """Scan a string directly (for small strings)"""
        findings = []

        for pattern, secret_type, confidence in self.compiled_secret_patterns:
            matches = pattern.finditer(value)

            for match in matches:
                matched_text = match.group(0)

                # Check for false positives
                if self._is_false_positive(matched_text):
                    continue

                findings.append(
                    SecretFinding(
                        secret_type=secret_type,
                        location=location,
                        matched_value=self._truncate_secret(matched_text),  # Truncated for display
                        confidence=confidence,
                        should_redact=confidence >= 0.7,  # Only redact high-confidence findings
                        _full_match=matched_text,  # Full value for redaction
                    )
                )

        return findings

    def _scan_value_chunked(self, value: str, location: str) -> list[SecretFinding]:
        """Scan a large string in chunks to prevent backtracking"""
        findings = []
        seen_secrets = set()  # Deduplicate findings from overlapping chunks

        # Process in overlapping chunks
        for i in range(0, len(value), self.CHUNK_SIZE):
            # Include overlap to catch secrets at boundaries
            chunk_start = max(0, i - self.CHUNK_OVERLAP)
            chunk_end = min(len(value), i + self.CHUNK_SIZE + self.CHUNK_OVERLAP)
            chunk = value[chunk_start:chunk_end]

            # Scan this chunk
            chunk_findings = self._scan_value_direct(chunk, location)

            # Deduplicate
            for finding in chunk_findings:
                # Use full match as dedup key
                if finding._full_match not in seen_secrets:
                    seen_secrets.add(finding._full_match)
                    findings.append(finding)

        return findings

    # Pre-compiled set of secret prefixes for faster lookup
    _SECRET_PREFIXES = frozenset(
        [
            "sk-",
            "ghp_",
            "gho_",
            "ghs_",
            "glpat-",
            "AKIA",
            "AIza",
            "ya29",
            "xox",
            "sk_",
            "rk_",
            "pk_",
            "-----BEGIN",
            "postgres://",
            "mysql://",
            "mongodb://",
            "AccountKey=",
            "key-",
        ]
    )

    def _could_contain_secret(self, value: str) -> bool:
        """
        Ultra-fast pre-filter to skip strings unlikely to contain secrets.
        Optimized for minimal CPU usage per call.

        Returns:
            True if string might contain a secret, False if definitely not
        """
        # Check for common secret prefixes (very fast string search)
        # Use membership test on first few chars for common patterns
        if len(value) >= 3:
            prefix_3 = value[:3]
            if prefix_3 in ("sk-", "ghp", "gho", "ghs", "glp", "xox", "sk_", "rk_", "pk_", "key"):
                return True

            # Check for longer prefixes
            if value[:4] == "AKIA" or value[:4] == "AIza" or value[:4] == "ya29" or value[:4] == "key-":
                return True

            if (
                value.startswith("-----BEGIN")
                or value.startswith("postgres://")
                or value.startswith("mysql://")
                or value.startswith("mongodb://")
            ):
                return True

        # Check for UUID pattern (potential Heroku key)
        if len(value) == 36 and value.count('-') == 4:
            return True

        # Check for secret keywords (case-insensitive for these specific ones)
        if "password" in value or "secret" in value or "token" in value or "api_key" in value or "AccountKey=" in value:
            return True

        # For longer strings (40+), check if they look like base64/random tokens
        # Most real secrets are 32-100 chars and mostly alphanumeric
        if len(value) >= 40:
            # Count alnum chars - if >80% and long enough, likely a token
            # Use a faster approximation: check first 40 chars only
            sample = value[:40]
            alnum = sum(c.isalnum() for c in sample)
            if alnum > 32:  # >80% of 40
                return True

        return False

    def _is_false_positive(self, value: str) -> bool:
        """Check if value matches false positive patterns"""
        return any(pattern.search(value) for pattern in self.compiled_fp_patterns)

    def _truncate_secret(self, secret: str, show_chars: int = 10) -> str:
        """Truncate secret for logging (show first N chars only)"""
        if len(secret) <= show_chars:
            return secret[:3] + "..."

        return secret[:show_chars] + "..."

    def _flatten_dict_generator(
        self, data: Any, prefix: str = "", depth: int = 0, min_str_len: int = 20
    ):
        """
        Generator that yields (location, value) pairs from nested data structures.
        Only yields string values >= min_str_len for efficiency.
        Optimized to avoid string operations for filtered values.

        Args:
            data: Data to flatten (dict, list, or scalar)
            prefix: Current key prefix
            depth: Current recursion depth (prevents stack overflow)
            min_str_len: Minimum string length to yield (default 20)

        Yields:
            Tuples of (location, string_value) where len(string_value) >= min_str_len
        """
        # Prevent infinite recursion
        MAX_DEPTH = 50
        if depth > MAX_DEPTH:
            return

        if isinstance(data, dict):
            # Check if prefix needs to be computed (only if we might yield)
            if prefix:
                for key, value in data.items():
                    # Quick check: if value is a short string, skip entirely (no string ops)
                    if isinstance(value, str):
                        if len(value) >= min_str_len:
                            yield (f"{prefix}.{key}", value)
                    elif isinstance(value, (dict, list)):
                        yield from self._flatten_dict_generator(
                            value, f"{prefix}.{key}", depth + 1, min_str_len
                        )
            else:
                for key, value in data.items():
                    if isinstance(value, str):
                        if len(value) >= min_str_len:
                            yield (key, value)
                    elif isinstance(value, (dict, list)):
                        yield from self._flatten_dict_generator(value, key, depth + 1, min_str_len)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, str):
                    if len(item) >= min_str_len:
                        yield (f"{prefix}[{i}]", item)
                elif isinstance(item, (dict, list)):
                    yield from self._flatten_dict_generator(
                        item, f"{prefix}[{i}]", depth + 1, min_str_len
                    )

        elif isinstance(data, str) and len(data) >= min_str_len:
            yield (prefix, data)

    def _flatten_dict(self, data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """
        Flatten nested dictionary

        Args:
            data: Dictionary to flatten
            prefix: Current key prefix

        Returns:
            Flattened dictionary with dotted keys
        """
        flat = {}

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flat.update(self._flatten_dict(value, full_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flat.update(self._flatten_dict(item, f"{full_key}[{i}]"))
                    else:
                        flat[f"{full_key}[{i}]"] = item
            else:
                flat[full_key] = value

        return flat

    def _redact_location(self, data: dict[str, Any], location: str, secret: str) -> dict[str, Any]:
        """
        Redact a secret at a specific location

        Args:
            data: Data dictionary
            location: Dotted path to secret (e.g., "response.data.api_key")
            secret: Secret value to redact

        Returns:
            Data with secret redacted
        """
        # Parse location path
        keys = self._parse_location(location)

        # Navigate to parent
        current = data
        for key in keys[:-1]:
            if isinstance(current, dict):
                current = current.get(key, {})
            elif isinstance(current, list) and isinstance(key, int):
                current = current[key] if key < len(current) else {}

        # Redact final value
        final_key = keys[-1]
        if isinstance(current, dict) and final_key in current:
            if isinstance(current[final_key], str):
                # Replace secret with redaction marker
                current[final_key] = current[final_key].replace(secret, "[REDACTED]")

        return data

    def _parse_location(self, location: str) -> list[Any]:
        """
        Parse location string into keys

        Args:
            location: Dotted path like "response.data[0].key"

        Returns:
            List of keys (strings and ints for array indices)
        """
        keys = []
        parts = location.split(".")

        for part in parts:
            # Check for array index
            if "[" in part:
                # Split on '[' to get key and index
                key, rest = part.split("[", 1)
                if key:
                    keys.append(key)

                # Extract index
                index_str = rest.rstrip("]")
                try:
                    keys.append(int(index_str))
                except ValueError:
                    keys.append(index_str)
            else:
                keys.append(part)

        return keys
