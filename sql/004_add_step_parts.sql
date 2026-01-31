-- Migration: Add step_start and step_finish part types
-- Run this in Supabase SQL Editor

-- 1. Add new columns for step tracking
ALTER TABLE opencode_message_parts
ADD COLUMN IF NOT EXISTS step_number INTEGER,
ADD COLUMN IF NOT EXISTS max_steps INTEGER,
ADD COLUMN IF NOT EXISTS input_tokens INTEGER,
ADD COLUMN IF NOT EXISTS output_tokens INTEGER,
ADD COLUMN IF NOT EXISTS cost NUMERIC(10, 6),
ADD COLUMN IF NOT EXISTS stop_reason TEXT;

-- 2. Update type check constraint to include 'step_start' and 'step_finish'
ALTER TABLE opencode_message_parts
DROP CONSTRAINT IF EXISTS opencode_message_parts_type_check;

ALTER TABLE opencode_message_parts
ADD CONSTRAINT opencode_message_parts_type_check
CHECK (type IN ('text', 'tool_call', 'tool_result', 'reasoning', 'step_start', 'step_finish'));

-- 3. Add indexes for step tracking queries
CREATE INDEX IF NOT EXISTS idx_opencode_message_parts_step_type
ON opencode_message_parts(type)
WHERE type IN ('step_start', 'step_finish');

CREATE INDEX IF NOT EXISTS idx_opencode_message_parts_step_number
ON opencode_message_parts(message_id, step_number)
WHERE step_number IS NOT NULL;

-- Verify the changes
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'opencode_message_parts'
-- ORDER BY ordinal_position;
