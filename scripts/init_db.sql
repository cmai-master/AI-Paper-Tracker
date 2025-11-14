-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable additional PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for text similarity search

-- Create schema
CREATE SCHEMA IF NOT EXISTS paperpulse;

-- Set default search path
ALTER DATABASE paperpulse SET search_path TO paperpulse, public;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA paperpulse TO paperpulse;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA paperpulse TO paperpulse;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA paperpulse TO paperpulse;

-- Default grants for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA paperpulse GRANT ALL ON TABLES TO paperpulse;
ALTER DEFAULT PRIVILEGES IN SCHEMA paperpulse GRANT ALL ON SEQUENCES TO paperpulse;
