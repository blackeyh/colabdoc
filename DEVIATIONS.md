# Deviations & Design Notes

This document captures places where the ColabDoc implementation intentionally
diverges from the most obvious reading of the Assignment 2 brief, and the
reasoning behind each choice.

## Authentication provider — local JWT auth instead of an external IdP

**What:** The PoC uses app-managed registration/login plus JWT access/refresh
tokens. It does not depend on a hosted authentication provider such as Auth0.

**Why:** For the assignment deliverable, a self-contained auth flow is easier
to run, demo, and test locally. It removes external dashboard/configuration
steps for reviewers while still covering protected routes, session refresh, and
role-based authorization.

**How applied:** Users are stored in the application database, passwords are
hashed locally, and the FastAPI backend issues JWTs directly. The current
system-context/runtime architecture should therefore be read as "ColabDoc
backend performs authentication" rather than "external IdP performs
authentication."

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
and editor — it can read, but cannot save edits, restore versions, or invoke
AI actions.

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

## Repository structure — simplified single repo layout

**What:** The deliverable is a single repository with `backend/` and
`frontend/` directories rather than multiple independently deployed services or
packages.

**Why:** The assignment submission is easier to clone, review, and demo when
the full stack lives in one place. The structure still keeps a clear separation
between frontend and backend responsibilities without requiring a more complex
workspace or package-manager setup.

**How applied:** `start.sh` bootstraps both halves of the stack from the repo
root, and the README documents the actual folder layout shipped in the PoC.

## External services from Assignment 1 — email/file storage omitted

**What:** The Assignment 1 diagrams included external email and file-storage
services, but the Assignment 2 PoC does not integrate either one.

**Why:** The shipped Assignment 2 feature set does not require attachment
storage or outbound email to demonstrate document collaboration, AI assistance,
permissions, export, or version history. Keeping these integrations out of the
PoC reduced setup friction and avoided dead configuration paths for reviewers.

**How applied:** Sharing is handled entirely inside the app by searching and
granting access to existing users, and exports are generated on demand from the
stored document content instead of being written to an external storage bucket.

## Export — HTML and TXT rather than binary office formats

**What:** Documents can be exported through
`GET /documents/{id}/export?format=html|txt`. The editor bar exposes that as
an `Export` control with `HTML` and `Text` options.

**Why:** Assignment 1 requires "at least one common portable format" that keeps
the current saved content readable. HTML and TXT satisfy that requirement while
remaining deterministic in tests, lightweight to generate on the backend, and
easy for graders to inspect without extra dependencies.

**How applied:** The backend renders Tiptap JSON into either a styled standalone
HTML document or a plain-text version with readable paragraphs and list
numbering. Export is allowed for any role with read access because it operates
on the persisted server copy of the document.

## Setup/runtime defaults — local SQLite and self-bootstrapping startup

**What:** `.env.example` now ships with a runnable local SQLite configuration,
and `start.sh` creates the virtual environment, installs backend/frontend
dependencies, and copies `.env.example` to `.env` when no env file exists.

**Why:** Assignment 2 explicitly asks for a reviewer-friendly run script. The
previous setup assumed a pre-existing venv, backend packages, and a manually
edited Postgres URL, which was a real friction point during testing.

**How applied:** The default reviewer path is now "clone -> `./start.sh` ->
open the app". Postgres remains supported by swapping `DATABASE_URL`, but the
example config is intentionally zero-dependency for local review. When the
script auto-creates `.env`, it also replaces the template JWT secret with a
fresh generated local secret.

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
blow the context budget. The provider interface now supports both full
completion (`complete`) and streamed generation (`stream_complete`), and the
frontend consumes the stream over `text/event-stream`.

## AI interactions — document-level audit trail

**What:** The `ai_interactions` table stores the selected text, generated
prompt, provider name, model name, response text, provider status, user
decision, and final applied text.

**Why:** The brief asks for a history of AI use that includes input, prompt,
model, response, and accept/reject status. A thin per-user activity feed was
not enough; the final implementation needs to function as a document-level
audit trail.

**How applied:** The new `POST /documents/{id}/ai/interactions/{iid}/resolve`
endpoint is called by the frontend whenever the user accepts, edits, or
rejects a suggestion. `GET /documents/{id}/ai/history` now returns the history
for the whole document, not just the current user. On Postgres, a startup
`ALTER TABLE IF NOT EXISTS` migration in `main.py` adds the extra metadata
columns to existing deployments; on SQLite (used in tests) the columns are
created by `Base.metadata.create_all`.

## Realtime stack — Yjs on the client, lightweight FastAPI relay on the server

**What:** Live text collaboration now uses Yjs in the frontend editor, while
FastAPI still provides the authenticated WebSocket transport, room presence,
cursor messages, version-reset broadcasts, and durable JSON persistence. There
is still no separate realtime service or Redis backplane.

**Why:** This closes the biggest gap between the Assignment 1 design and the
earlier Assignment 2 PoC: concurrent edits from connected collaborators now
merge at the CRDT layer instead of replacing the whole document. At the same
time, the deployment story stays simple enough for a local course demo.

**How applied:** `EditorTextarea.jsx` binds Tiptap to a per-document Yjs doc via
`@tiptap/extension-collaboration`, emits incremental updates plus full snapshots,
and applies incoming snapshots/updates over the existing WebSocket. The backend
stores the latest opaque snapshot for each in-memory room and replays it to late
joiners, while `persist` messages continue to write the canonical JSON copy used
by export, AI context, and version history.

## Collaboration presence — cursor rendering, typing, and snapshot-based reconnect

**What:** Presence still includes `typing` plus in-editor remote cursor/selection
rendering, but reconnect behavior no longer falls back to full-document
last-write-wins overwrites. Instead, clients republish their latest Yjs snapshot
and ask peers to replay the current room state.

**Why:** The brief asks for presence, realtime collaboration, and better
conflict handling. Snapshot replay is a practical compromise that works with the
existing FastAPI server without adding a full Yjs persistence service.

**How applied:** The server emits `sync_request`, `crdt_update`, `crdt_snapshot`,
and `reset` WebSocket messages. The frontend keeps the latest local snapshot for
reconnect, and `EditorTextarea.jsx` still overlays collaborator carets/highlights
with ProseMirror decorations on top of the Yjs-synchronized document.

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

- **End-to-end validation against a real LLM.** `OpenAIProvider` is
  implemented but not exercised in CI; manual verification against LM Studio
  is the current story.
- **Dedicated Yjs persistence / multi-process sync.** The server stores only the
  latest opaque room snapshot in memory plus the durable JSON document in the
  database. It does not persist the full Yjs update log or coordinate multiple
  app instances through a shared Yjs backend.
- **Server-side refresh-token revocation list.** Logout is stateless; a
  compromised refresh token is valid until it expires.
- **Multi-instance realtime fan-out.** The in-memory WebSocket manager is
  sufficient for the assignment demo, but horizontal scaling would require a
  shared backplane such as Redis or a dedicated collaboration service.
