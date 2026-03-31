"""
Secret Scanner — detects and redacts exposed secrets.

Combines high-performance dict scanning (chunked, pre-filtered) with
context-aware text scanning (entropy detection, code block skipping,
suppression annotations).

Supports API keys, tokens, credentials, private keys, database URLs,
and high-entropy strings across 30+ providers.
"""

import copy
import logging
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class SecretType(str, Enum):
    """Types of secrets that can be detected."""

    # AI/ML Services
    OPENAI_API_KEY = "openai_api_key"
    OPENAI_PROJECT_KEY = "openai_project_key"
    ANTHROPIC_API_KEY = "anthropic_api_key"

    # Version Control
    GITHUB_PAT = "github_pat"
    GITHUB_OAUTH = "github_oauth"
    GITHUB_FINE_GRAINED_PAT = "github_fine_grained_pat"
    GITHUB_APP_TOKEN = "github_app_token"
    GITLAB_PAT = "gitlab_pat"

    # Cloud — AWS
    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"

    # Cloud — Google
    GOOGLE_API_KEY = "google_api_key"
    GOOGLE_OAUTH = "google_oauth"

    # Cloud — Azure
    AZURE_STORAGE_KEY = "azure_storage_key"
    AZURE_CONNECTION_STRING = "azure_connection_string"

    # Cloud — Other
    HEROKU_API_KEY = "heroku_api_key"
    DIGITALOCEAN_TOKEN = "digitalocean_token"

    # Communication
    SLACK_TOKEN = "slack_token"
    SLACK_WEBHOOK = "slack_webhook"
    TWILIO_API_KEY = "twilio_api_key"
    SENDGRID_API_KEY = "sendgrid_api_key"
    MAILGUN_API_KEY = "mailgun_api_key"

    # Payment
    STRIPE_KEY = "stripe_key"

    # Cryptographic
    PRIVATE_KEY = "private_key"
    JWT_TOKEN = "jwt_token"

    # Database
    DATABASE_URL = "database_url"

    # Package Managers
    NPM_TOKEN = "npm_token"
    PYPI_TOKEN = "pypi_token"

    # Generic
    GENERIC_PASSWORD = "generic_password"
    GENERIC_API_KEY = "generic_api_key"
    GENERIC_SECRET = "generic_secret"
    HIGH_ENTROPY_SECRET = "high_entropy_secret"
    BASE64_SECRET = "base64_secret"


@dataclass
class SecretFinding:
    """Represents a detected secret."""

    secret_type: SecretType
    location: str  # Dotted path for dict scanning, empty for text
    matched_value: str  # Truncated for display/logging
    confidence: float  # 0.0 to 1.0
    should_redact: bool = True
    full_match: str = ""  # Full matched text (for redaction)
    start_pos: int | None = None  # Character offset in scanned string
    end_pos: int | None = None
    line_number: int | None = None


