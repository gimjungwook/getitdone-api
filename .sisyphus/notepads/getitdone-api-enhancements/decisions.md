# Decisions

## Architecture Decisions
- No subagent system (single conversation flow for web chat)
- No AI agent creation feature
- No plan agent (file editing not needed)
- No title/summary agent (generate-title already implemented)
- Compaction: 50 messages auto-trigger, keep original messages, summary stored separately
- Session cost tracking: accumulate per-session alongside daily quota
