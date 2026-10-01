-- Runs once, on the first start of an empty postgres volume.
-- Test database for pytest (TEST_DATABASE_URL). Extensions (pgvector) are created by Alembic migrations.
CREATE DATABASE uzsenpai_test;
