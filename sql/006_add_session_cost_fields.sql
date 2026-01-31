-- Migration: Add cost tracking fields to sessions
-- Run this in Supabase SQL Editor
-- 
-- These columns are used by Session.update() in prompt.py to track
-- per-session cumulative cost and token usage.

-- 1. Add cost/token tracking columns to sessions
ALTER TABLE opencode_sessions
ADD COLUMN IF NOT EXISTS total_cost NUMERIC(10, 6) DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_input_tokens INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_output_tokens INTEGER DEFAULT 0;

-- 2. Add index for cost queries (e.g., sorting sessions by cost)
CREATE INDEX IF NOT EXISTS idx_opencode_sessions_cost
ON opencode_sessions(user_id, total_cost)
WHERE total_cost > 0;

-- Verify the changes
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'opencode_sessions'
-- AND column_name IN ('total_cost', 'total_input_tokens', 'total_output_tokens')
-- ORDER BY ordinal_position;
