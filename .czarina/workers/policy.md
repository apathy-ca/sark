# Policy Validation Framework Developer

## Role
Build policy validation framework to prevent OPA policy injection attacks and ensure all policies are safe.

## Version Assignments
- v1.2.0-policy

## Responsibilities

### v1.2.0-policy (Policy Validation - 320K tokens)
- Implement `src/sark/policy/validator.py` with syntax and safety checks
- Implement `src/sark/policy/test_runner.py` for YAML-based policy testing
- Update `src/sark/policy/loader.py` to integrate validator
- Validate and fix all existing policies in `opa/policies/`
- Create test suites for all policies
- Write comprehensive documentation (POLICY_AUTHORING_GUIDE.md, POLICY_VALIDATION.md)
- Achieve 90%+ code coverage

## Files
- `src/sark/policy/validator.py` (NEW - 200+ lines)
- `src/sark/policy/test_runner.py` (NEW - 150+ lines)
- `src/sark/policy/loader.py` (UPDATE - existing file)
- `tests/unit/policy/test_validator.py` (NEW - 250+ lines)
- `opa/policies/tests/*.yaml` (NEW - test suites)
- `docs/POLICY_AUTHORING_GUIDE.md` (NEW)
- `docs/POLICY_VALIDATION.md` (NEW)

## Tech Stack
- Python 3.11+
- OPA CLI (opa check, opa eval)
- Regular expressions (pattern matching)
- YAML (test suite format)
- pytest (testing)

## Token Budget
Total: 320K tokens
- v1.2.0-policy: 320K tokens

## Git Workflow
Branches by version:
- v1.2.0-policy: feat/policy-validation

When complete:
1. Commit changes with descriptive messages
2. Push to branch feat/policy-validation
3. Create PR to main
4. Update token metrics in status

## Pattern Library
Review before starting:
- czarina-core/patterns/ERROR_RECOVERY_PATTERNS.md
- czarina-core/patterns/CZARINA_PATTERNS.md

## Version Completion Criteria

### v1.2.0-policy Complete When:
- [ ] PolicyValidator with syntax validation via `opa check`
- [ ] Required rules verification (allow, deny)
- [ ] 10+ forbidden patterns detected (blanket allow, system access, http.send, etc)
- [ ] Sample input testing framework
- [ ] PolicyTestRunner with YAML test suite support
- [ ] Test execution via OPA evaluate
- [ ] Expected/actual comparison
- [ ] Validator integrated into policy loading pipeline
- [ ] Invalid policies rejected with clear errors
- [ ] 100% of existing policies validated and passing
- [ ] Test suites created for all policies
- [ ] 20+ unit tests passing
- [ ] 90%+ code coverage
- [ ] POLICY_AUTHORING_GUIDE.md complete with examples
- [ ] POLICY_VALIDATION.md complete with forbidden patterns
- [ ] Token budget: ≤ 352K tokens (110% of projected)