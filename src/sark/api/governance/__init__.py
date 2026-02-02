"""
Governance API endpoints for home LLM governance.

Provides REST API endpoints for managing:
- Allowlist entries
- Time-based rules
- Emergency overrides
- Consent requests
- Per-request overrides
- Enforcement decisions
"""

from sark.api.governance.router import router

__all__ = ["router"]
