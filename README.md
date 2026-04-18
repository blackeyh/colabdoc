# ColabDoc

A collaborative document editor with real-time co-editing, user authentication, permission management, version history, and an AI assistant sidebar.

## Requirements

- Python 3.12+
- Node.js 18+
- npm

## Tech Stack

- Backend: FastAPI + SQLAlchemy + PostgreSQL
- Frontend: React + Vite
- Realtime: WebSockets
- Auth: JWT

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/blackeyh/colabdoc
cd colabdoc
```

**2. Create and activate a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**3. Install backend dependencies**
```bash
pip install -r backend/requirements.txt
```

**4. Install frontend dependencies**
```bash
cd frontend
npm install
cd ..
```

**5. Create an `env` or `.env` file** in the project root.

Copy `.env.example` and fill in the values:

```bash
cp .env.example .env
```

Required variables (see `.env.example` for documentation):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL for Postgres (SQLite is used in tests only) |
| `JWT_SECRET` | Secret used to sign access and refresh tokens |
| `JWT_ALGORITHM` | Signing algorithm (default `HS256`) |
| `JWT_ACCESS_MINUTES` | Access-token lifetime in minutes (default `20`) |
| `JWT_REFRESH_DAYS` | Refresh-token lifetime in days (default `7`) |
| `AI_PROVIDER` | `null` (canned responses, default) or `openai` |
| `LM_STUDIO_BASE_URL` | OpenAI-compatible endpoint (LM Studio or api.openai.com) |
| `LM_STUDIO_MODEL` | Model identifier |
| `OPENAI_API_KEY` | Optional; required when hitting api.openai.com |
| `OPENAI_MODEL` | Optional; model identifier for the OpenAI provider |

The backend loads configuration from either `env` or `.env`.

**6. Run the app**
```bash
./start.sh
```

This script:

- installs frontend packages if needed
- builds the React app into `frontend/dist`
- starts the FastAPI server on port `8000`

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Development Notes

- API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
- The backend serves the built frontend from `frontend/dist`.
- If you want to run the backend manually, use:

```bash
cd backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

## Features

- Sign up / log in
- Create and manage documents
- Add collaborators by searching their name or email
- Set permissions: Editor, Commenter, Viewer
- Real-time collaborative editing via WebSockets
- Version history with restore
- AI assistant panel for document help

## WebSocket Protocol

Clients open an authenticated WebSocket at `/ws/documents/{doc_id}?token={access_token}`.
The access token is the short-lived JWT issued by `POST /auth/login` (see [Authentication](#authentication)).

### Close codes

| Code | Meaning |
|---|---|
| `4001` | Invalid or expired access token. Client should refresh and reconnect. |
| `4003` | User has no permission on this document. |
| `4004` | Document not found. |

### Server → client messages

| Type | Payload | Emitted when |
|---|---|---|
| `init` | `{content, title, role, active_users}` | Immediately after auth, to seed local state. |
| `update` | `{content, user}` | Another user persisted a change. |
| `cursor` | `{user, position}` | Another user moved their selection. |
| `typing` | `{user}` | Another user sent a typing ping. |
| `user_joined` | `{user}` | A collaborator joined the room. |
| `user_left` | `{user}` | A collaborator disconnected. |

`content` is JSON-B on the wire: either the Tiptap document shape (`{type:"doc", content:[…]}`)
or the legacy plain-text shape (`{text:"…"}`) for documents that predate the rich-text editor.
The frontend normalizes both via `frontend/src/lib/contentCompat.js`.

### Client → server messages

| Type | Payload | Effect |
|---|---|---|
| `update` | `{content, save_version?}` | Persist the document; optionally snapshot a new Version. Requires `editor` or `owner` role. |
| `cursor` | `{position}` | Broadcast selection position. |
| `typing` | `{}` | Broadcast a typing indicator (rate-limited by the client). |

### Offline behaviour

While the socket is disconnected, the frontend queues a single last-write-wins
update and flushes it on reconnect. This is an intentional simplification — a
CRDT (e.g. Yjs) would preserve concurrent edits, but is out of scope.

## Authentication

`POST /auth/login` returns a short-lived access token (default 20 minutes) and a
refresh token (default 7 days). The frontend stores both in `localStorage` and
uses a single-flight refresh on 401: `api.js` automatically hits
`POST /auth/refresh` with the refresh token, updates both tokens, and retries
the original request once. The WebSocket hook attempts the same refresh on close
code `4001` before surfacing a session-expired event.

Trade-off: `localStorage` is uniform with the existing Bearer/WebSocket auth
surface but is vulnerable to XSS. Moving the refresh token to an `HttpOnly`
cookie is tracked in `DEVIATIONS.md`.

## Testing

### Backend (pytest)

```bash
pip install -r backend/requirements.txt
pytest -q
```

Tests run against an in-memory SQLite database. `database.py` exposes a
dialect-aware `JSONType` that picks `JSONB` on Postgres and `JSON` on SQLite,
so the same models work in both places. `AI_PROVIDER` defaults to `null`
under test, meaning the full AI flow is exercised against the canned
`NullProvider` — no model required.

### Frontend (vitest)

```bash
cd frontend
npm install
npm run test
```

Vitest runs under `jsdom` with `@testing-library/react`. Tests live in
`frontend/tests/`. `apiFetch` is mocked at the module boundary so specs don't
depend on a running backend.

## Project Structure

```
backend/          FastAPI backend
  main.py         App entry point + WebSocket handler
  models.py       Database models
  auth.py         JWT authentication
  routers/        API route handlers (auth, documents, permissions, versions)
frontend/
  src/            React application source
  dist/           Production build output
env / .env        Environment variables (do not commit)
start.sh          Server startup script
```
