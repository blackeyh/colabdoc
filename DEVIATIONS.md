# Deviations & Design Notes

This document captures places where the ColabDoc implementation intentionally
diverges from the most obvious reading of the Assignment 2 brief, and the
reasoning behind each choice.

## Authentication — access + refresh split

**What:** `/auth/login` returns both an access token (short-lived, 20 min by
default) and a refresh token (7 days). `/auth/refresh` exchanges a refresh
token for a fresh pair.

**Why:** The brief asks for short-lived JWTs with a way to stay signed in.
Rotating both tokens on refresh shrinks the window a leaked refresh token is
useful. The access token's `type: access` claim is checked on every protected
request, and the refresh token's `type: refresh` claim is checked only at the
refresh endpoint, so a token of the wrong kind is rejected even if the
signature is valid.

**Trade-off — localStorage:** Both tokens live in `localStorage`. This is
uniform with the existing Bearer/WebSocket auth (the WS token is a query
parameter, which `HttpOnly` cookies cannot provide), and keeps the frontend
simple. It is vulnerable to XSS: any script running in the origin can read
the tokens. A production deployment should move the refresh token to an
`HttpOnly; Secure; SameSite=Strict` cookie and have a dedicated
`/auth/refresh` endpoint that reads it from the cookie rather than the body.

## Roles — four roles, not three

**What:** The system keeps the pre-existing set: `owner`, `editor`,
`commenter`, `viewer`. The brief asks for "at least three."

**Why:** `commenter` was already wired into the codebase from Assignment 1.
Removing it would require a DB migration and would break any existing
permission rows. Keeping it is strictly additive and satisfies the "at
least three" requirement.

**How applied:** The ACL comparator in `routers/documents.py` and
`routers/versions.py` uses a numeric order
(`viewer < commenter < editor < owner`) so `commenter` sits between viewer
and editor — it can read, but cannot save edits or restore versions.

## Rich-text editor — Tiptap with a compat shim

**What:** The editor is Tiptap (ProseMirror) and stores content as the Tiptap
JSON document shape (`{type:"doc", content:[...]}`). Documents created under
Assignment 1 have the shape `{text:"…"}`.

**Why:** Tiptap gives us the toolbar features the brief asks for (bold,
italic, headings, lists, code blocks) and ships with undo history that covers
AI-accept insertions for free.

**How applied:** `frontend/src/lib/contentCompat.js:toTiptap` normalizes both
shapes on load. Legacy docs render as a single paragraph; the first edit
overwrites the stored content with a Tiptap doc. No migration is run on the
existing `documents.content` column.

## AI — provider abstraction and a null provider

**What:** `backend/ai/` exposes an `LLMProvider` ABC with two concrete
implementations: `OpenAIProvider` (talks to any OpenAI-compatible endpoint
including LM Studio) and `NullProvider` (returns a deterministic stub).
`get_provider()` picks one based on the `AI_PROVIDER` env var.

**Why:** The brief asks for AI features but not for a specific vendor. The
null provider keeps the full UX flow demonstrable and testable without a
running model, and decouples code review from model availability.

**How applied:** Prompts live in `backend/ai/prompts.py` as a dict keyed by
action; adding a new action is one dict entry. `truncate_context` keeps a
4000-character window centered on the selected text so long documents don't
blow the context budget.

## AI interactions — `user_action` and `final_text`

**What:** The `ai_interactions` table gained two columns: `user_action`
(`pending | accepted | rejected | edited`) and `final_text`.

**Why:** The brief asks for a history of AI use with user decisions. Storing
the original AI output in `suggestion` and the user's final text in
`final_text` preserves both sides of the diff so the history panel can show
exactly what changed.

**How applied:** The new `POST /documents/{id}/ai/interactions/{iid}/resolve`
endpoint is called by the frontend whenever the user accepts, edits, or
rejects a suggestion. On Postgres, a startup `ALTER TABLE IF NOT EXISTS`
migration in `main.py` adds the columns to existing deployments; on SQLite
(used in tests) the columns are created by `Base.metadata.create_all`.

## Collab — typing indicator and last-write-wins offline queue

**What:** The WebSocket protocol gained a `typing` message in both
directions. While the client is disconnected, it keeps a single-slot
last-write-wins buffer of the latest Tiptap JSON and flushes it on reconnect.

**Why:** The brief asks for presence/typing and for resilience against
transient disconnects. A full CRDT would handle concurrent offline edits
correctly, but is out of scope for this batch.

**How applied:** `frontend/src/hooks/useWebSocket.js` exposes an `onReconnect`
callback; `EditorPage.jsx` uses it to pull the canonical document via
`apiFetch('/documents/{id}')` before flushing the offline queue, so the last
server state wins when there is a conflict.

## Testing — SQLite with a JSONB→JSON shim

**What:** Pytest uses an in-memory SQLite engine. `database.py` defines
`JSONType = JSONB().with_variant(JSON(), "sqlite")`; all models use
`JSONType` instead of `JSONB` directly.

**Why:** The production DB is Postgres (Neon). Standing up a Postgres
instance per test run is slow and fragile; SQLite-in-memory is instant and
reliable. The variant trick means the same `mapped_column` definition works
in both places without branching in the model code.

**How applied:** `tests/conftest.py` redirects `SessionLocal` and `engine`
to the test DB, overrides the `get_db` dependency, and creates a fresh
schema per test. Fixtures (`client`, `auth_user`, `user_factory`,
`doc_factory`) handle the common setup.

## Out of scope for this batch

These were explicitly deferred and are not in the current change set:

- **Streaming AI responses.** The provider abstraction leaves room for it,
  but the router returns the full completion in a single response. SSE or
  WebSocket chunking is a follow-up.
- **End-to-end validation against a real LLM.** `OpenAIProvider` is
  implemented but not exercised in CI; manual verification against LM Studio
  is the current story.
- **CRDT/Yjs conflict resolution.** The offline queue is last-write-wins.
- **Remote cursor offsets on the Tiptap document.** Cursor broadcasts still
  carry the legacy textarea offset; mapping to ProseMirror positions is a
  follow-up.
- **Server-side refresh-token revocation list.** Logout is stateless; a
  compromised refresh token is valid until it expires.
- **Swapping the DB away from Neon.** Out of scope.
