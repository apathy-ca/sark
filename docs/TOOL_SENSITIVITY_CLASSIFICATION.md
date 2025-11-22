## Tool Sensitivity Classification

SARK automatically classifies MCP tools based on their sensitivity level to enforce appropriate access controls and audit requirements.

### Sensitivity Levels

| Level | Description | Access Requirements | Examples |
|-------|-------------|---------------------|----------|
| **LOW** | Public or internal data, minimal restrictions | Authenticated users | `read_data`, `get_user`, `list_servers` |
| **MEDIUM** | Confidential data, requires proper role | Developer role or higher | `update_config`, `write_file`, `create_resource` |
| **HIGH** | Highly sensitive data, team-based access | Team membership + work hours + audit | `delete_user`, `exec_command`, `admin_panel` |
| **CRITICAL** | Mission-critical or sensitive operations | Team manager + MFA + work hours + audit | `process_payment`, `manage_credentials`, `encrypt_data` |

### Automatic Detection

Tools are automatically classified based on keyword analysis during registration:

#### Critical Keywords
Triggers **CRITICAL** sensitivity level:
- `payment`, `transaction`, `credit_card`
- `password`, `secret`, `key`, `token`, `credential`
- `auth`, `permission`, `access_control`
- `encrypt`, `decrypt`

#### High Keywords
Triggers **HIGH** sensitivity level:
- `delete`, `drop`, `remove`, `purge`
- `exec`, `execute`, `kill`, `destroy`
- `admin`, `root`, `sudo`, `truncate`

#### Medium Keywords
Triggers **MEDIUM** sensitivity level:
- `write`, `update`, `modify`, `change`, `edit`
- `create`, `insert`, `save`, `upload`
- `put`, `post`, `patch`

#### Low Keywords
Triggers **LOW** sensitivity level:
- `read`, `get`, `fetch`, `retrieve`
- `list`, `show`, `display`, `view`
- `query`, `search`, `find`

**Default:** If no keywords match, tools default to **MEDIUM** sensitivity.

### API Endpoints

#### Get Tool Sensitivity
```http
GET /api/v1/tools/{tool_id}/sensitivity
```

**Response:**
```json
{
  "tool_id": "123e4567-e89b-12d3-a456-426614174000",
  "tool_name": "delete_user",
  "sensitivity_level": "high",
  "is_overridden": false,
  "last_updated": "2025-11-22T10:30:00Z"
}
```

#### Update Tool Sensitivity (Manual Override)
```http
POST /api/v1/tools/{tool_id}/sensitivity
```

**Request:**
```json
{
  "sensitivity_level": "critical",
  "reason": "Handles PII data - requires additional protection"
}
```

**Authorization:** Requires admin role and policy approval.

**Audit Trail:** All manual overrides are logged with user ID, timestamp, and reason.

#### Detect Sensitivity (Testing)
```http
POST /api/v1/tools/detect-sensitivity
```

**Request:**
```json
{
  "tool_name": "process_payment",
  "tool_description": "Processes credit card transactions",
  "parameters": {
    "card_number": "string",
    "amount": "number"
  }
}
```

**Response:**
```json
{
  "detected_level": "critical",
  "keywords_matched": ["payment", "credit_card"],
  "detection_method": "critical_keywords"
}
```

#### Get Sensitivity History
```http
GET /api/v1/tools/{tool_id}/sensitivity/history
```

Returns all sensitivity changes including manual overrides.

#### Get Sensitivity Statistics
```http
GET /api/v1/tools/statistics/sensitivity
```

**Response:**
```json
{
  "total_tools": 150,
  "by_sensitivity": {
    "low": 45,
    "medium": 70,
    "high": 25,
    "critical": 10
  },
  "overridden_count": 5
}
```

#### List Tools by Sensitivity
```http
GET /api/v1/tools/sensitivity/{level}
```

Example: `GET /api/v1/tools/sensitivity/critical`

#### Bulk Detect Sensitivity
```http
POST /api/v1/tools/servers/{server_id}/tools/detect-all
```

Detects sensitivity for all tools on a server. Useful for re-classification.

### Integration with OPA Policies