class SecretScanner:
    """Scan data for accidentally exposed secrets.

    Provides two scanning modes:
    - Dict scanning: ``scan(dict)`` / ``redact_secrets(dict)`` — optimised for
      structured tool responses with pre-filtering and chunked processing.
    - Text scanning: ``scan_text(str)`` / ``redact(Any)`` — context-aware
      scanning with entropy detection, code-block skipping, and suppression
      annotations.  ``redact`` also handles dicts, lists, and tuples
      recursively.
    """

    # Performance tuning
    CHUNK_SIZE = 10_000
    CHUNK_OVERLAP = 200
    MAX_STRING_LENGTH = 1_000_000

    # (SecretType, regex_string, confidence)
    _PATTERN_DEFS: list[tuple[SecretType, str, float]] = [
        # AI/ML ----------------------------------------------------------------
        (SecretType.OPENAI_PROJECT_KEY, r"sk-proj-[a-zA-Z0-9\-_]{20,}", 1.0),
        (SecretType.OPENAI_API_KEY, r"sk-[a-zA-Z0-9]{20,}", 1.0),
        (SecretType.ANTHROPIC_API_KEY, r"sk-ant-[a-zA-Z0-9\-_]{70,}", 1.0),
        # Version Control ------------------------------------------------------
        (SecretType.GITHUB_FINE_GRAINED_PAT, r"github_pat_[a-zA-Z0-9_]{82}", 1.0),
        (SecretType.GITHUB_PAT, r"ghp_[a-zA-Z0-9]{20,}", 1.0),
        (SecretType.GITHUB_OAUTH, r"gho_[a-zA-Z0-9]{20,}", 1.0),
        (SecretType.GITHUB_APP_TOKEN, r"ghs_[a-zA-Z0-9]{36}", 1.0),
        (SecretType.GITLAB_PAT, r"glpat-[a-zA-Z0-9\-_]{20,}", 1.0),
        # Cloud — AWS ----------------------------------------------------------
        (SecretType.AWS_ACCESS_KEY, r"AKIA[0-9A-Z]{16}", 1.0),
        (
            SecretType.AWS_SECRET_KEY,
            r"(?i)aws.{0,20}secret.{0,20}['\"][a-zA-Z0-9/+=]{40}['\"]",
            0.9,
        ),
        # Cloud — Google -------------------------------------------------------
        (SecretType.GOOGLE_API_KEY, r"AIza[0-9A-Za-z\-_]{35}", 0.95),
        (SecretType.GOOGLE_OAUTH, r"ya29\.[0-9A-Za-z\-_]+", 0.95),
        # Cloud — Azure --------------------------------------------------------
        (SecretType.AZURE_STORAGE_KEY, r"AccountKey=[A-Za-z0-9+/]{86,90}={0,2}", 0.95),
        (
            SecretType.AZURE_CONNECTION_STRING,
            r"(?i)(?:DefaultEndpointsProtocol|BlobEndpoint|QueueEndpoint|TableEndpoint|FileEndpoint)=[^;\s]+(?:;|$)",
            0.9,
        ),
        # Cloud — Other --------------------------------------------------------
        (
            SecretType.HEROKU_API_KEY,
            r"(?i)heroku[_\-\s]*(?:api[_\-\s]*)?(?:key|token)[_\-\s]*[:=\s]+[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
            0.90,
        ),
        (SecretType.DIGITALOCEAN_TOKEN, r"dop_v1_[a-f0-9]{64}", 1.0),
        # Communication --------------------------------------------------------
        (SecretType.SLACK_TOKEN, r"xox[baprs]-[0-9a-zA-Z\-]{10,48}", 1.0),
        (
            SecretType.SLACK_WEBHOOK,
            r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]{8,}/B[a-zA-Z0-9_]{8,}/[a-zA-Z0-9_]{24,}",
            1.0,
        ),
        (SecretType.TWILIO_API_KEY, r"SK[0-9a-fA-F]{32}", 0.85),
        (SecretType.SENDGRID_API_KEY, r"SG\.[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{40,}", 1.0),
        (SecretType.MAILGUN_API_KEY, r"key-[0-9a-zA-Z]{32}", 0.95),
        # Payment --------------------------------------------------------------
        (SecretType.STRIPE_KEY, r"(?:sk|pk|rk)_(?:live|test)_[0-9a-zA-Z]{24,}", 1.0),
        # Cryptographic --------------------------------------------------------
        (
            SecretType.PRIVATE_KEY,
            r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
            r"(?:[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----)?",
            1.0,
        ),
        (
            SecretType.JWT_TOKEN,
            r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+",
            0.9,
        ),
        # Database -------------------------------------------------------------
        (
            SecretType.DATABASE_URL,
            r"(?i)(?:postgres|mysql|mongodb|redis|mariadb|mssql)://[^\s@:]+:[^\s@]+@[^\s]+",
            0.95,
        ),
        # Package Managers -----------------------------------------------------
        (SecretType.NPM_TOKEN, r"npm_[a-zA-Z0-9]{32,}", 1.0),
        (SecretType.PYPI_TOKEN, r"pypi-AgEIcHlwaS5vcmc[a-zA-Z0-9_-]{70,}", 1.0),
        # Generic --------------------------------------------------------------
        (
            SecretType.GENERIC_PASSWORD,
            r"(?i)(?:password|passwd|pwd)\s*[:=]\s*['\"]?[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};:,.<>?]{8,}['\"]?",
            0.7,
        ),
        (
            SecretType.GENERIC_API_KEY,
            r"(?i)(?:api[_\-]?key|apikey)\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}['\"]?",
            0.8,
        ),
        (
            SecretType.GENERIC_SECRET,
            r"(?i)(?:secret|token)\s*[:=]\s*['\"]?[a-zA-Z0-9]{16,}['\"]?",
            0.7,
        ),
        # Base64 (low confidence — informational only) -------------------------
        (
            SecretType.BASE64_SECRET,
            r"(?:[A-Za-z0-9+/]{4}){16,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?",
            0.5,
        ),
    ]

    FALSE_POSITIVE_PATTERNS = [
        r"127\.0\.0\.1",
        r"0\.0\.0\.0",
        r"test@test\.com",
        r"(?i)dummy",
        r"(?i)sample",
        r"(?i)placeholder",
    ]

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        redaction_placeholder: str = "[REDACTED]",
        skip_code_blocks: bool = True,
        skip_test_fixtures: bool = True,
        enable_suppressions: bool = True,
    ):
        self.config = config or {}
        self.redaction_placeholder = redaction_placeholder
        self.skip_code_blocks = skip_code_blocks
        self.skip_test_fixtures = skip_test_fixtures
        self.enable_suppressions = enable_suppressions
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        self._compiled_patterns: list[tuple[SecretType, re.Pattern, float]] = [
            (secret_type, re.compile(pattern), confidence)
            for secret_type, pattern, confidence in self._PATTERN_DEFS
        ]
        self._compiled_fp_patterns = [
            re.compile(p) for p in self.FALSE_POSITIVE_PATTERNS
        ]
        self._high_entropy_pattern = re.compile(r"[A-Za-z0-9+/]{60,}={0,2}")

    # ------------------------------------------------------------------
    # Dict API
    # ------------------------------------------------------------------

    def scan(self, data: dict[str, Any]) -> list[SecretFinding]:
        """Scan a dictionary for exposed secrets.

        Optimised for structured tool responses: flattens the dict, pre-filters
        short / unlikely strings, then pattern-matches candidates.
        """
        findings: list[SecretFinding] = []
        candidates = [
            (loc, val)
            for loc, val in self._flatten_dict_generator(data, min_str_len=16)
            if self._could_contain_secret(val)
        ]
        for location, value in candidates:
            findings.extend(self._scan_value(value, location))
        return findings

    def redact_secrets(
        self,
        data: dict[str, Any],
        findings: list[SecretFinding] | None = None,
    ) -> dict[str, Any]:
        """Return a deep copy of *data* with high-confidence secrets replaced."""
        if findings is None:
            findings = self.scan(data)
        if not findings:
            return data
        redacted = copy.deepcopy(data)
        for finding in findings:
            if finding.should_redact:
                redacted = self._redact_location(
                    redacted, finding.location, finding.full_match
                )
        return redacted

    # ------------------------------------------------------------------
    # Text / polymorphic API
    # ------------------------------------------------------------------

    def scan_text(
        self, text: str, file_path: str | None = None
    ) -> list[SecretFinding]:
        """Scan raw text for secrets with context awareness.

        Supports code-block skipping, suppression annotations, and Shannon
        entropy detection for high-entropy strings.
        """
        if self.skip_test_fixtures and file_path and self._is_test_fixture(file_path):
            return []

        excluded_ranges = self._get_excluded_ranges(text)
        findings: list[SecretFinding] = []

        for secret_type, pattern, confidence in self._compiled_patterns:
            for match in pattern.finditer(text):
                matched_text = match.group(0)
                start_pos = match.start()
                end_pos = match.end()

                if self._is_in_excluded_range(start_pos, end_pos, excluded_ranges):
                    continue
                if self._is_false_positive(matched_text):
                    continue

                line_number = text[:start_pos].count("\n") + 1
                findings.append(
                    SecretFinding(
                        secret_type=secret_type,
                        location="",
                        matched_value=self._truncate_secret(matched_text),
                        confidence=confidence,
                        should_redact=confidence >= 0.7,
                        full_match=matched_text,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        line_number=line_number,
                    )
                )

        findings.extend(self._scan_high_entropy(text, excluded_ranges))
        return sorted(findings, key=lambda f: f.start_pos or 0)

    def redact(
        self, data: Any, file_path: str | None = None
    ) -> tuple[Any, list[SecretFinding]]:
        """Recursively redact secrets from any data structure.

        Returns ``(redacted_data, findings)``.  Handles str, dict, list, and
        tuple; other types pass through unchanged.
        """
        all_findings: list[SecretFinding] = []

        def _recursive(obj: Any) -> Any:
            if isinstance(obj, str):
                findings = self.scan_text(obj, file_path=file_path)
                all_findings.extend(findings)
                if not findings:
                    return obj
                result = obj
                for finding in reversed(findings):
                    result = (
                        result[: finding.start_pos]
                        + self.redaction_placeholder
                        + result[finding.end_pos :]
                    )
                return result
            if isinstance(obj, dict):
                return {k: _recursive(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_recursive(item) for item in obj]
            if isinstance(obj, tuple):
                return tuple(_recursive(item) for item in obj)
            return obj

        redacted = _recursive(data)
        return redacted, all_findings

    # ------------------------------------------------------------------
    # Core pattern matching
    # ------------------------------------------------------------------

    def _scan_value(self, value: str, location: str) -> list[SecretFinding]:
        if len(value) > self.MAX_STRING_LENGTH:
            logger.warning(
                "String at %s exceeds max length (%d > %d), truncating",
                location,
                len(value),
                self.MAX_STRING_LENGTH,
            )
            value = value[: self.MAX_STRING_LENGTH]
        if len(value) > self.CHUNK_SIZE:
            return self._scan_value_chunked(value, location)
        return self._scan_value_direct(value, location)

    def _scan_value_direct(self, value: str, location: str) -> list[SecretFinding]:
        findings: list[SecretFinding] = []
        for secret_type, pattern, confidence in self._compiled_patterns:
            for match in pattern.finditer(value):
                matched_text = match.group(0)
                if self._is_false_positive(matched_text):
                    continue
                findings.append(
                    SecretFinding(
                        secret_type=secret_type,
                        location=location,
                        matched_value=self._truncate_secret(matched_text),
                        confidence=confidence,
                        should_redact=confidence >= 0.7,
                        full_match=matched_text,
                        start_pos=match.start(),
                        end_pos=match.end(),
                    )
                )
        return findings

    def _scan_value_chunked(self, value: str, location: str) -> list[SecretFinding]:
        findings: list[SecretFinding] = []
        seen: set[str] = set()
        for i in range(0, len(value), self.CHUNK_SIZE):
            chunk_start = max(0, i - self.CHUNK_OVERLAP)
            chunk_end = min(len(value), i + self.CHUNK_SIZE + self.CHUNK_OVERLAP)
            for finding in self._scan_value_direct(value[chunk_start:chunk_end], location):
                if finding.full_match not in seen:
                    seen.add(finding.full_match)
                    findings.append(finding)
        return findings

    # ------------------------------------------------------------------
    # Pre-filtering (dict mode performance)
    # ------------------------------------------------------------------

    def _could_contain_secret(self, value: str) -> bool:
        """Ultra-fast pre-filter to skip strings unlikely to contain secrets."""
        if len(value) < 3:
            return False

        p3 = value[:3]
        if p3 in (
            "sk-", "ghp", "gho", "ghs", "glp", "xox", "sk_", "rk_", "pk_", "key",
            "npm", "SG.", "dop",
        ):
            return True

        p4 = value[:4]
        if p4 in ("AKIA", "AIza", "ya29", "key-", "pypi", "eyJ"):
            return True

        if value.startswith((
            "-----BEGIN",
            "postgres://", "mysql://", "mongodb://", "redis://",
            "mariadb://", "mssql://",
            "https://hooks.slack.com",
            "github_pat_",
        )):
            return True

        lower = value.lower()
        if any(
            kw in lower
            for kw in ("password", "secret", "token", "api_key", "accountkey=", "heroku")
        ):
            return True

        if len(value) >= 40:
            alnum = sum(c.isalnum() for c in value[:40])
            if alnum > 32:
                return True

        return False

    def _is_false_positive(self, value: str) -> bool:
        return any(p.search(value) for p in self._compiled_fp_patterns)

    @staticmethod
    def _truncate_secret(secret: str, show_chars: int = 10) -> str:
        if len(secret) <= show_chars:
            return secret[:3] + "..."
        return secret[:show_chars] + "..."

    # ------------------------------------------------------------------
    # Entropy detection (text mode)
    # ------------------------------------------------------------------

    def _scan_high_entropy(
        self,
        text: str,
        excluded_ranges: list[tuple[int, int]],
    ) -> list[SecretFinding]:
        findings: list[SecretFinding] = []
        context_keywords = (
            "secret", "password", "passwd", "pwd", "key", "token",
            "credential", "auth", "api", "private", "bearer",
        )

        for match in self._high_entropy_pattern.finditer(text):
            value = match.group(0)
            start_pos, end_pos = match.start(), match.end()

            if self._is_in_excluded_range(start_pos, end_pos, excluded_ranges):
                continue
            if len(value) < 60 or self._is_likely_non_secret(value):
                continue
            if self._calculate_entropy(value) <= 4.8:
                continue

            ctx_start = max(0, start_pos - 50)
            ctx_end = min(len(text), end_pos + 50)
            context = text[ctx_start:ctx_end].lower()

            if not any(kw in context for kw in context_keywords):
                continue

            findings.append(
                SecretFinding(
                    secret_type=SecretType.HIGH_ENTROPY_SECRET,
                    location="",
                    matched_value=self._truncate_secret(value),
                    confidence=0.8,
                    should_redact=True,
                    full_match=value,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    line_number=text[:start_pos].count("\n") + 1,
                )
            )
        return findings

    @staticmethod
    def _calculate_entropy(data: str) -> float:
        if not data:
            return 0.0
        freq: dict[str, int] = {}
        for ch in data:
            freq[ch] = freq.get(ch, 0) + 1
        length = len(data)
        return -sum(
            (c / length) * math.log2(c / length) for c in freq.values() if c > 0
        )

    @staticmethod
    def _is_likely_non_secret(value: str) -> bool:
        """Return True if *value* looks like a hash, UUID, or repeated pattern."""
        if re.match(
            r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$",
            value,
        ):
            return True
        if re.match(r"^[0-9a-fA-F]{32}$", value):
            return True
        if re.match(r"^[0-9a-fA-F]{40}$", value):
            return True
        if re.match(r"^[0-9a-fA-F]{64}$", value):
            return True
        if len(set(value)) < len(value) * 0.3:
            return True
        return False

    # ------------------------------------------------------------------
    # Context awareness (text mode)
    # ------------------------------------------------------------------

    def _get_excluded_ranges(self, text: str) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        if self.skip_code_blocks:
            ranges.extend(self._find_code_blocks(text))
        if self.enable_suppressions:
            ranges.extend(self._find_suppressed_regions(text))
        return ranges

    @staticmethod
    def _find_code_blocks(text: str) -> list[tuple[int, int]]:
        return [
            (m.start(), m.end())
            for m in re.finditer(r"```[a-zA-Z]*\n.*?\n```", text, re.DOTALL)
        ]

    @staticmethod
    def _find_suppressed_regions(text: str) -> list[tuple[int, int]]:
        ranges: list[tuple[int, int]] = []
        block_start: int | None = None
        pos = 0
        for line in text.split("\n"):
            line_start, line_end = pos, pos + len(line)
            if "sark-secret-scanner: ignore-start" in line:
                block_start = line_start
            elif "sark-secret-scanner: ignore-end" in line and block_start is not None:
                ranges.append((block_start, line_end))
                block_start = None
            elif block_start is None and (
                "sark-secret-scanner: ignore" in line or "nosecret" in line
            ):
                ranges.append((line_start, line_end))
            pos = line_end + 1
        return ranges

    @staticmethod
    def _is_in_excluded_range(
        start: int, end: int, excluded: list[tuple[int, int]]
    ) -> bool:
        return any(not (end <= es or start >= ee) for es, ee in excluded)

    @staticmethod
    def _is_test_fixture(file_path: str) -> bool:
        normalized = file_path.lower().replace("\\", "/")
        indicators = (
            "/test/", "/tests/", "/fixtures/", "/mocks/", "/stubs/",
            "test_", "_test.", "fixture", "mock_", ".fixture.",
            "conftest.py", "/examples/", "/samples/",
        )
        return any(ind in normalized for ind in indicators)

    # ------------------------------------------------------------------
    # Dict helpers
    # ------------------------------------------------------------------

    def _flatten_dict_generator(
        self,
        data: Any,
        prefix: str = "",
        depth: int = 0,
        min_str_len: int = 20,
    ):
        MAX_DEPTH = 50
        if depth > MAX_DEPTH:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                if isinstance(value, str):
                    if len(value) >= min_str_len:
                        yield (full_key, value)
                elif isinstance(value, (dict, list)):
                    yield from self._flatten_dict_generator(
                        value, full_key, depth + 1, min_str_len
                    )
        elif isinstance(data, list):
            for i, item in enumerate(data):
                idx_key = f"{prefix}[{i}]"
                if isinstance(item, str):
                    if len(item) >= min_str_len:
                        yield (idx_key, item)
                elif isinstance(item, (dict, list)):
                    yield from self._flatten_dict_generator(
                        item, idx_key, depth + 1, min_str_len
                    )
        elif isinstance(data, str) and len(data) >= min_str_len:
            yield (prefix, data)

    def _redact_location(
        self, data: dict[str, Any], location: str, secret: str
    ) -> dict[str, Any]:
        keys = self._parse_location(location)
        current: Any = data
        for key in keys[:-1]:
            if isinstance(current, dict):
                current = current.get(key, {})
            elif isinstance(current, list) and isinstance(key, int):
                current = current[key] if key < len(current) else {}
        final_key = keys[-1]
        if isinstance(current, dict) and final_key in current:
            if isinstance(current[final_key], str):
                current[final_key] = current[final_key].replace(
                    secret, self.redaction_placeholder
                )
        return data

    @staticmethod
    def _parse_location(location: str) -> list[Any]:
        keys: list[Any] = []
        for part in location.split("."):
            if "[" in part:
                key, rest = part.split("[", 1)
                if key:
                    keys.append(key)
                idx_str = rest.rstrip("]")
                try:
                    keys.append(int(idx_str))
                except ValueError:
                    keys.append(idx_str)
            else:
                keys.append(part)
        return keys
