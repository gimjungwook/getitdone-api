# Issues

## 2026-01-31 Compaction Tests UUID Error
- 9 compaction tests fail with: `invalid input syntax for type uuid: "test-user"`
- The test_session fixture uses `user_id="test-user"` but DB expects UUID format
- Fix: Either use mock/in-memory storage or use a real UUID like "00000000-0000-0000-0000-000000000001"
- Other test files (test_step_parts, test_session_costs) work because they don't hit Supabase

## 2026-01-31 DB Migrations Not Executed
- sql/004_add_step_parts.sql and sql/005_add_compaction_fields.sql not yet run on remote Supabase
- supabase db execute --file doesn't work, need SQL Editor or psql
