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

**5. Create an `env` or `.env` file** in the project root:
```
DATABASE_URL=postgresql://neondb_owner:npg_NpCsDMbuvW09@ep-raspy-sky-anzefd9q-pooler.c-6.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
JWT_SECRET=supersecretjwtkey2026colabdoc
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
LM_STUDIO_MODEL=local-model

```

Optional AI configuration:
```
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
```

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
