# Changes vs `main`

Summary of everything changed or added in the working tree compared to the
`main` branch. Totals: **+5,212 / −1,272** across 24 modified files, plus 22
new files.

## Modified files (24)

### Backend

| File | Δ | What changed |
|---|---|---|
| `backend/auth.py` | +47 | Access + refresh tokens with `type` claim, separate decoders, configurable lifetimes from env. |
| `backend/database.py` | +10 | Dialect-aware `JSONType = JSONB().with_variant(JSON(), "sqlite")` for test compatibility. |
| `backend/main.py` | +35 | Postgres-only idempotent `ALTER TABLE ADD COLUMN IF NOT EXISTS` for `user_action`/`final_text`; `typing` broadcast in WS loop. |
| `backend/models.py` | +11 | `AIInteraction.user_action`, `AIInteraction.final_text`; switched to `JSONType`. |
| `backend/requirements.txt` | +4 | Adds `openai`, `httpx`, `pytest`, `pytest-asyncio`. |
| `backend/routers/auth.py` | +72 | `/auth/refresh` endpoint; `RegisterRequest`/`LoginResponse`/`TokenPair` models; `response_model` + `summary` on every route. |
| `backend/routers/ai.py` | +237 | Rewritten: `/assist` + `/resolve` + paginated `/history`; 6-action validation; `ClientDisconnect` → `status=cancelled`; Tiptap-aware text extraction. |
| `backend/routers/documents.py` | +65 | Pydantic response models (`DocumentResponse`, `DocumentListResponse`, `DocumentUpdateResponse`, `DeleteResponse`); `response_model` + `summary` on each route. |
| `backend/routers/permissions.py` | +46 | Pydantic response models (`PermissionEntry`, `PermissionResponse`, `MessageResponse`); `response_model` + `summary` on each route. |
| `backend/routers/versions.py` | +52 | Pydantic response models + `response_model` + `summary` polish. |

### Frontend

| File | Δ | What changed |
|---|---|---|
| `frontend/package.json` | +13 | Adds `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/pm`; dev-deps `vitest`, `@testing-library/*`, `jsdom`; new `test` script. |
| `frontend/package-lock.json` | +3,916 | Lockfile churn from the new deps. |
| `frontend/vite.config.js` | +6 | Vitest config block (jsdom, globals, setup file). |
| `frontend/src/App.jsx` | +7 | Uses `getToken`/`clearTokens` from `api.js` instead of raw `localStorage`. |
| `frontend/src/api.js` | +82 | Token helpers; `ensureRefresh()` single-flight refresh; retry-once on 401; `session-expired` event on final 401. |
| `frontend/src/hooks/useWebSocket.js` | +30 | `tryRefresh()` on close code 4001 before reconnect; `no-permission` status on 4003. |
| `frontend/src/components/auth/LoginPage.jsx` | +7 | Persists `access_token` + `refresh_token` via `setTokens`. |
| `frontend/src/components/editor/EditorBar.jsx` | +11 | Status map adds `saving` / `saved` / `offline` / `error` / `reconnecting` / `no-permission`. |
| `frontend/src/components/editor/EditorPage.jsx` | +150 | Tiptap content state; typing throttle/expiry; offline single-slot queue; reconnect-reconcile via `GET /documents/{id}`; selection state forwarded to AI panel. |
| `frontend/src/components/editor/EditorTextarea.jsx` | +159 | Plain `<textarea>` → Tiptap editor + toolbar (B/I/H1/H2/bullet/ordered/code/undo/redo); `insertAtSelection` / `getSelectedText` imperative handles. |
| `frontend/src/components/editor/sidebar/AIPanel.jsx` | +115 | Side-by-side compare; editable suggestion; `AbortController` cancel; Accept/Edit/Reject → `/resolve`. |
| `frontend/src/components/editor/sidebar/ActiveUsers.jsx` | +12 | Shows "typing…" badge instead of cursor offset. |
| `frontend/src/components/editor/sidebar/Sidebar.jsx` | +11 | Mounts `AIHistoryPanel`; passes `typingUsers` through. |

### Docs

| File | Δ | What changed |
|---|---|---|
| `README.md` | +114 | Authentication, Testing, and WebSocket Protocol sections. |

## New files (22)

### Root

| File | Purpose |
|---|---|
| `.env.example` | All required env vars documented. |
| `DEVIATIONS.md` | Design choices and out-of-scope items. |
| `AI1220 Assignment 2.pdf` | Assignment brief (probably should not be committed). |

### Backend

| File | Purpose |
|---|---|
| `backend/ai/__init__.py` | Package exports (`PROMPTS`, `LLMProvider`, `get_provider`, `truncate_context`). |
| `backend/ai/context.py` | `truncate_context` — 4000-char window centered on selected text. |
| `backend/ai/prompts.py` | 6 prompts (summarize, rewrite, translate, restructure, expand, grammar) + `VALID_ACTIONS`. |
| `backend/ai/providers.py` | `LLMProvider` ABC, `OpenAIProvider`, `NullProvider`, `get_provider()`. |

### Frontend

| File | Purpose |
|---|---|
| `frontend/src/lib/contentCompat.js` | Legacy `{text:""}` ↔ Tiptap doc bridge. |
| `frontend/src/components/editor/sidebar/AIHistoryPanel.jsx` | Paginated AI history. |
| `frontend/tests/setup.js` | Vitest setup (jest-dom extensions). |
| `frontend/tests/LoginPage.test.jsx` | 2 tests. |
| `frontend/tests/AIPanel.test.jsx` | 5 tests. |
| `frontend/tests/EditorBar.test.jsx` | 6 tests. |

### Tests

| File | Purpose |
|---|---|
| `tests/__init__.py` | Marks the tests package. |
| `tests/conftest.py` | SQLite in-memory harness, `get_db` override, `_fresh_schema` autouse, `auth_user` / `doc_factory` / `user_factory` fixtures. |
| `tests/test_auth.py` | Auth + refresh token suite. |
| `tests/test_documents.py` | CRUD on documents. |
| `tests/test_permissions.py` | 4-role ACL matrix. |
| `tests/test_versions.py` | Version save/list/restore. |
| `tests/test_ai.py` | End-to-end AI flow via `NullProvider`. |
| `tests/test_ai_unit.py` | Unit tests for `prompts`/`providers`/`context`. |
| `tests/test_websocket.py` | WS connect/auth/broadcast/typing. |

## Notes

- **Not yet committed.** All changes are unstaged / untracked.
- **54 pytest + 13 vitest** passing; `vite build` clean.
- `AI1220 Assignment 2.pdf` is in the untracked set — you probably do not
  want to commit it. Consider adding `*.pdf` or the specific path to
  `.gitignore`.
