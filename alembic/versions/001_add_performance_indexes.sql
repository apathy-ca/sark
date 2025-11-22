-- Performance Optimization: Add database indexes for common queries
--
-- This migration adds composite and single-column indexes to optimize
-- common query patterns identified during performance profiling.
--
-- Target: Database query time < 20ms for p95

-- ============================================================================
-- MCP Servers Table Indexes
-- ============================================================================

-- Index for filtering by status (common in list endpoints)
CREATE INDEX IF NOT EXISTS idx_mcp_servers_status
ON mcp_servers(status)
WHERE status != 'decommissioned';  -- Partial index excludes decommissioned servers

-- Index for filtering by sensitivity level (common in security queries)
CREATE INDEX IF NOT EXISTS idx_mcp_servers_sensitivity
ON mcp_servers(sensitivity_level);

-- Composite index for status + sensitivity queries
CREATE INDEX IF NOT EXISTS idx_mcp_servers_status_sensitivity
ON mcp_servers(status, sensitivity_level);

-- Index for owner queries (finding all servers owned by a user)
CREATE INDEX IF NOT EXISTS idx_mcp_servers_owner
ON mcp_servers(owner_id)
WHERE owner_id IS NOT NULL;

-- Index for team queries (finding all servers managed by a team)
CREATE INDEX IF NOT EXISTS idx_mcp_servers_team
ON mcp_servers(team_id)
WHERE team_id IS NOT NULL;

-- Index for created_at for chronological sorting
CREATE INDEX IF NOT EXISTS idx_mcp_servers_created_at
ON mcp_servers(created_at DESC);

-- Composite index for status + created_at (common list query pattern)
CREATE INDEX IF NOT EXISTS idx_mcp_servers_status_created
ON mcp_servers(status, created_at DESC);

-- ============================================================================
-- MCP Tools Table Indexes
-- ============================================================================

-- Index for finding tools by server (most common query)
-- Note: This might already exist as a foreign key index
CREATE INDEX IF NOT EXISTS idx_mcp_tools_server
ON mcp_tools(server_id);

-- Index for finding tools by sensitivity level
CREATE INDEX IF NOT EXISTS idx_mcp_tools_sensitivity
ON mcp_tools(sensitivity_level);

-- Composite index for server + sensitivity queries
CREATE INDEX IF NOT EXISTS idx_mcp_tools_server_sensitivity
ON mcp_tools(server_id, sensitivity_level);

-- ============================================================================
-- Audit Events Table Indexes (TimescaleDB)
-- ============================================================================

-- Composite index for user + timestamp queries (time-series pattern)
-- TimescaleDB automatically creates indexes on time column, but composite helps
CREATE INDEX IF NOT EXISTS idx_audit_events_user_time
ON audit_events(user_id, timestamp DESC)
WHERE user_id IS NOT NULL;

-- Composite index for event_type + timestamp (filtering by event type)
CREATE INDEX IF NOT EXISTS idx_audit_events_type_time
ON audit_events(event_type, timestamp DESC);

-- Composite index for server + timestamp (server audit trail)
CREATE INDEX IF NOT EXISTS idx_audit_events_server_time
ON audit_events(server_id, timestamp DESC)
WHERE server_id IS NOT NULL;

-- Index for severity filtering (security monitoring)
CREATE INDEX IF NOT EXISTS idx_audit_events_severity
ON audit_events(severity, timestamp DESC)
WHERE severity IN ('high', 'critical');  -- Partial index for important events only

-- Index for IP address lookups (security analysis)
CREATE INDEX IF NOT EXISTS idx_audit_events_ip
ON audit_events(ip_address, timestamp DESC)
WHERE ip_address IS NOT NULL;

-- ============================================================================
-- API Keys Table Indexes
-- ============================================================================

-- Index for active keys lookup (most common)
CREATE INDEX IF NOT EXISTS idx_api_keys_active
ON api_keys(is_active, created_at DESC)
WHERE is_active = true;

-- Index for user's API keys
CREATE INDEX IF NOT EXISTS idx_api_keys_user
ON api_keys(user_id, created_at DESC);

-- Index for key prefix lookup (fast key validation)
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix
ON api_keys(key_prefix)
WHERE is_active = true;

-- ============================================================================
-- Users Table Indexes
-- ============================================================================

-- Index for email lookups (authentication)
CREATE INDEX IF NOT EXISTS idx_users_email
ON users(email)
WHERE is_active = true;

-- Index for role-based queries
CREATE INDEX IF NOT EXISTS idx_users_role
ON users(role);

-- ============================================================================
-- Performance Notes
-- ============================================================================
--
-- Partial Indexes:
--   - WHERE clauses on indexes reduce index size and improve performance
--   - Only index the rows that are commonly queried
--
-- DESC Indexes:
--   - Most list queries sort by created_at/timestamp DESC (newest first)
--   - DESC indexes improve query performance for these patterns
--
-- Composite Indexes:
--   - Order matters: most selective column first
--   - Can be used for queries on leading columns only
--   - Example: idx_mcp_servers_status_created can be used for:
--     * WHERE status = 'active'
--     * WHERE status = 'active' ORDER BY created_at DESC
--     But NOT for: WHERE created_at > '2024-01-01' alone
--
-- Maintenance:
--   - PostgreSQL automatically maintains indexes
--   - Run ANALYZE periodically to update statistics
--   - Monitor index usage with pg_stat_user_indexes
--
-- ============================================================================

-- Analyze tables after adding indexes to update query planner statistics
ANALYZE mcp_servers;
ANALYZE mcp_tools;
ANALYZE audit_events;
ANALYZE api_keys;
ANALYZE users;
