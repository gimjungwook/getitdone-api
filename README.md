---
title: OpenCode API
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# OpenCode API

LLM Agent API Server - ported from TypeScript [opencode](https://github.com/anomalyco/opencode) to Python.

## Features

- **Multi-provider LLM support**: Anthropic (Claude), OpenAI (GPT-4), Google Gemini via LiteLLM
- **Tool system**: Web search, web fetch, todo management, question (user input)
- **Session management**: Persistent conversations with Supabase storage
- **SSE streaming**: Real-time streaming responses with step tracking
- **Session cost tracking**: Per-session token usage and cost accumulation
- **Conversation compaction**: Auto-compact after 50 messages to reduce API costs
- **Message pagination**: Offset-based pagination with total count
- **Daily usage quota**: Per-user daily token limits with Supabase auth
- **REST API**: FastAPI with automatic OpenAPI docs

## API Endpoints

### Sessions

- `GET /session` - List all sessions
- `POST /session` - Create a new session
- `GET /session/{id}` - Get session details
- `PATCH /session/{id}` - Update session (title)
- `DELETE /session/{id}` - Delete a session
- `GET /session/{id}/message` - List messages (paginated)
- `POST /session/{id}/message` - Send a message (SSE streaming response)
- `POST /session/{id}/abort` - Cancel ongoing generation
- `POST /session/{id}/generate-title` - Generate session title from first message
- `GET /session/{id}/cost` - Get session cost breakdown
- `POST /session/{id}/compact` - Trigger conversation compaction
- `GET /session/{id}/compaction-status` - Get compaction status

### Providers

- `GET /provider` - List available LLM providers
- `GET /provider/{id}` - Get provider details
- `GET /provider/{id}/model` - List provider models

### Events

- `GET /event` - Subscribe to real-time events (SSE)

## SSE Event Types

When streaming via `POST /session/{id}/message`, the following event types are sent:

| Type | Description | Key Fields |
|------|-------------|------------|
| `message_start` | New assistant message begins | `message_id`, `parent_id` |
| `text` | Text content chunk | `text` |
| `reasoning` | Model thinking/reasoning | `text` |
| `tool_call` | Tool invocation | `tool_call: { id, name, arguments }` |
| `tool_result` | Tool execution result | `text` |
| `step_start` | Agentic loop step begins | `step_number`, `max_steps` |
| `step_finish` | Agentic loop step ends | `step_number`, `stop_reason`, `cost` |
| `done` | Generation complete | `usage: { input_tokens, output_tokens }`, `stop_reason` |
| `error` | Error occurred | `error` |

## Message Pagination

`GET /session/{id}/message` supports pagination:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | null | Max messages to return |
| `offset` | int | 0 | Messages to skip |
| `order` | string | "asc" | "asc" (oldest first) or "desc" (newest first) |

Response format:
```json
{
  "messages": [...],
  "total_count": 128,
  "limit": 40,
  "offset": 0
}
```

## Environment Variables

Set these as Hugging Face Space secrets or in `.env`:

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models |
| `OPENAI_API_KEY` | OpenAI API key for GPT models |
| `GEMINI_API_KEY` | Google Gemini API key |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `OPENCODE_SERVER_PASSWORD` | Optional: Basic auth password |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python app.py

# Or with uvicorn
uvicorn app:app --host 0.0.0.0 --port 7860 --reload
```

## API Documentation

Once running, visit:

- Swagger UI: `http://localhost:7860/docs`
- ReDoc: `http://localhost:7860/redoc`

## Example Usage

```python
import httpx

# Create a session
response = httpx.post("http://localhost:7860/session")
session = response.json()
session_id = session["id"]

# Send a message (with SSE streaming)
with httpx.stream(
    "POST",
    f"http://localhost:7860/session/{session_id}/message",
    json={"content": "Hello, what can you help me with?"}
) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            print(line[6:])

# Get messages with pagination
response = httpx.get(
    f"http://localhost:7860/session/{session_id}/message",
    params={"limit": 20, "offset": 0, "order": "desc"}
)
data = response.json()
print(f"Total: {data['total_count']}, Showing: {len(data['messages'])}")

# Get session cost
response = httpx.get(f"http://localhost:7860/session/{session_id}/cost")
cost = response.json()
print(f"Total cost: ${cost['total_cost']:.4f}")
```

## License

MIT
