# Data Governance Policy
# Enforces data classification, PII protection, retention, and cross-border transfer rules

package mcp.gateway.datagovernance

import future.keywords.if
import future.keywords.in

# ============================================================================
# DATA CLASSIFICATION
# ============================================================================

# Data classification levels
data_classifications := {"public", "internal", "confidential", "restricted"}

# Tool's data classification level
tool_data_classification := classification if {
    classification := input.tool.data_classification
}

tool_data_classification := "internal" if {
    not input.tool.data_classification
}

# User's data access clearance
user_clearance_level := level if {
    level := input.user.data_clearance
}

user_clearance_level := "internal" if {
    not input.user.data_clearance
}

# Classification hierarchy (higher can access lower)
classification_hierarchy := {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}

# Check if user has sufficient clearance
has_sufficient_clearance if {
    tool_level := classification_hierarchy[tool_data_classification]
    user_level := classification_hierarchy[user_clearance_level]
    user_level >= tool_level
}

# ============================================================================
# PII DETECTION AND HANDLING
# ============================================================================

# Patterns that indicate PII
pii_indicators := {
    "email", "phone", "ssn", "credit_card", "passport",
    "drivers_license", "medical_record", "biometric", "ip_address",
}

# Check if tool accesses PII
tool_accesses_pii if {
    some indicator in pii_indicators
    contains(lower(input.tool.description), indicator)
}

tool_accesses_pii if {
    input.tool.handles_pii == true
}

# PII handling requirements
pii_requirements_met if {
    not tool_accesses_pii
}

pii_requirements_met if {
    tool_accesses_pii
    # User must have PII training
    input.user.pii_training_completed == true
    # User must acknowledge PII handling
    input.context.pii_acknowledged == true
    # Audit logging must be enabled
    input.context.audit_enabled == true
}

# ============================================================================
# DATA RETENTION POLICIES
# ============================================================================

# Retention periods by classification (days)
retention_periods := {
    "public": 2555,        # 7 years
    "internal": 1825,      # 5 years
    "confidential": 1095,  # 3 years
    "restricted": 365,     # 1 year
}

# Check if data retention policy allows this operation
retention_policy_met if {
    input.action != "data_export"
}

retention_policy_met if {
    input.action == "data_export"
    classification := tool_data_classification
    max_retention := retention_periods[classification]

    # Check if exported data is within retention period
    data_age_days := (input.context.timestamp - input.context.data_created_at) / 86400
    data_age_days <= max_retention
}

# ============================================================================
# CROSS-BORDER DATA TRANSFER
# ============================================================================

# Data residency requirements
data_residency := {
    "restricted": ["US"],  # Restricted data must stay in US
    "confidential": ["US", "CA", "EU"],
    "internal": ["US", "CA", "EU", "UK", "AU"],
    "public": "*",  # No restrictions
}

# Check if cross-border transfer is allowed
cross_border_allowed if {
    input.action != "data_export"
}

cross_border_allowed if {
    input.action == "data_export"
    classification := tool_data_classification
    allowed_regions := data_residency[classification]

    # Check if destination is allowed
    destination_region := input.context.export_destination_region
    (allowed_regions == "*") or (destination_region in allowed_regions)
}

# GDPR compliance for EU data
gdpr_compliant if {
    destination_region := input.context.export_destination_region
    destination_region != "EU"
}

gdpr_compliant if {
    destination_region := input.context.export_destination_region
    destination_region == "EU"
    # Must have legal basis for processing
    input.context.gdpr_legal_basis in {"consent", "contract", "legal_obligation", "legitimate_interest"}
    # Must have data processing agreement
    input.context.dpa_signed == true
}

# ============================================================================
# SENSITIVE DATA REDACTION
# ============================================================================

# Fields that must be redacted for non-privileged users
redaction_required_fields := {
    "ssn", "tax_id", "credit_card_full", "password", "api_key",
    "private_key", "medical_diagnosis", "salary",
}

# Check if user can access unredacted data
can_access_unredacted if {
    input.user.role in {"admin", "security_admin", "compliance_officer"}
}

can_access_unredacted if {
    input.user.data_clearance == "restricted"
    input.context.business_justification_provided == true
}

# Redaction requirements met
redaction_requirements_met if {
    can_access_unredacted
}

redaction_requirements_met if {
    not can_access_unredacted
    # System must apply redaction
    input.context.redaction_enabled == true
}

# ============================================================================
# DATA MINIMIZATION
# ============================================================================

# Check if tool only accesses minimum necessary data
data_minimization_met if {
    # Allow if specific fields are requested (not SELECT *)
    requested_fields := input.context.requested_fields
    count(requested_fields) > 0
    count(requested_fields) < 50  # Reasonable limit
}

data_minimization_met if {
    # Allow for admin/audit purposes
    input.user.role in {"admin", "auditor"}
    input.context.audit_purpose == true
}

# ============================================================================
# ENCRYPTION REQUIREMENTS
# ============================================================================

# Data at rest encryption required for sensitive data
encryption_at_rest_required if {
    tool_data_classification in {"confidential", "restricted"}
}

encryption_requirements_met if {
    not encryption_at_rest_required
}

encryption_requirements_met if {
    encryption_at_rest_required
    input.context.encryption_at_rest_enabled == true
}

# Data in transit encryption (always required)
encryption_in_transit_met if {
    input.context.tls_enabled == true
    input.context.tls_version in {"1.2", "1.3"}
}

# ============================================================================
# DATA LINEAGE TRACKING
# ============================================================================

# Require data lineage for restricted data
data_lineage_required if {
    tool_data_classification == "restricted"
}

data_lineage_met if {
    not data_lineage_required
}

data_lineage_met if {
    data_lineage_required
    input.context.data_lineage_tracked == true
    count(input.context.data_lineage_chain) > 0
}

# ============================================================================
# FINAL AUTHORIZATION DECISION
# ============================================================================

allow if {
    has_sufficient_clearance
    pii_requirements_met
    retention_policy_met
    cross_border_allowed
    gdpr_compliant
    redaction_requirements_met
    data_minimization_met
    encryption_requirements_met
    encryption_in_transit_met
    data_lineage_met
}

default allow := false

# ============================================================================
# DECISION METADATA
# ============================================================================

failed_checks := checks if {
    checks := {check |
        not has_sufficient_clearance
        check := "insufficient_clearance"
    } | {check |
        not pii_requirements_met
        check := "pii_requirements_not_met"
    } | {check |
        not retention_policy_met
        check := "retention_policy_violation"
    } | {check |
        not cross_border_allowed
        check := "cross_border_transfer_blocked"
    } | {check |
        not gdpr_compliant
        check := "gdpr_non_compliant"
    } | {check |
        not redaction_requirements_met
        check := "redaction_required"
    } | {check |
        not data_minimization_met
        check := "data_minimization_violation"
    } | {check |
        not encryption_requirements_met
        check := "encryption_required"
    } | {check |
        not data_lineage_met
        check := "data_lineage_required"
    }
}

reason := "Allowed: Data governance policies satisfied" if {
    allow
}

reason := sprintf("Denied: Data governance violations: %s", [concat(", ", failed_checks)]) if {
    not allow
}

result := {
    "allow": allow,
    "reason": reason,
    "data_classification": tool_data_classification,
    "user_clearance": user_clearance_level,
    "requires_redaction": not can_access_unredacted,
    "pii_handling_required": tool_accesses_pii,
    "failed_checks": failed_checks,
}
