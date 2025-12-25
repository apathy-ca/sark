"""
Prompt Injection Detection System

Detects potential prompt injection attacks using:
- Pattern-based detection (20+ known injection patterns)
- Entropy analysis (detect encoded payloads)
- Risk scoring (0-100 scale)
"""

import re
import math
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    """Severity levels for injection findings"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class InjectionFinding:
    """Represents a single injection detection finding"""
    severity: Severity
    pattern_name: str
    matched_text: str
    location: str
    recommendation: str


@dataclass
class InjectionDetectionResult:
    """Result of injection detection scan"""
    detected: bool
    risk_score: int
    findings: List[InjectionFinding]

    def __bool__(self):
        return self.detected


class PromptInjectionDetector:
    """Detects prompt injection patterns in tool parameters"""

    # High-severity patterns - instruction manipulation
    INSTRUCTION_PATTERNS = [
        (r"ignore\s+(?:all\s+)?(?:previous|above|prior)\s+instructions?", "Ignore instructions", Severity.HIGH),
        (r"ignore\s+(?:the\s+)?instructions?", "Ignore instructions (short form)", Severity.HIGH),
        (r"disregard\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions?|rules?|prompts?)", "Disregard instructions", Severity.HIGH),
        (r"disregard\s+(?:the\s+)?(?:instructions?|rules?|prompts?)", "Disregard instructions (short form)", Severity.HIGH),
        (r"forget\s+(?:all\s+)?(?:previous|everything|above)\s+(?:instructions?|context)?", "Forget instructions", Severity.HIGH),
        (r"forget\s+(?:everything|all)", "Forget everything", Severity.HIGH),
        (r"override\s+(?:all\s+)?(?:previous|system)\s+(?:instructions?|rules?)", "Override instructions", Severity.HIGH),
    ]

    # High-severity patterns - role manipulation
    ROLE_PATTERNS = [
        (r"you\s+are\s+now\s+(?:a|an)\s+\w+", "Role change", Severity.HIGH),
        (r"you\s+are\s+(?:a|an)\s+(?:helpful\s+)?(?:hacker|attacker|admin|root|system)", "Suspicious role assignment", Severity.HIGH),
        (r"act\s+as\s+(?:a|an)\s+\w+", "Act as another role", Severity.HIGH),
        (r"pretend\s+(?:you|to)\s+(?:are|be)\s+(?:a|an)?\s*\w+", "Pretend to be", Severity.HIGH),
        (r"roleplay\s+as\s+(?:a|an)?\s*\w+", "Roleplay as", Severity.HIGH),
    ]

    # Critical patterns - data exfiltration
    EXFILTRATION_PATTERNS = [
        (r"(?:send|post|export|transmit)\s+.{0,50}\s+to\s+https?://", "Data exfiltration attempt", Severity.CRITICAL),
        (r"curl\s+.*?https?://", "Command injection via curl", Severity.CRITICAL),
        (r"wget\s+.*?https?://", "Command injection via wget", Severity.CRITICAL),
    ]

    # High-severity patterns - system prompt leakage
    SYSTEM_PATTERNS = [
        (r"(?:show|reveal|display|print)\s+(?:me\s+)?(?:your\s+)?(?:system|initial|original)\s+(?:prompt|instructions?)", "System prompt extraction", Severity.HIGH),
        (r"what\s+(?:are|were)\s+your\s+(?:original|initial|system)\s+instructions?", "System prompt query", Severity.HIGH),
        (r"what\s+(?:is|was)\s+your\s+(?:system|initial|original)\s+prompt", "System prompt query (alt)", Severity.HIGH),
        (r"repeat\s+(?:your|the)\s+(?:system|initial|original)\s+prompt", "System prompt repeat", Severity.HIGH),
        (r"tell\s+me\s+your\s+(?:system|initial|original)\s+(?:prompt|instructions?)", "System prompt tell", Severity.HIGH),
    ]

    # Medium-severity patterns - encoding/obfuscation
    ENCODING_PATTERNS = [
        (r"base64\s*\(", "Base64 encoding", Severity.MEDIUM),
        (r"eval\s*\(", "Eval execution", Severity.CRITICAL),
        (r"exec\s*\(", "Exec execution", Severity.CRITICAL),
        (r"\\x[0-9a-fA-F]{2}", "Hex encoding", Severity.MEDIUM),
        (r"\\u[0-9a-fA-F]{4}", "Unicode escape", Severity.MEDIUM),
    ]

    # Medium-severity patterns - prompt injection markers
    INJECTION_MARKERS = [
        (r"<\s*system\s*>", "System tag", Severity.HIGH),
        (r"system\s*:\s*", "System prefix", Severity.HIGH),
        (r"<\s*\|endoftext\|\s*>", "End of text marker", Severity.MEDIUM),
        (r"###\s*instruction", "Instruction delimiter", Severity.MEDIUM),
    ]

    # Low-severity patterns - suspicious keywords
    SUSPICIOUS_PATTERNS = [
        (r"jailbreak", "Jailbreak keyword", Severity.MEDIUM),
        (r"bypass\s+(security|filter|protection)", "Bypass attempt", Severity.MEDIUM),
        (r"developer\s+mode", "Developer mode", Severity.LOW),
        (r"admin\s+mode", "Admin mode", Severity.LOW),
    ]

    # Entropy threshold for detecting encoded payloads
    ENTROPY_THRESHOLD = 4.5
    ENTROPY_MIN_LENGTH = 50

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize prompt injection detector

        Args:
            config: Optional configuration dict with custom patterns or thresholds
        """
        self.config = config or {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile all regex patterns for performance"""
        self.compiled_patterns = []

        for pattern_list in [
            self.INSTRUCTION_PATTERNS,
            self.ROLE_PATTERNS,
            self.EXFILTRATION_PATTERNS,
            self.SYSTEM_PATTERNS,
            self.ENCODING_PATTERNS,
            self.INJECTION_MARKERS,
            self.SUSPICIOUS_PATTERNS,
        ]:
            for pattern, name, severity in pattern_list:
                self.compiled_patterns.append(
                    (re.compile(pattern, re.IGNORECASE), name, severity)
                )

    def detect(self, params: Dict[str, Any]) -> InjectionDetectionResult:
        """
        Detect prompt injection attempts in tool parameters

        Args:
            params: Dictionary of tool parameters to scan

        Returns:
            InjectionDetectionResult with findings and risk score
        """
        findings = []

        # Scan all string values in params
        for key, value in self._flatten_params(params).items():
            if not isinstance(value, str):
                continue

            # Pattern matching
            findings.extend(self._scan_patterns(value, key))

            # Entropy analysis
            entropy_finding = self._check_entropy(value, key)
            if entropy_finding:
                findings.append(entropy_finding)

        # Calculate risk score
        risk_score = self._calculate_risk_score(findings)

        return InjectionDetectionResult(
            detected=len(findings) > 0,
            risk_score=risk_score,
            findings=findings
        )

    def _flatten_params(self, params: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """
        Flatten nested dictionary to extract all string values

        Args:
            params: Dictionary to flatten
            prefix: Current key prefix for nested values

        Returns:
            Flattened dictionary with dotted keys
        """
        flat = {}

        for key, value in params.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                flat.update(self._flatten_params(value, full_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        flat.update(self._flatten_params(item, f"{full_key}[{i}]"))
                    else:
                        flat[f"{full_key}[{i}]"] = item
            else:
                flat[full_key] = value

        return flat

    def _scan_patterns(self, text: str, location: str) -> List[InjectionFinding]:
        """
        Scan text for known injection patterns

        Args:
            text: Text to scan
            location: Parameter location/key

        Returns:
            List of findings
        """
        findings = []

        for pattern, name, severity in self.compiled_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                matched_text = match.group(0)
                findings.append(InjectionFinding(
                    severity=severity,
                    pattern_name=name,
                    matched_text=matched_text[:100],  # Truncate long matches
                    location=location,
                    recommendation=self._get_recommendation(severity, name)
                ))

        return findings

    def _check_entropy(self, text: str, location: str) -> Optional[InjectionFinding]:
        """
        Check if text has suspiciously high entropy (potential encoded payload)

        Args:
            text: Text to analyze
            location: Parameter location/key

        Returns:
            InjectionFinding if high entropy detected, None otherwise
        """
        if len(text) < self.ENTROPY_MIN_LENGTH:
            return None

        entropy = self._calculate_entropy(text)

        if entropy > self.ENTROPY_THRESHOLD:
            return InjectionFinding(
                severity=Severity.MEDIUM,
                pattern_name="High entropy",
                matched_text=text[:50] + "...",
                location=location,
                recommendation="Potential encoded payload detected. Verify content is legitimate."
            )

        return None

    def _calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of text

        Args:
            text: Text to analyze

        Returns:
            Entropy value (higher = more random/encoded)
        """
        if not text:
            return 0.0

        # Count character frequencies
        char_counts: Dict[str, int] = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1

        # Calculate entropy
        entropy = 0.0
        text_len = len(text)

        for count in char_counts.values():
            probability = count / text_len
            entropy -= probability * math.log2(probability)

        return entropy

    def _calculate_risk_score(self, findings: List[InjectionFinding]) -> int:
        """
        Calculate overall risk score (0-100)

        Args:
            findings: List of detected findings

        Returns:
            Risk score from 0 (safe) to 100 (critical)
        """
        if not findings:
            return 0

        score = 0

        # Score based on severity
        severity_weights = {
            Severity.CRITICAL: 40,
            Severity.HIGH: 25,
            Severity.MEDIUM: 15,
            Severity.LOW: 5,
        }

        for finding in findings:
            score += severity_weights.get(finding.severity, 0)

        # Cap at 100
        return min(score, 100)

    def _get_recommendation(self, severity: Severity, pattern_name: str) -> str:
        """Get recommendation text for a finding"""
        if severity == Severity.CRITICAL:
            return f"BLOCK REQUEST: {pattern_name} detected. This indicates a likely attack."
        elif severity == Severity.HIGH:
            return f"Alert security team: {pattern_name} detected. Review request carefully."
        elif severity == Severity.MEDIUM:
            return f"Warning: {pattern_name} detected. May be legitimate but requires review."
        else:
            return f"Low risk: {pattern_name} detected. Log for monitoring."