Tool sensitivity levels are enforced through OPA policies:

```rego
# Example policy check
allow if {
    input.action == "tool:invoke"
    input.tool.sensitivity_level == "high"
    input.user.role == "developer"
    some team_id in input.user.teams
    team_id in input.tool.teams
    is_work_hours
    input.context.audit_enabled == true
}
```

The sensitivity level affects:
- **Access control**: Higher sensitivity requires elevated permissions
- **Time restrictions**: High/critical tools may be restricted to work hours
- **Audit requirements**: High/critical tools require audit logging
- **MFA requirements**: Critical tools require MFA verification
- **Team requirements**: High/critical tools require team ownership

### Automatic Detection During Registration

When registering a server, tools without explicit sensitivity levels are automatically classified:

```python
# In server registration
POST /api/v1/servers
{
  "name": "database-server",
  "tools": [
    {
      "name": "read_users",
      "description": "Retrieves user records"
      // No sensitivity_level specified
      // Will be auto-detected as LOW
    },
    {
      "name": "delete_account",
      "description": "Permanently deletes user account"
      // Will be auto-detected as HIGH
    }
  ]
}
```

### Manual Override Workflow

1. **Initial Classification**: Tool registered with auto-detected sensitivity
2. **Security Review**: Admin reviews tool sensitivity
3. **Override**: Admin updates sensitivity with justification
4. **Audit**: Change logged with user, timestamp, and reason
5. **Enforcement**: New sensitivity level immediately applied

### Best Practices

**For Tool Developers:**
- Use descriptive names that reflect the tool's purpose
- Include clear descriptions of what the tool does
- Explicitly set sensitivity_level if known
- Review auto-detected levels after registration

**For Security Teams:**
- Regularly review tool classifications using statistics endpoint
- Monitor manual overrides through audit logs
- Re-classify tools after major updates using bulk detection
- Document reasons for manual overrides

**For Administrators:**
- Set up alerts for critical tool registrations
- Review new high/critical tools before activation
- Enforce team ownership for high/critical tools
- Regular audits of tool sensitivity distribution

### Examples

#### Auto-Detection Examples

| Tool Name | Description | Detected Level | Reason |
|-----------|-------------|----------------|--------|
| `get_user_profile` | "Retrieves user information" | LOW | Contains "get" keyword |
| `update_settings` | "Modifies application settings" | MEDIUM | Contains "update" keyword |
| `delete_database` | "Drops database tables" | HIGH | Contains "delete" and "drop" |
| `process_payment` | "Handles credit card transactions" | CRITICAL | Contains "payment" and "credit_card" |
| `reset_password` | "Resets user passwords" | CRITICAL | Contains "password" |

#### Parameter Detection

```python
{
  "tool_name": "manage_account",
  "description": "Account management operations",
  "parameters": {
    "username": "string",
    "admin_privileges": "boolean",  // "admin" keyword
    "new_password": "string"        // "password" keyword
  }
}
# Detected: CRITICAL (due to "password" in parameters)
```

### Performance

- **Detection Speed**: <5ms per tool
- **Keyword Matching**: Regex-based with word boundaries
- **Caching**: Results cacheable (tool sensitivity rarely changes)
- **Bulk Operations**: Efficiently handles 100+ tools per server

### Security Considerations

1. **Principle of Least Privilege**: Default to MEDIUM, not LOW
2. **Conservative Classification**: When in doubt, classify higher
3. **Audit All Overrides**: Complete audit trail for compliance
4. **Immutable History**: Sensitivity changes are logged, not deleted
5. **Policy Integration**: Classification enforced through OPA policies

### Future Enhancements

- **ML-based classification**: Machine learning for more accurate detection
- **Custom keyword sets**: Organization-specific keyword configuration
- **Sensitivity scoring**: Numerical scores instead of discrete levels
- **Recommendation engine**: Suggest sensitivity based on usage patterns
- **Automated re-classification**: Periodic review and re-classification

---

**Related Documentation:**
- [OPA Policy Guide](OPA_POLICY_GUIDE.md)
- [Security Guide](SECURITY.md)
- [API Reference](API_INTEGRATION.md)
