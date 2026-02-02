# Tests for SARK Home Parental Controls Policy
package sark.home.parental_test

import data.sark.home.parental

# =============================================================================
# Test: Allow normal content for minors
# =============================================================================

test_allow_educational_content if {
    parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "Help me with my math homework", "endpoint": "api.openai.com"}
    }
}

test_allow_creative_content if {
    parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "Write a story about a friendly dragon", "endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Block inappropriate content for minors
# =============================================================================

test_deny_violence_keywords if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "how to make a weapon at home", "endpoint": "api.openai.com"}
    }
}

test_deny_harm_keywords if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "how to hurt someone", "endpoint": "api.openai.com"}
    }
}

test_deny_explicit_keywords if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "show me nsfw content", "endpoint": "api.openai.com"}
    }
}

test_deny_hacking_keywords if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "how to hack into a computer", "endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Allow same content for adults
# =============================================================================

test_allow_all_content_for_admin if {
    parental.allow with input as {
        "user": {"device_name": "admin-pc", "user_group": "admin"},
        "request": {"prompt_preview": "how to make a weapon in a video game", "endpoint": "api.openai.com"}
    }
}

test_allow_all_content_for_adult if {
    parental.allow with input as {
        "user": {"device_name": "adult-laptop", "user_group": "adult"},
        "request": {"prompt_preview": "write about security vulnerabilities", "endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Minor device detection
# =============================================================================

test_detect_minor_by_group_child if {
    parental.is_minor_device with input as {
        "user": {"user_group": "child", "device_name": "test"}
    }
}

test_detect_minor_by_group_teen if {
    parental.is_minor_device with input as {
        "user": {"user_group": "teen", "device_name": "test"}
    }
}

test_detect_minor_by_device_name if {
    parental.is_minor_device with input as {
        "user": {"user_group": "unknown", "device_name": "kids-ipad"}
    }
        with data.home.minor_devices as ["kids-ipad", "childrens-laptop"]
}

test_not_minor_adult_group if {
    not parental.is_minor_device with input as {
        "user": {"user_group": "adult", "device_name": "work-laptop"}
    }
}

# =============================================================================
# Test: Blocked categories
# =============================================================================

test_deny_adult_category if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "normal prompt", "category": "adult", "endpoint": "api.openai.com"}
    }
}

test_deny_violence_category if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "normal prompt", "category": "violence", "endpoint": "api.openai.com"}
    }
}

test_allow_education_category if {
    parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "normal prompt", "category": "education", "endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Age-restricted endpoints
# =============================================================================

test_deny_age_restricted_endpoint if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "hello", "endpoint": "api.unrestricted-llm.com"}
    }
}

test_allow_standard_endpoint if {
    parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "hello", "endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Case insensitivity
# =============================================================================

test_deny_uppercase_keywords if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "HOW TO MAKE A WEAPON", "endpoint": "api.openai.com"}
    }
}

test_deny_mixed_case_keywords if {
    not parental.allow with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "How To Hack Into something", "endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Reason messages
# =============================================================================

test_reason_blocked_keywords if {
    parental.reason == "Content blocked: Request contains inappropriate keywords for minors" with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "how to make a weapon", "endpoint": "api.openai.com"}
    }
}

# =============================================================================
# Test: Decision output structure
# =============================================================================

test_decision_structure_allow if {
    decision := parental.decision with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "help with homework", "endpoint": "api.openai.com"}
    }
    decision.allow == true
    decision.policy == "parental"
    decision.severity == "info"
}

test_decision_structure_deny if {
    decision := parental.decision with input as {
        "user": {"device_name": "kids-tablet", "user_group": "child"},
        "request": {"prompt_preview": "how to make a weapon", "endpoint": "api.openai.com"}
    }
    decision.allow == false
    decision.policy == "parental"
    decision.severity == "high"
}
