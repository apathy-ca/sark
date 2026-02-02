# SARK Home Parental Controls Policy
# Content filtering and safety controls for minors using LLM services
#
# Use case: Block inappropriate content requests from children's devices

package sark.home.parental

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# =============================================================================
# Default Allow (with content filtering)
# =============================================================================

default allow := true
default reason := ""

# =============================================================================
# Deny Rules
# =============================================================================

# Deny if prompt contains blocked keywords
allow := false if {
    is_minor_device
    contains_blocked_content
}

# Deny if requesting blocked categories
allow := false if {
    is_minor_device
    requests_blocked_category
}

# Deny if age-inappropriate endpoint
allow := false if {
    is_minor_device
    is_age_restricted_endpoint
}

# =============================================================================
# Minor Device Detection
# =============================================================================

# Check if this is a device assigned to a minor
is_minor_device if {
    input.user.user_group in ["child", "children", "minor", "teen"]
}

is_minor_device if {
    input.user.device_name in data.home.minor_devices
}

is_minor_device if {
    input.user.device_ip in data.home.minor_device_ips
}

# =============================================================================
# Content Filtering
# =============================================================================

# Default blocked keyword categories for minors
default_blocked_keywords := [
    # Violence
    "how to make a weapon",
    "how to hurt",
    "how to kill",
    # Adult content indicators
    "nsfw",
    "explicit",
    "adult content",
    # Dangerous activities
    "how to hack",
    "bypass security",
    "exploit vulnerability"
]

# Get blocked keywords from config or use defaults
blocked_keywords := data.home.parental_blocked_keywords if {
    data.home.parental_blocked_keywords
}

blocked_keywords := default_blocked_keywords if {
    not data.home.parental_blocked_keywords
}

# Check if prompt contains any blocked keywords
contains_blocked_content if {
    prompt := lower(input.request.prompt_preview)
    some keyword in blocked_keywords
    contains(prompt, lower(keyword))
}

# Track which keyword was matched for logging
matched_keyword := keyword if {
    prompt := lower(input.request.prompt_preview)
    some keyword in blocked_keywords
    contains(prompt, lower(keyword))
}

# =============================================================================
# Category Filtering
# =============================================================================

# Blocked categories for minors
default_blocked_categories := [
    "adult",
    "violence",
    "gambling",
    "drugs",
    "weapons"
]

blocked_categories := data.home.parental_blocked_categories if {
    data.home.parental_blocked_categories
}

blocked_categories := default_blocked_categories if {
    not data.home.parental_blocked_categories
}

# Check if request is for a blocked category
requests_blocked_category if {
    input.request.category in blocked_categories
}

# =============================================================================
# Age-Restricted Endpoints
# =============================================================================

# Some LLM endpoints may be age-restricted
default_age_restricted_endpoints := [
    "api.unrestricted-llm.com",
    "adult-ai.example.com"
]

age_restricted_endpoints := data.home.age_restricted_endpoints if {
    data.home.age_restricted_endpoints
}

age_restricted_endpoints := default_age_restricted_endpoints if {
    not data.home.age_restricted_endpoints
}

is_age_restricted_endpoint if {
    input.request.endpoint in age_restricted_endpoints
}

# =============================================================================
# Safe Mode Enforcement
# =============================================================================

# Check if safe mode is required for this device
safe_mode_required if {
    is_minor_device
    input.rules.enforce_safe_mode == true
}

# Deny if safe mode required but not enabled in request
allow := false if {
    safe_mode_required
    not input.request.safe_mode == true
}

# =============================================================================
# Reason Messages
# =============================================================================

reason := "Content blocked: Request contains inappropriate keywords for minors" if {
    is_minor_device
    contains_blocked_content
}

reason := sprintf("Content blocked: Category '%s' is restricted for minors", [input.request.category]) if {
    is_minor_device
    requests_blocked_category
}

reason := "Endpoint blocked: Age-restricted LLM service" if {
    is_minor_device
    is_age_restricted_endpoint
}

reason := "Safe mode required but not enabled in request" if {
    safe_mode_required
    not input.request.safe_mode == true
}

# =============================================================================
# Policy Decision Output
# =============================================================================

decision := {
    "allow": allow,
    "reason": reason,
    "policy": "parental",
    "severity": severity,
    "metadata": {
        "is_minor_device": is_minor_device,
        "content_filtered": contains_blocked_content,
        "category_blocked": requests_blocked_category,
        "safe_mode_required": safe_mode_required
    }
}

severity := "info" if {
    allow
}

severity := "warning" if {
    not allow
    not contains_blocked_content
}

severity := "high" if {
    not allow
    contains_blocked_content
}

# =============================================================================
# Content Flags for Logging
# =============================================================================

# Flags to include in audit logs (without revealing full prompt)
content_flags := flags if {
    flags := [flag |
        some keyword in blocked_keywords
        contains(lower(input.request.prompt_preview), lower(keyword))
        flag := sprintf("matched:%s", [keyword])
    ]
}
