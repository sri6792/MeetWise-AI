# MeetWise AI

AI-powered **pre-meeting briefing agent**. Enter who you are meeting and why; MeetWise researches the
organisation and attendee on the live web (Tavily), analyses the evidence with Claude, and produces a
personalised briefing with questions, opportunities and a PDF export, where **every statement carries an
evidence label and source reference**.

```
frontend/  Next.js + TypeScript + Tailwind        backend/  FastAPI + SQLAlchemy (SQLite / PostgreSQL)
```

## How it works

1. **Create a meeting** (company, attendee, date/time, purpose) → saved in the database.
2. **Research runs in the background** and reports real progress (the UI polls `/status`):
   news (last 30 days) → company profile → attendee's public professional background.
3. **Evidence is stored separately from interpretation.** Every Tavily result becomes a `Source`
   (URL, title, publication date *if provided*, retrieval date, freshness).
4. **Claude proposes statements and cites source ids; the evidence engine decides the label.**
5. A briefing, questions and opportunities are assembled, shown in the dashboard, saved to history,
   and exportable as PDF.

### Evidence & Freshness engine (`backend/app/services/evidence_service.py`)

Claude cannot award itself trust. Labels come from deterministic rules:

| Label | Rule |
|---|---|
| **Verified** | ≥ 2 independent domains, strong text match with the cited source text, at least one recent source, and any numbers in the claim appear in the source |
| **Partially supported** | Some support: one source, same-domain duplicates, undated sources, or weaker match |
| **Needs verification** | No valid source cited, invented source ids, or the cited text doesn't support the statement |
| **Potentially outdated** | Every supporting source is older than its window (news 30 days, other 365 days) |

- AI interpretations (`is_inference`) can **never** be "Verified" and are tagged "AI interpretation".
- Invented source ids are discarded. Missing publication dates stay **unknown**; they are never guessed.
- Gaps become visible "Limitations" in the briefing instead of being papered over.

## Setup (Windows)

### Backend
```powershell
cd C:\projects\MeetWise-AI\backend
venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env        # then add TAVILY_API_KEY and ANTHROPIC_API_KEY (save as UTF-8)
uvicorn app.main:app --reload
```
Docs: http://127.0.0.1:8000/docs · Status: http://127.0.0.1:8000/health

> **If you already ran an earlier version:** the app adds new columns automatically. If anything
> looks off, delete `backend/meetwise.db` (dev data only) and restart.

### Frontend
```powershell
cd C:\projects\MeetWise-AI\frontend
npm install
npm run dev                    # http://localhost:3000
```
Optional `frontend/.env.local`: `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000` (this is the default).

### Demo mode (no API keys)
Set `MOCK_MODE=true` in `backend/.env`. The full pipeline runs on **clearly labelled fictional data**
(`[MOCK DATA]` titles, `example.com` links). Mock briefings show a banner in the app and in the PDF.
Use it to rehearse, to build UI, or as a fallback if the network fails during a demo.

### Tests
```powershell
cd backend
pytest -v
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/meetings` | Create meeting (201) |
| GET | `/api/meetings` | List/search meetings |
| GET / PATCH / DELETE | `/api/meetings/{id}` | Read / edit / delete (delete removes all research) |
| POST | `/api/meetings/{id}/research` | Start research (202; 409 if running; 503 if keys missing) |
| GET | `/api/meetings/{id}/status` | Stage + progress % + error message |
| GET | `/api/meetings/{id}/briefing` | Full briefing with evidence labels and sources |
| GET | `/api/meetings/{id}/sources?category=` | Raw evidence list |
| GET | `/api/meetings/{id}/news` | News items (headline, summary, date, link) |
| GET | `/api/meetings/{id}/pdf` | Download PDF |
| GET | `/api/history` | History with `q`, `status`, date range, sort, pagination |
| GET | `/api/history/stats?today=` | Dashboard numbers |
| GET | `/health` | Backend, DB, key and mock-mode status |

TypeScript types for these shapes: `frontend/src/types/api.ts` (single contract for the frontend team).

## Deployment

**Backend → Render.** Use `render.yaml` (Blueprint), or create a Web Service manually with
root directory `backend`, build `pip install -r requirements.txt`, start
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set environment variables:
`TAVILY_API_KEY`, `ANTHROPIC_API_KEY`, `CORS_ORIGINS=https://<your-vercel-app>.vercel.app`, and
`DATABASE_URL` from a Render PostgreSQL database. SQLite also works, but its file is erased on every
redeploy. Research runs inside the web process, so run a single instance.

**Frontend → Vercel.** Import the repo, set root directory `frontend`, and add
`NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com`.

## Known limitations

- PDF uses standard fonts: non-Latin scripts (e.g. Hindi, Japanese) print as `?`.
- Free Render instances sleep; the first request after idle can take ~30 s. Open `/health` before demoing.
- Research quality depends on what Tavily finds. Obscure people may yield "no reliable public information",
  and the app says so rather than guessing.
- Meeting edits don't refresh an existing briefing; use "Re-run research".
