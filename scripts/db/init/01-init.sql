-- ============================================================================
-- SARK Database Initialization
-- ============================================================================
-- This script runs automatically when initializing a new managed PostgreSQL
-- database. It creates necessary extensions and initial schema.
--
-- NOTE: This only runs for managed PostgreSQL. For external databases,
-- coordinate with your DBA team to apply these changes.
-- ============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable trigram similarity for fuzzy text search
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Enable additional text search capabilities
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Log completion
DO $$
BEGIN
    RAISE NOTICE 'SARK database initialization completed successfully';
END $$;
