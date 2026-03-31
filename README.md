# ColabDoc

A collaborative document editor with real-time co-editing, user authentication, and permission management.

## Requirements

- Python 3.12+
- pip

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/blackeyh/colabdoc
cd colabdoc
```

**2. Install dependencies**
```bash
pip install -r backend/requirements.txt
```

**3. Create the `env` file** in the project root with the following:
```
DATABASE_URL=postgresql://neondb_owner:npg_NpCsDMbuvW09@ep-raspy-sky-anzefd9q-pooler.c-6.us-east-1.aws.neon.tech/neondb?channel_binding=require&sslmode=require
JWT_SECRET=supersecretjwtkey2026colabdoc
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

**4. Run the server**
```bash
./start.sh
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

## Features

- Sign up / log in
- Create and manage documents
- Add collaborators by searching their name or email
- Set permissions: Editor, Commenter, Viewer
- Real-time collaborative editing via WebSockets
- Version history with restore

## Project Structure

```
backend/          FastAPI backend
  main.py         App entry point + WebSocket handler
  models.py       Database models
  auth.py         JWT authentication
  routers/        API route handlers (auth, documents, permissions, versions)
frontend/
  index.html      Single-page frontend (vanilla JS)
env               Environment variables (do not commit)
start.sh          Server startup script
```

## API Docs

Available at [http://localhost:8000/docs](http://localhost:8000/docs) when running locally.
