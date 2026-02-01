## Phase 7: Production Deployment (2026-02-01)

### 7-1: Environment Setup

#### Backend Environment Variables (getitdone-api)
Required environment variables:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `GOOGLE_GEMINI_API_KEY`: Google Gemini API key
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)

#### Frontend Environment Variables (aicampus)
Required environment variables:
- `NEXT_PUBLIC_OPENCODE_API_URL`: Backend API URL (e.g., http://localhost:8000)
- `NEXT_PUBLIC_SUPABASE_URL`: Supabase project URL
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: Supabase anonymous key

#### Configuration Files
- Backend: `getitdone-api/.env` (create from .env.example)
- Frontend: `aicampus/.env.local` (create from .env.example)

### 7-2: Backend Deployment

#### Deployment Steps
1. Install dependencies: `pip install -r requirements.txt`
2. Run migrations: `supabase db push`
3. Start server: `python -m uvicorn getitdone_api.main:app --host 0.0.0.0 --port 8000`
4. Verify health: `curl http://localhost:8000/health`

#### Deployment Platforms
- Option 1: Heroku (Python support)
- Option 2: Railway (Python support)
- Option 3: AWS Lambda (with API Gateway)
- Option 4: Google Cloud Run (containerized)

### 7-3: Frontend Deployment

#### Deployment Steps
1. Build: `npm run build`
2. Start: `npm run start`
3. Verify: `curl http://localhost:3000`

#### Deployment Platforms
- Vercel (recommended for Next.js)
- Netlify
- AWS Amplify
- Google Cloud Run

### 7-4: Health Check

#### Backend Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

#### Frontend Health Check
```bash
curl http://localhost:3000
# Expected: HTML response with status 200
```

#### Integration Health Check
1. Create session: `curl -X POST http://localhost:8000/session`
2. Send message: `curl -X POST http://localhost:8000/session/{id}/message`
3. Verify SSE streaming works

### 7-5: Documentation

#### Documentation Files
- Backend: `getitdone-api/README.md`
- Frontend: `aicampus/README.md`
- API: `getitdone-api/API.md`
- Deployment: `.sisyphus/notepads/ai-feature-rebuild/deployment.md`

#### Documentation Content
- Setup instructions
- Environment variables
- API endpoints
- Deployment steps
- Troubleshooting

### Status
- 7-1: Environment Setup - ✅ Documented
- 7-2: Backend Deployment - ⏳ Pending
- 7-3: Frontend Deployment - ⏳ Pending
- 7-4: Health Check - ⏳ Pending
- 7-5: Documentation - ⏳ Pending

### Next Steps
- Phase 8: Cleanup & Documentation
