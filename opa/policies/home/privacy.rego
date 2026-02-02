# SARK Home Privacy Policy
# Detects and blocks PII (Personally Identifiable Information) in LLM prompts
#
# Use case: Prevent children from accidentally sharing personal information with AI services

package sark.home.privacy

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Allow
# =============================================================================

default allow := true
default reason := ""

# =============================================================================
# Deny Rules
# =============================================================================

# Deny if PII detected in prompt
allow := false if {
    pii_detected
    not is_pii_exemption
}

# =============================================================================
# PII Detection Patterns
# =============================================================================

# Email address detection
has_email if {
    regex.match(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`, input.request.prompt_preview)
}

# Phone number detection (various formats)
has_phone if {
    # US format: 123-456-7890, (123) 456-7890, 123.456.7890
    regex.match(`(\+1[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}`, input.request.prompt_preview)
}

# Social Security Number detection
has_ssn if {
    regex.match(`\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b`, input.request.prompt_preview)
}

# Credit card number detection (basic patterns)
has_credit_card if {
    # Visa, Mastercard, Amex patterns
    regex.match(`\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b`, input.request.prompt_preview)
}

# Street address detection (basic)
has_address if {
    # Matches patterns like "123 Main St" or "456 Oak Avenue"
    regex.match(`\b\d+\s+[A-Za-z]+\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct)\b`, input.request.prompt_preview)
}

# Date of birth patterns
has_dob if {
    # Matches MM/DD/YYYY or similar
    regex.match(`\b(0?[1-9]|1[0-2])[-/](0?[1-9]|[12][0-9]|3[01])[-/](19|20)\d{2}\b`, input.request.prompt_preview)
}

# Name patterns (when combined with other PII indicators)
has_full_name if {
    # Look for "my name is" patterns
    regex.match(`(?i)(my name is|i am|i'm)\s+[A-Z][a-z]+\s+[A-Z][a-z]+`, input.request.prompt_preview)
}

# Home address with city/state/zip
has_full_address if {
    regex.match(`\b\d+\s+[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Z]{2}\s+\d{5}`, input.request.prompt_preview)
}

# =============================================================================
# Combined PII Detection
# =============================================================================

# Any PII detected
pii_detected if { has_email }
pii_detected if { has_phone }
pii_detected if { has_ssn }
pii_detected if { has_credit_card }
pii_detected if { has_full_address }
pii_detected if { has_dob }

# Sensitive PII (more strict)
sensitive_pii_detected if { has_ssn }
sensitive_pii_detected if { has_credit_card }

# =============================================================================
# PII Type Tracking
# =============================================================================

# Track which types of PII were detected for logging
detected_pii_types := types if {
    types := [type |
        pii_checks := {
            "email": has_email,
            "phone": has_phone,
            "ssn": has_ssn,
            "credit_card": has_credit_card,
            "address": has_full_address,
            "dob": has_dob,
            "full_name": has_full_name
        }
        some type, detected in pii_checks
        detected == true
    ]
}

# =============================================================================
# Exemptions
# =============================================================================

# Allow PII for exempt user groups (e.g., adults managing their own data)
is_pii_exemption if {
    input.user.user_group in ["admin", "parent", "adult"]
    not sensitive_pii_detected  # Never allow SSN/CC even for adults
}

# Allow if device is marked as PII-exempt
is_pii_exemption if {
    input.user.device_name in data.home.pii_exempt_devices
    not sensitive_pii_detected
}

# =============================================================================
# Privacy Levels
# =============================================================================

# Privacy enforcement level
privacy_level := "strict" if {
    input.rules.privacy_level == "strict"
}

privacy_level := "moderate" if {
    input.rules.privacy_level == "moderate"
}

privacy_level := "permissive" if {
    input.rules.privacy_level == "permissive"
}

privacy_level := "moderate" if {
    not input.rules.privacy_level
}

# In strict mode, also block potential names
allow := false if {
    privacy_level == "strict"
    has_full_name
    not is_pii_exemption
}

# In permissive mode, only block sensitive PII
allow := true if {
    privacy_level == "permissive"
    not sensitive_pii_detected
}

# =============================================================================
# Reason Messages
# =============================================================================

reason := "Privacy alert: Social Security Number detected in prompt" if {
    has_ssn
}

reason := "Privacy alert: Credit card number detected in prompt" if {
    has_credit_card
    not has_ssn
}

reason := "Privacy alert: Email address detected in prompt" if {
    has_email
    not has_ssn
    not has_credit_card
}

reason := "Privacy alert: Phone number detected in prompt" if {
    has_phone
    not has_email
    not has_ssn
    not has_credit_card
}

reason := "Privacy alert: Personal address detected in prompt" if {
    has_full_address
    not has_phone
    not has_email
    not has_ssn
    not has_credit_card
}

reason := sprintf("Privacy alert: Multiple PII types detected (%s)", [concat(", ", detected_pii_types)]) if {
    count(detected_pii_types) > 1
}

# =============================================================================
# Policy Decision Output
# =============================================================================

decision := {
    "allow": allow,
    "reason": reason,
    "policy": "privacy",
    "severity": severity,
    "metadata": {
        "pii_detected": pii_detected,
        "sensitive_pii": sensitive_pii_detected,
        "pii_types": detected_pii_types,
        "privacy_level": privacy_level,
        "is_exempt": is_pii_exemption
    }
}

severity := "info" if {
    allow
    not pii_detected
}

severity := "warning" if {
    allow
    pii_detected
    is_pii_exemption
}

severity := "high" if {
    not allow
    not sensitive_pii_detected
}

severity := "critical" if {
    not allow
    sensitive_pii_detected
}

# =============================================================================
# Redaction Suggestions
# =============================================================================

# Suggest redacted version (for advisory mode)
redaction_suggestions := suggestions if {
    pii_detected
    suggestions := {
        "email": "[EMAIL REDACTED]",
        "phone": "[PHONE REDACTED]",
        "ssn": "[SSN REDACTED]",
        "credit_card": "[CARD REDACTED]",
        "address": "[ADDRESS REDACTED]",
        "dob": "[DOB REDACTED]"
    }
}
