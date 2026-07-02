-- PostgreSQL initialization script for the Mastery Engine.
-- This script runs on first database creation (docker-entrypoint-initdb.d).

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas for each bounded context (per Task 004)
CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS content;
CREATE SCHEMA IF NOT EXISTS learning;
CREATE SCHEMA IF NOT EXISTS assessment;
CREATE SCHEMA IF NOT EXISTS mastery;
CREATE SCHEMA IF NOT EXISTS scheduling;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS billing;
CREATE SCHEMA IF NOT EXISTS administration;
CREATE SCHEMA IF NOT EXISTS infrastructure;

-- Grant privileges to the application user
GRANT USAGE ON SCHEMA identity TO mastery;
GRANT USAGE ON SCHEMA content TO mastery;
GRANT USAGE ON SCHEMA learning TO mastery;
GRANT USAGE ON SCHEMA assessment TO mastery;
GRANT USAGE ON SCHEMA mastery TO mastery;
GRANT USAGE ON SCHEMA scheduling TO mastery;
GRANT USAGE ON SCHEMA analytics TO mastery;
GRANT USAGE ON SCHEMA billing TO mastery;
GRANT USAGE ON SCHEMA administration TO mastery;
GRANT USAGE ON SCHEMA infrastructure TO mastery;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Mastery Engine database initialized with 10 schemas.';
END $$;
