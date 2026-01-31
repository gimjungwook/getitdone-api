-- Migration: Add compaction tracking fields
-- Run this in Supabase SQL Editor

-- 1. Add compaction tracking columns to message_parts
ALTER TABLE opencode_message_parts
ADD COLUMN IF NOT EXISTS is_compacted BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS compacted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS original_token_count INTEGER;

-- 2. Add compaction summary field to sessions
ALTER TABLE opencode_sessions
ADD COLUMN IF NOT EXISTS compaction_summary TEXT,
ADD COLUMN IF NOT EXISTS last_compacted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS compaction_count INTEGER DEFAULT 0;

-- 3. Add index for compacted parts queries
CREATE INDEX IF NOT EXISTS idx_opencode_message_parts_compacted
ON opencode_message_parts(session_id, is_compacted)
WHERE is_compacted = TRUE;

-- 4. Add index for compaction tracking
CREATE INDEX IF NOT EXISTS idx_opencode_sessions_compacted
ON opencode_sessions(id, last_compacted_at)
WHERE compaction_count > 0;

-- Verify the changes
-- SELECT 
--   table_name, 
--   column_name, 
--   data_type, 
--   is_nullable
-- FROM information_schema.columns
-- WHERE table_name IN ('opencode_message_parts', 'opencode_sessions')
-- AND column_name IN ('is_compacted', 'compacted_at', 'original_token_count', 'compaction_summary', 'last_compacted_at', 'compaction_count')
-- ORDER BY table_name, ordinal_position;