"""Prompt injection detection system.

Detects malicious attempts to manipulate AI tool parameters through:
- Pattern-based detection (20+ known injection techniques)
- Entropy analysis for encoded/obfuscated payloads
- Risk scoring system (0-100)
"""

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import math
import re
from typing import Any

import structlog

logger = structlog.get_logger()


class Severity(str, Enum):
    """Finding severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class InjectionFinding:
    """Single injection detection finding."""

    pattern_name: str
    severity: Severity
    matched_text: str
    location: str
    description: str


@dataclass
class InjectionDetectionResult:
    """Complete injection detection result."""

    findings: list[InjectionFinding] = field(default_factory=list)
    risk_score: int = 0
    detected: bool = False
    total_patterns_checked: int = 0
    high_entropy_strings: list[tuple[str, float]] = field(default_factory=list)

    @property
    def has_high_severity(self) -> bool:
        """Check if any high severity findings exist."""
        return any(f.severity == Severity.HIGH for f in self.findings)

    @property
    def has_medium_severity(self) -> bool:
        """Check if any medium severity findings exist."""
        return any(f.severity == Severity.MEDIUM for f in self.findings)


class PromptInjectionDetector:
    """Detects prompt injection attempts in tool parameters."""

    def __init__(self, config: "InjectionDetectionConfig | None" = None):
        """
        Initialize detector with compiled regex patterns.

        Args:
            config: Optional configuration. If not provided, loads from environment.
        """
        if config is None:
            from sark.security.config import get_injection_config

            config = get_injection_config()

        self.config = config
        self._patterns = self._compile_patterns()

        # Set severity weights from config
        self.SEVERITY_WEIGHTS = {
            Severity.HIGH: config.severity_weight_high,
            Severity.MEDIUM: config.severity_weight_medium,
            Severity.LOW: config.severity_weight_low,
        }

        # Cache normalizer for performance
        self._normalizer = None

    @staticmethod
    @lru_cache(maxsize=1)
    def _compile_patterns() -> list[tuple[str, Severity, str, re.Pattern]]:
        """
        Compile regex patterns for injection detection.

        Returns:
            List of tuples: (pattern_name, severity, description, compiled_regex)
        """
        patterns = [
            # Instruction override patterns (HIGH severity)
            (
                "ignore_instructions",
                Severity.HIGH,
                "Attempt to ignore previous instructions",
                re.compile(
                    r"ignore\s+(all\s+)?((previous|prior|above|system)\s+)?instructions?",
                    re.IGNORECASE,
                ),
            ),
            (
                "disregard_instructions",
                Severity.HIGH,
                "Attempt to disregard instructions",
                re.compile(
                    r"disregard\s+(all\s+)?(previous|prior|above|system)\s+(instructions?|rules?|context)",
                    re.IGNORECASE,
                ),
            ),
            (
                "forget_instructions",
                Severity.HIGH,
                "Attempt to forget previous instructions",
                re.compile(
                    r"forget\s+(all\s+)?(previous|prior|above|system)\s+(instructions?|rules?|context)",
                    re.IGNORECASE,
                ),
            ),
            # Role manipulation patterns (HIGH severity)
            (
                "role_override",
                Severity.HIGH,
                "Attempt to override AI role",
                re.compile(
                    r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|behave\s+like)\s+(a\s+)?(assistant|developer|admin|root|system)",
                    re.IGNORECASE,
                ),
            ),
            (
                "new_instructions",
                Severity.HIGH,
                "Attempt to inject new instructions",
                re.compile(
                    r"(new\s+instructions?|new\s+role|new\s+task|new\s+system\s+prompt)",
                    re.IGNORECASE,
                ),
            ),
            (
                "system_message",
                Severity.HIGH,
                "Attempt to inject system message",
                re.compile(
                    r"<\s*system\s*>|system\s*:|system\s+message\s*:",
                    re.IGNORECASE,
                ),
            ),
            # Data exfiltration patterns (HIGH severity)
            (
                "url_exfiltration",
                Severity.HIGH,
                "Attempt to exfiltrate data via URL",
                re.compile(
                    r"(send|post|transmit|forward|export)\s+.*?\s+to\s+https?://",
                    re.IGNORECASE,
                ),
            ),
            (
                "webhook_injection",
                Severity.HIGH,
                "Suspicious webhook URL injection",
                re.compile(
                    r"webhook\s*=\s*['\"]https?://|callback_url\s*=\s*['\"]https?://",
                    re.IGNORECASE,
                ),
            ),
            # Code execution patterns (HIGH severity)
            (
                "eval_exec",
                Severity.HIGH,
                "Code execution attempt (eval/exec)",
                re.compile(
                    r"\b(eval|exec|__import__|compile)\s*\(",
                    re.IGNORECASE,
                ),
            ),
            (
                "subprocess_shell",
                Severity.HIGH,
                "Shell command execution attempt",
                re.compile(
                    r"\b(subprocess|os\.system|popen|shell=True|cmd\s*/c)",
                    re.IGNORECASE,
                ),
            ),
            (
                "code_injection",
                Severity.HIGH,
                "Potential code injection",
                re.compile(
                    r"`;|&&\s*|;\s*rm\s+-rf|;\s*cat\s+/etc/passwd|drop\s+table",
                    re.IGNORECASE,
                ),
            ),
            # Encoding/obfuscation patterns (MEDIUM severity)
            (
                "base64_decode",
                Severity.MEDIUM,
                "Base64 decode attempt",
                re.compile(
                    r"(base64\.b64decode|atob|decode\(.*base64)",
                    re.IGNORECASE,
                ),
            ),
            (
                "hex_decode",
                Severity.MEDIUM,
                "Hex decode attempt",
                re.compile(
                    r"(bytes\.fromhex|hex\.decode|\\x[0-9a-f]{2}.*\\x[0-9a-f]{2})",
                    re.IGNORECASE,
                ),
            ),
            (
                "unicode_escape",
                Severity.MEDIUM,
                "Unicode escape sequence",
                re.compile(
                    r"\\u[0-9a-f]{4}.*\\u[0-9a-f]{4}|\\U[0-9a-f]{8}",
                    re.IGNORECASE,
                ),
            ),
            # Prompt delimiter patterns (MEDIUM severity)
            (
                "delimiter_injection",
                Severity.MEDIUM,
                "Prompt delimiter injection",
                re.compile(
                    r"(---\s*END\s+SYSTEM|===\s*USER\s+INPUT|<<<\s*INSTRUCTION|>>>)",
                    re.IGNORECASE,
                ),
            ),
            (
                "xml_tag_injection",
                Severity.MEDIUM,
                "XML/HTML tag injection",
                re.compile(
                    r"<\s*(user|assistant|human|ai|bot)\s*>",
                    re.IGNORECASE,
                ),
            ),
            # Context manipulation (MEDIUM severity)
            (
                "context_override",
                Severity.MEDIUM,
                "Attempt to override context",
                re.compile(
                    r"(override|replace|change)\s+(the\s+)?(context|system\s+prompt|guidelines)",
                    re.IGNORECASE,
                ),
            ),
            (
                "parameter_injection",
                Severity.MEDIUM,
                "Parameter injection attempt",
                re.compile(
                    r"temperature\s*[:=]\s*[2-9]|max_tokens\s*[:=]\s*[0-9]{5,}",
                    re.IGNORECASE,
                ),
            ),
            # Jailbreak patterns (MEDIUM severity)
            (
                "jailbreak_prefix",
                Severity.MEDIUM,
                "Jailbreak attempt prefix",
                re.compile(
                    r"(DAN|developer\s+mode|unrestricted\s+mode|god\s+mode)",
                    re.IGNORECASE,
                ),
            ),
            # Information disclosure (LOW severity)
            (
                "reveal_system",
                Severity.LOW,
                "Attempt to reveal system prompt",
                re.compile(
                    r"(show|reveal|display|print|output)\s+(your\s+)?(system\s+prompt|instructions?|rules?)",
                    re.IGNORECASE,
                ),
            ),
            (
                "repeat_prompt",
                Severity.LOW,
                "Attempt to make AI repeat prompt",
                re.compile(
                    r"repeat\s+(your\s+)?(instructions?|prompt|system\s+message)",
                    re.IGNORECASE,
                ),
            ),
            # SQL injection patterns (MEDIUM severity)
            (
                "sql_injection",
                Severity.MEDIUM,
                "SQL injection attempt",
                re.compile(
                    r"('\s*OR\s+'1'\s*=\s*'1|;\s*DROP\s+TABLE|UNION\s+SELECT|--\s*$)",
                    re.IGNORECASE,
                ),
            ),
            # Path traversal (MEDIUM severity)
            (
                "path_traversal",
                Severity.MEDIUM,
                "Path traversal attempt",
                re.compile(
                    r"\.\./\.\./|\.\.\\\.\.\\|/etc/passwd|/proc/self",
                    re.IGNORECASE,
                ),
            ),
            # Credential extraction (HIGH severity)
            (
                "credential_request",
                Severity.HIGH,
                "Request for credentials or secrets",
                re.compile(
                    r"(give|show|tell)\s+me\s+(your\s+|the\s+)?(api\s+key|password|secret|token|credentials?)",
                    re.IGNORECASE,
                ),
            ),
        ]

        return patterns

    def detect(
        self, parameters: dict[str, Any], context: dict[str, Any] | None = None
    ) -> InjectionDetectionResult:
        """
        Detect prompt injection attempts in parameters.

        Args:
            parameters: Dictionary of tool parameters to check
            context: Optional additional context to check

        Returns:
            InjectionDetectionResult with findings and risk score
        """
        result = InjectionDetectionResult()
        result.total_patterns_checked = len(self._patterns)

        # Flatten nested parameters
        flattened_params = self._flatten_dict(parameters)
        if context:
            flattened_context = self._flatten_dict(context, prefix="context")
            flattened_params.update(flattened_context)

        # Get cached normalizer
        if self._normalizer is None:
            from sark.security.text_normalizer import get_normalizer

            self._normalizer = get_normalizer()

        # Run pattern detection
        for location, value in flattened_params.items():
            if not isinstance(value, str):
                continue

            # Detect obfuscation techniques
            obfuscation_info = self._normalizer.detect_obfuscation(value)

            # Normalize text for better detection
            normalized_value = self._normalizer.normalize(value, aggressive=False)

            # Check against all patterns on BOTH original and normalized text
            for pattern_name, severity, description, regex in self._patterns:
                # Check original text first
                match = regex.search(value)
                if match:
                    finding = InjectionFinding(
                        pattern_name=pattern_name,
                        severity=severity,
                        matched_text=match.group(0)[:100],  # Truncate to 100 chars
                        location=location,
                        description=description,
                    )
                    result.findings.append(finding)
                    logger.warning(
                        "injection_pattern_detected",
                        pattern=pattern_name,
                        severity=severity.value,
                        location=location,
                    )
                # If not found in original, check normalized text
                elif normalized_value != value:
                    match_normalized = regex.search(normalized_value)
                    if match_normalized:
                        # Add additional note about obfuscation
                        obf_note = " (detected after normalization - "
                        if obfuscation_info.get("has_homoglyphs"):
                            obf_note += "homoglyphs, "
                        if obfuscation_info.get("has_zero_width"):
                            obf_note += "zero-width chars, "
                        if obfuscation_info.get("has_fullwidth"):
                            obf_note += "fullwidth chars, "
                        if obfuscation_info.get("has_combining_marks"):
                            obf_note += "combining marks, "
                        obf_note = obf_note.rstrip(", ") + ")"

                        finding = InjectionFinding(
                            pattern_name=pattern_name,
                            severity=severity,
                            matched_text=normalized_value[:100],
                            location=location,
                            description=description + obf_note,
                        )
                        result.findings.append(finding)
                        logger.warning(
                            "injection_pattern_detected_normalized",
                            pattern=pattern_name,
                            severity=severity.value,
                            location=location,
                            obfuscation=obfuscation_info,
                        )

            # Check entropy for potential encoded payloads
            if len(value) >= self.config.entropy_min_length:
                entropy = self._calculate_entropy(value)
                if entropy > self.config.entropy_threshold:
                    result.high_entropy_strings.append((location, entropy))
                    finding = InjectionFinding(
                        pattern_name="high_entropy",
                        severity=Severity.MEDIUM,
                        matched_text=value[:100],
                        location=location,
                        description=f"High entropy string detected (entropy={entropy:.2f})",
                    )
                    result.findings.append(finding)
                    logger.warning(
                        "high_entropy_detected",
                        location=location,
                        entropy=entropy,
                        length=len(value),
                    )

        # Calculate risk score
        result.risk_score = self._calculate_risk_score(result.findings)
        result.detected = len(result.findings) > 0

        if result.detected:
            logger.info(
                "injection_detection_complete",
                findings_count=len(result.findings),
                risk_score=result.risk_score,
                high_severity=result.has_high_severity,
            )

        return result

    def _flatten_dict_generator(self, data: Any, prefix: str = "", depth: int = 0):
        """
        Generator that yields (location, value) pairs from nested data structures.
        More efficient than building intermediate dictionaries.

        Args:
            data: Data to flatten (dict, list, or scalar)
            prefix: Current key prefix
            depth: Current recursion depth (prevents stack overflow)

        Yields:
            Tuples of (location, value)
        """
        # Prevent infinite recursion using configured max depth
        max_depth = getattr(self.config, "max_parameter_depth", 10)
        if depth > max_depth:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                yield from self._flatten_dict_generator(value, full_key, depth + 1)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                full_key = f"{prefix}[{i}]"
                yield from self._flatten_dict_generator(item, full_key, depth + 1)

        else:
            # Scalar value - yield it
            if prefix:  # Only yield if we have a key
                yield (prefix, data)

    def _flatten_dict(
        self, d: dict[str, Any], parent_key: str = "", prefix: str = ""
    ) -> dict[str, Any]:
        """
        Flatten nested dictionary for comprehensive parameter checking.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key for nested items
            prefix: Prefix for all keys

        Returns:
            Flattened dictionary with dot-notation keys
        """
        # Use generator and convert to dict
        combined_prefix = (
            f"{prefix}.{parent_key}" if prefix and parent_key else (prefix or parent_key)
        )
        return dict(self._flatten_dict_generator(d, combined_prefix))

    @staticmethod
    def _calculate_entropy(text: str) -> float:
        """
        Calculate Shannon entropy of a string.

        High entropy (>4.5) suggests encoded/obfuscated content.

        Args:
            text: String to analyze

        Returns:
            Shannon entropy value
        """
        if not text:
            return 0.0

        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        length = len(text)
        entropy = 0.0
        for count in char_counts.values():
            probability = count / length
            entropy -= probability * math.log2(probability)

        return entropy

    def _calculate_risk_score(self, findings: list[InjectionFinding]) -> int:
        """
        Calculate risk score (0-100) based on findings.

        Scoring:
        - High severity: 30 points each
        - Medium severity: 15 points each
        - Low severity: 5 points each
        - Maximum: 100

        Args:
            findings: List of injection findings

        Returns:
            Risk score capped at 100
        """
        score = 0
        for finding in findings:
            score += self.SEVERITY_WEIGHTS.get(finding.severity, 0)

        # Cap at 100
        return min(score, 100)
