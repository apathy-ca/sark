-- SARK PostgreSQL initialization script

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create initial schema (tables will be created by Alembic/SQLAlchemy)

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE sark TO sark;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO sark;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO sark;
