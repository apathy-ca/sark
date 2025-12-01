# Adapter Code Review Checklist

**Version:** 1.0
**Owner:** ENGINEER-1 (Lead Architect)
**Purpose:** Ensure all adapter implementations meet quality standards

---

## Pre-Review Checklist (Submitter)

Before submitting an adapter for review, ensure:

- [ ] All abstract methods from `ProtocolAdapter` are implemented
- [ ] All contract tests in `BaseAdapterTest` pass
- [ ] Code coverage >= 85% for adapter code
- [ ] Integration tests with real protocol instances pass
- [ ] Documentation is complete (docstrings, README)
- [ ] No linting errors (`ruff check`)
- [ ] Type checking passes (`mypy`)
- [ ] CHANGELOG.md updated with changes

---

## Code Review Checklist (Reviewer)

### 1. Interface Compliance

- [ ] Implements all required abstract methods
- [ ] Method signatures match `ProtocolAdapter` interface exactly
- [ ] Returns correct types (ResourceSchema, CapabilitySchema, etc.)
- [ ] Raises correct exceptions per interface contract
- [ ] `protocol_name` is lowercase and unique
- [ ] `protocol_version` matches the protocol spec being implemented

### 2. Error Handling

- [ ] Uses adapter exceptions (`DiscoveryError`, `ValidationError`, etc.)
- [ ] Includes descriptive error messages
- [ ] Populates exception `details` field with context
- [ ] `invoke()` returns `InvocationResult(success=False)` instead of raising
- [ ] `health_check()` returns `False` instead of raising
- [ ] Handles timeouts gracefully
- [ ] Network errors are caught and converted to adapter exceptions

### 3. Data Validation

- [ ] `validate_request()` properly validates input against schemas
- [ ] Raises `ValidationError` with field-level errors
- [ ] Input schema validation is thorough
- [ ] Protocol-specific validation is correct
- [ ] Edge cases are handled (None, empty strings, etc.)

### 4. Resource Discovery

- [ ] `discover_resources()` returns valid `ResourceSchema` instances
- [ ] All required fields are populated
- [ ] `protocol` field matches `adapter.protocol_name`
- [ ] `sensitivity_level` is correctly determined
- [ ] Metadata includes protocol-specific information
- [ ] Handles discovery failures gracefully

### 5. Capability Handling

- [ ] `get_capabilities()` returns valid `CapabilitySchema` instances
- [ ] Capability IDs are unique and stable
- [ ] Input/output schemas are correct
- [ ] Sensitivity levels are appropriate
- [ ] Metadata includes protocol-specific info (HTTP method, gRPC package, etc.)
- [ ] Handles resources with no capabilities

### 6. Invocation

- [ ] `invoke()` measures duration correctly
- [ ] Results are correctly mapped to `InvocationResult`
- [ ] Protocol errors are handled and returned in `error` field
- [ ] Metadata includes useful debugging information
- [ ] Streaming support works if implemented
- [ ] Batch operations work if implemented

### 7. Performance

- [ ] Uses connection pooling where applicable
- [ ] Implements caching for capabilities (if beneficial)
- [ ] Batch operations are optimized (not just sequential)
- [ ] No blocking calls in async methods
- [ ] Proper use of async/await throughout
- [ ] Timeouts are configured appropriately

### 8. Testing

- [ ] Inherits from `BaseAdapterTest`
- [ ] All contract tests pass
- [ ] Integration tests with real protocol instances
- [ ] Edge cases are tested
- [ ] Error conditions are tested
- [ ] Code coverage >= 85%
- [ ] Tests are well-organized and documented

### 9. Documentation

- [ ] Class and method docstrings are complete
- [ ] Examples are provided in docstrings
- [ ] Protocol-specific config format is documented
- [ ] README in adapter directory explaining usage
- [ ] Any protocol quirks or limitations are documented

### 10. Code Quality

- [ ] Follows Python style guidelines (PEP 8)
- [ ] No linting errors
- [ ] Type hints on all functions
- [ ] Clear variable names
- [ ] No code duplication
- [ ] Complex logic is commented
- [ ] TODOs are tracked or removed

---

## Merge Criteria

An adapter PR can be merged when:

1. ✅ All checklist items above are satisfied
2. ✅ At least 2 approvals (including ENGINEER-1)
3. ✅ CI/CD pipeline passes (tests, linting, type checking)
4. ✅ Code coverage >= 85%
5. ✅ No unresolved review comments
6. ✅ Interface contract document is followed
7. ✅ Integration tests pass

---

## Automated Checks

The following are checked automatically by CI/CD:

- [ ] All tests pass
- [ ] Code coverage >= 85%
- [ ] No linting errors (`ruff check`)
- [ ] Type checking passes (`mypy`)
- [ ] No security vulnerabilities (`bandit`)
- [ ] Dependencies are up to date

---

## Sign-Off

| Reviewer | Role | Approval | Date |
|----------|------|----------|------|
| ENGINEER-1 | Lead Architect | Required | |
| QA-1 | Testing Lead | Required | |
| Additional | Team Member | Optional | |

---

## Notes

Use this space for review notes, questions, or concerns.

