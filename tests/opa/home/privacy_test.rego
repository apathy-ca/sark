# Tests for SARK Home Privacy Policy
package sark.home.privacy_test

import data.sark.home.privacy

# =============================================================================
# Test: Allow content without PII
# =============================================================================

test_allow_no_pii if {
    privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "Help me write a story about a cat"}
    }
}

test_allow_normal_questions if {
    privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "What is the capital of France?"}
    }
}

# =============================================================================
# Test: Detect and block email addresses
# =============================================================================

test_detect_email if {
    privacy.has_email with input as {
        "request": {"prompt_preview": "My email is john.doe@example.com"}
    }
}

test_deny_email_for_minor if {
    not privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "Contact me at test@gmail.com"}
    }
}

test_detect_various_email_formats if {
    privacy.has_email with input as {
        "request": {"prompt_preview": "user.name+tag@sub.domain.co.uk"}
    }
}

# =============================================================================
# Test: Detect and block phone numbers
# =============================================================================

test_detect_phone_dashes if {
    privacy.has_phone with input as {
        "request": {"prompt_preview": "Call me at 555-123-4567"}
    }
}

test_detect_phone_dots if {
    privacy.has_phone with input as {
        "request": {"prompt_preview": "My number is 555.123.4567"}
    }
}

test_detect_phone_with_area_code if {
    privacy.has_phone with input as {
        "request": {"prompt_preview": "Call (555) 123-4567"}
    }
}

test_deny_phone_for_minor if {
    not privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "My mom's phone is 555-867-5309"}
    }
}

# =============================================================================
# Test: Detect and block SSN (always blocked, even for adults)
# =============================================================================

test_detect_ssn_dashes if {
    privacy.has_ssn with input as {
        "request": {"prompt_preview": "My SSN is 123-45-6789"}
    }
}

test_detect_ssn_spaces if {
    privacy.has_ssn with input as {
        "request": {"prompt_preview": "SSN: 123 45 6789"}
    }
}

test_deny_ssn_for_anyone if {
    not privacy.allow with input as {
        "user": {"user_group": "adult"},
        "request": {"prompt_preview": "My social security number is 123-45-6789"}
    }
}

test_deny_ssn_for_admin if {
    # Even admins cannot share SSN
    not privacy.allow with input as {
        "user": {"user_group": "admin"},
        "request": {"prompt_preview": "SSN: 123-45-6789"}
    }
}

# =============================================================================
# Test: Detect and block credit card numbers
# =============================================================================

test_detect_visa if {
    privacy.has_credit_card with input as {
        "request": {"prompt_preview": "My card is 4111111111111111"}
    }
}

test_detect_mastercard if {
    privacy.has_credit_card with input as {
        "request": {"prompt_preview": "Card number: 5500000000000004"}
    }
}

test_detect_amex if {
    privacy.has_credit_card with input as {
        "request": {"prompt_preview": "Amex: 340000000000009"}
    }
}

test_deny_credit_card_for_anyone if {
    not privacy.allow with input as {
        "user": {"user_group": "adult"},
        "request": {"prompt_preview": "My credit card is 4111111111111111"}
    }
}

# =============================================================================
# Test: Detect addresses
# =============================================================================

test_detect_full_address if {
    privacy.has_full_address with input as {
        "request": {"prompt_preview": "I live at 123 Main Street, Springfield, IL 62701"}
    }
}

test_deny_address_for_minor if {
    not privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "My address is 456 Oak Avenue, Chicago, IL 60601"}
    }
}

# =============================================================================
# Test: Adult exemptions (for non-sensitive PII)
# =============================================================================

test_allow_email_for_adult if {
    privacy.allow with input as {
        "user": {"user_group": "adult"},
        "request": {"prompt_preview": "My email is adult@example.com"}
    }
}

test_allow_phone_for_parent if {
    privacy.allow with input as {
        "user": {"user_group": "parent"},
        "request": {"prompt_preview": "Call me at 555-123-4567"}
    }
}

test_allow_address_for_admin if {
    privacy.allow with input as {
        "user": {"user_group": "admin"},
        "request": {"prompt_preview": "Office at 123 Business Drive, New York, NY 10001"}
    }
}

# =============================================================================
# Test: Sensitive PII always blocked
# =============================================================================

test_sensitive_pii_ssn if {
    privacy.sensitive_pii_detected with input as {
        "request": {"prompt_preview": "123-45-6789"}
    }
}

test_sensitive_pii_credit_card if {
    privacy.sensitive_pii_detected with input as {
        "request": {"prompt_preview": "4111111111111111"}
    }
}

# =============================================================================
# Test: PII type tracking
# =============================================================================

test_detected_pii_types_email if {
    types := privacy.detected_pii_types with input as {
        "request": {"prompt_preview": "test@example.com"}
    }
    "email" in types
}

test_detected_pii_types_multiple if {
    types := privacy.detected_pii_types with input as {
        "request": {"prompt_preview": "Email: test@example.com, Phone: 555-123-4567"}
    }
    "email" in types
    "phone" in types
}

# =============================================================================
# Test: Privacy levels
# =============================================================================

test_strict_privacy_blocks_names if {
    not privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "My name is John Smith"},
        "rules": {"privacy_level": "strict"}
    }
}

test_permissive_allows_email if {
    privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "test@example.com"},
        "rules": {"privacy_level": "permissive"}
    }
}

test_permissive_still_blocks_ssn if {
    not privacy.allow with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "123-45-6789"},
        "rules": {"privacy_level": "permissive"}
    }
}

# =============================================================================
# Test: Reason messages
# =============================================================================

test_reason_ssn_detected if {
    privacy.reason == "Privacy alert: Social Security Number detected in prompt" with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "My SSN is 123-45-6789"}
    }
}

test_reason_email_detected if {
    privacy.reason == "Privacy alert: Email address detected in prompt" with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "Contact me at test@example.com"}
    }
}

# =============================================================================
# Test: Decision output structure
# =============================================================================

test_decision_structure_allow if {
    decision := privacy.decision with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "Tell me about dinosaurs"}
    }
    decision.allow == true
    decision.policy == "privacy"
    decision.metadata.pii_detected == false
}

test_decision_structure_deny if {
    decision := privacy.decision with input as {
        "user": {"user_group": "child"},
        "request": {"prompt_preview": "My SSN is 123-45-6789"}
    }
    decision.allow == false
    decision.policy == "privacy"
    decision.severity == "critical"
    decision.metadata.sensitive_pii == true
}
