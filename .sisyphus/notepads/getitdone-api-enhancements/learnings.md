# Learnings

## 2026-01-31 Wave 1 Completed
- Step parts (step_start/step_finish) added to MessagePart model
- Session cost tracking (total_cost, total_input_tokens, total_output_tokens) added to SessionInfo
- Plan agent removed from DEFAULT_AGENTS
- Supabase DB uses UUID type for user_id column - "test-user" string causes errors
- Tests that need DB use Supabase remote connection (not local)
- Storage class has both Supabase and in-memory backends
- compaction agent added to agent.py with hidden=True, mode="primary"
- compaction.txt prompt file created at src/opencode_api/agent/prompts/compaction.txt
