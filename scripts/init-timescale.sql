-- SARK TimescaleDB initialization script

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create audit_events table (will be converted to hypertable)
-- Note: This will be managed by SQLAlchemy, but we set up TimescaleDB-specific features here

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE sark_audit TO sark;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sark;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sark;

-- After table creation (run this manually or via migration):
-- SELECT create_hypertable('audit_events', 'timestamp');
-- CREATE INDEX idx_audit_events_user_id_timestamp ON audit_events (user_id, timestamp DESC);
-- CREATE INDEX idx_audit_events_server_id_timestamp ON audit_events (server_id, timestamp DESC);
-- CREATE INDEX idx_audit_events_event_type ON audit_events (event_type, timestamp DESC);
