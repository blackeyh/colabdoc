# ColabDoc

A collaborative document editor with real-time co-editing, user authentication, permission management, version history, export, and a streamed AI assistant sidebar.

## Requirements

- Python 3.12+
- Node.js 18+
- npm

## Tech Stack

- Backend: FastAPI + SQLAlchemy + SQLite/PostgreSQL
- Frontend: React + Vite
- Realtime: WebSockets + Yjs snapshots/updates
- Auth: JWT
- Editor: Tiptap (ProseMirror)
- AI: OpenAI-compatible provider abstraction + null test/demo provider

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/blackeyh/colabdoc
cd colabdoc
```

**2. Optional: review the default local config**

`start.sh` will automatically create `.env` from `.env.example` if neither
`env` nor `.env` exists. The shipped example is runnable locally as-is:

- SQLite database
- `AI_PROVIDER=null` for no-network demos/tests
- OpenAI-compatible AI variables prefilled for a local Ollama-style server if you later switch to `AI_PROVIDER=openai`

If you want to create the file yourself:

```bash
cp .env.example .env
```

Important variables:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy URL. The example uses local SQLite for zero-config startup. |
| `JWT_SECRET` | Secret used to sign access and refresh tokens |
| `JWT_ALGORITHM` | Signing algorithm (default `HS256`) |
| `JWT_ACCESS_MINUTES` | Access-token lifetime in minutes (default `20`) |
| `JWT_REFRESH_DAYS` | Refresh-token lifetime in days (default `7`) |
| `AI_PROVIDER` | `null` (canned responses, default) or `openai` |
| `LM_STUDIO_BASE_URL` | OpenAI-compatible endpoint (Ollama, LM Studio, or api.openai.com) |
| `LM_STUDIO_MODEL` | Model identifier |
| `OPENAI_API_KEY` | Optional; required when hitting api.openai.com |
| `OPENAI_MODEL` | Optional; model identifier for the OpenAI provider |

The backend loads configuration from either `env` or `.env`.

**3. Run the app**
```bash
./start.sh
```

This script:

- creates `.venv` if it does not exist
- installs backend dependencies when the venv is missing or requirements changed
- creates `.env` from `.env.example` if no env file exists
- replaces the template JWT secret with a generated local secret on first run
- installs frontend packages if needed
- builds the React app into `frontend/dist`
- starts the FastAPI server on port `8000`

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Development Notes

- API docs are available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
- The backend serves the built frontend from `frontend/dist`.
- The default local SQLite database created by the example config lives at `backend/colabdoc.db`.
- If you want to run the backend manually, use:

```bash
cd backend
../.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
```

## Architecture Overview

- The React frontend owns authentication state, the Tiptap editor, and the AI/version/sidebar UX.
- The FastAPI backend exposes REST APIs for auth, documents, permissions, versions, export, and AI.
- A single WebSocket endpoint handles collaboration presence, Yjs update relay, cursors, typing, and durable document snapshots.
- SQLAlchemy stores documents, permissions, versions, and AI interaction history.
- AI providers sit behind one backend interface, so switching between `null`, Ollama/LM Studio, or OpenAI-compatible hosted APIs is a config change rather than a route rewrite.

For the final submission architecture diagrams and the explicit mapping from the
Assignment 1 report to the delivered Assignment 2 system, see
[ARCHITECTURE_ADDENDUM.md](ARCHITECTURE_ADDENDUM.md).

For a single consolidated submission document, see
[ASSIGNMENT2_REPORT.md](ASSIGNMENT2_REPORT.md).

For a styled PDF submission version, see
[ASSIGNMENT2_REPORT.pdf](ASSIGNMENT2_REPORT.pdf).

## Features

- Sign up / log in
- Create and manage documents
- Add collaborators by searching their name or email
- Set permissions: Editor, Commenter, Viewer
- Real-time collaborative editing via Yjs over authenticated WebSockets
- In-editor collaborator carets and selection highlights
- Version history with restore
- Streamed AI assistant suggestions with accept/reject/edit flow
- Export the current saved document as HTML or plain text

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
| `init` | `{content, title, role, active_users, crdt_state}` | Immediately after auth, to seed local state. |
| `update` | `{content, user}` | Legacy full-document update path for backwards compatibility. |
| `crdt_update` | `{update, user}` | Another user sent a Yjs incremental update. |
| `crdt_snapshot` | `{snapshot, user, target_user_id?}` | Full Yjs snapshot used for late-join or reconnect sync. |
| `sync_request` | `{requester}` | A collaborator is asking peers to replay the current CRDT snapshot. |
| `reset` | `{content, snapshot, user}` | A version restore replaced the whole shared document. |
| `cursor` | `{user, position}` | Another user moved their selection. |
| `typing` | `{user}` | Another user sent a typing ping. |
| `user_joined` | `{user}` | A collaborator joined the room. |
| `user_left` | `{user}` | A collaborator disconnected. |

`content` is JSON-B on the wire: either the Tiptap document shape (`{type:"doc", content:[…]}`)
or the legacy plain-text shape (`{text:"…"}`) for documents that predate the rich-text editor.
The frontend normalizes both via `frontend/src/lib/contentCompat.js`.

Remote `cursor` messages are rendered directly inside the editor using
ProseMirror decorations: collaborators show up as a colored caret label, and
non-collapsed selections get a tinted highlight in that collaborator's color.

### Client → server messages

| Type | Payload | Effect |
|---|---|---|
| `update` | `{content, save_version?}` | Legacy full-document persist/broadcast path. |
| `persist` | `{content, save_version?}` | Persist the latest rich-text JSON and optionally snapshot a new Version. Requires `editor` or `owner` role. |
| `crdt_update` | `{update, snapshot}` | Relay a Yjs incremental update and refresh the room’s latest full snapshot. |
| `crdt_snapshot` | `{snapshot, target_user_id?}` | Publish or directly replay a full Yjs document snapshot. |
| `sync_request` | `{}` | Ask connected peers to replay their latest full snapshot. |
| `reset` | `{content, snapshot}` | Broadcast a version-restore reset to all collaborators. |
| `cursor` | `{position}` | Broadcast selection position. |
| `typing` | `{}` | Broadcast a typing indicator (rate-limited by the client). |

### Offline behaviour

Live editing now runs through Yjs, so concurrent edits from multiple connected
collaborators merge at the CRDT layer instead of overwriting the whole
document. The backend still stores durable JSON snapshots for export, AI, and
version history, and caches the latest opaque Yjs snapshot per room so late
joiners can bootstrap quickly.

If a client disconnects, it keeps the latest full Yjs snapshot plus the latest
durable JSON persist request. On reconnect, it republishes its current snapshot,
requests a fresh peer snapshot, and then flushes the persisted server save. This
is a pragmatic middle ground between full Yjs server persistence and the older
last-write-wins document overwrite flow.

## AI Streaming

The editor requests AI suggestions through `POST /documents/{doc_id}/ai/assist/stream`.
The backend returns a `text/event-stream` response with these event types:

| Event | Payload | Meaning |
|---|---|---|
| `meta` | `{id, action, status}` | AI interaction row created; stream started. |
| `delta` | `{chunk}` | Next streamed text chunk from the provider. |
| `done` | `{id, action, status, suggestion}` | Stream completed successfully. |
| `error` | `{id, action, status, message, partial}` | Provider failed mid-stream; partial text is preserved. |

The frontend renders `delta` chunks progressively while generation is in
progress. `AbortController` powers the Cancel button; the backend records the
interaction as `cancelled` if the client disconnects before completion.

AI actions are restricted to `editor` and `owner` roles. `viewer` and
`commenter` users see a clear read-only message in the sidebar and receive
`403` from the backend if they attempt the action endpoints directly.

## AI History

`GET /documents/{doc_id}/ai/history` returns document-level interaction history
for any collaborator with read access. Each entry includes:

- input (`selected_text`)
- full generated prompt (`prompt_text`)
- provider/model metadata
- response (`suggestion`)
- provider status (`pending`, `completed`, `failed`, `cancelled`)
- user decision (`pending`, `accepted`, `rejected`, `edited`)
- final applied text when the user edited or accepted the suggestion

The sidebar history panel refreshes whenever a new interaction is created or
resolved, so the document-level audit trail stays current during the demo.

## AI During Collaboration

AI suggestions are generated from a truncated snapshot of the current document
context plus the user's current selection; they are never auto-applied. The
user always compares original vs. suggestion first, then explicitly accepts,
edits, or rejects it. If collaborators have changed the surrounding document
significantly while a suggestion is open, the safe workflow is to reject it and
run AI again against the latest shared state. The accept action is anchored to
the original requested range, so it does not silently follow a later caret move
to a different location. Accepted suggestions still flow through the editor's
undo history, so they can be reverted immediately.

## Document Export

The editor bar includes an `Export` action that downloads the current saved
document through `GET /documents/{doc_id}/export?format=html|txt`.

- `html` returns a styled standalone HTML file that preserves headings, lists,
  blockquotes, code blocks, and inline formatting such as bold/italic/code.
- `txt` returns a plain-text export with the document title plus readable
  paragraphs and list numbering/bullets.

Export is available to any user who can read the document (`viewer`,
`commenter`, `editor`, `owner`), because it operates on the already-saved
server version rather than unsaved local editor state.

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

At the time of this update, the automated suite covers:

- auth and refresh flow
- document CRUD + permissions
- AI prompt/context helpers
- AI invocation, streaming, history, and resolve logging
- WebSocket auth/basic exchange
- editor bar, AI panel, AI history panel, login, and remote cursor rendering

## Project Structure

```
backend/          FastAPI backend
  main.py         App entry point + WebSocket handler
  models.py       Database models
  auth.py         JWT authentication
  routers/        API route handlers (auth, documents, permissions, versions, ai)
  ai/             Prompt/config/provider layer
  exporters.py    HTML/TXT document export renderer
frontend/
  src/            React application source
  dist/           Production build output
env / .env        Environment variables (do not commit)
start.sh          Server startup script
```
