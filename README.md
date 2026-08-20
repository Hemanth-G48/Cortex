# Student Life OS (Cortex)

A productivity application that helps students manage their academic and personal life in one place. It pairs a **FastAPI** backend with a **React + TypeScript + Vite** frontend, and is built around a powerful **Second Brain** — a local-first knowledge base that ingests notes, documents, and course materials, embeds them offline with fastembed, and makes them searchable through semantic (vector) search, a knowledge graph, and AI tutoring. Think of it as a personal study companion that remembers everything you feed it and helps you connect ideas, revise, and learn.

## Features

- **Courses & Timetable** — track courses, schedules, and academic calendars.
- **Task & Life Management** — tasks, reminders, Eisenhower matrix, daily logs, and goal tracking.
- **Pomodoro Timer** — focus sessions with progress rings and settings.
- **RPG System** — quests, missions, and rewards to gamify productivity.
- **Second Brain / Vault** — a local-first knowledge base: ingest Markdown notes, PDFs, and course docs, embed them **offline** with fastembed (BAAI/bge-small-en-v1.5, 384-dim, no GPU/API required), then search them semantically via a vector store. Includes a knowledge graph (concepts, links, mindmaps), an Obsidian vault integration, AI tutoring, spaced-repetition flashcards, and weekly review/reflection workflows.
- **Visualizations** — radar charts and dashboards for life areas and academic performance.

## Architecture

```
productivity_app/
├── backend/          # FastAPI app (uvicorn :8000)
│   ├── app/
│   │   ├── routers/  # API route modules
│   │   ├── services/ # Business logic (embeddings, search, …)
│   │   ├── models/   # SQLAlchemy models
│   │   └── schemas/  # Pydantic schemas
│   ├── scripts/
│   └── requirements.txt
├── frontend/         # React 19 + TS + Vite (:5173)
├── second_brain/     # Knowledge base / Obsidian vault
├── screenshots/      # UI screenshots (see below)
└── start.sh          # One-command dev startup
```

## Getting Started

```bash
# Install deps and start both servers (backend :8000, frontend :5173)
./start.sh --install

# Or just start (if already installed)
./start.sh
```

Open the app at <http://localhost:5173>. The frontend proxies `/api` to the backend at <http://localhost:8000>.

### Useful flags

```bash
./start.sh --no-reload   # backend without auto-reload
./start.sh --host 0.0.0.0 # expose to the LAN (default is loopback)
./start.sh --no-open     # don't auto-open the browser
```

### Manual setup

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # then fill in values
uvicorn app.main:app --reload --port 8000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

## Second Brain

The Second Brain is the core intelligence layer of Student Life OS. It turns scattered notes and study materials into a connected, queryable knowledge system.

**Ingestion & Embeddings**
- Drop in Markdown notes, PDFs, and course documents (see `second_brain/notes/` and the Obsidian vault).
- Files are chunked and embedded **locally and offline** using `fastembed` with the `BAAI/bge-small-en-v1.5` model (384-dim vectors), so no cloud API or GPU is required.
- Embeddings are stored in a vector store (`backend/app/services/vector_store*.py`) for fast similarity search.

**Retrieval & Reasoning**
- **Semantic search** (`kb_search.py`) returns the most relevant chunks for any query.
- A **knowledge graph** (`kb_graph.py`, `kb_concepts.py`, `kb_links.py`, `kb_mindmap.py`) links concepts, subjects, and sources so you can navigate ideas spatially instead of linearly.
- **AI tutoring & study aids** (`kb_tutor.py`, `kb_study.py`, `kb_practice.py`, `flashcard_srs.py`) generate explanations, quizzes, and spaced-repetition flashcards from your own notes.

**Organization & Maintenance**
- Auto-categorization, tagging, de-duplication, citation tracking, and subject detection keep the vault tidy.
- Health audits, re-indexing jobs, and weekly review/reflection workflows (`kb_weekly_review.py`, `kb_reflections.py`, `kb_health.py`) surface what to revisit.
- Optional Obsidian automation (`second_brain/gemini-obsidian.sh`) bridges the in-app vault with an external Obsidian vault.

## Screenshots

![Dashboard](screenshots/Screenshot_2026-08-20_13-06-29.jpg)

![Courses & Timetable](screenshots/Screenshot_2026-08-20_13-09-16.jpg)

![Life Planner](screenshots/Screenshot_2026-08-20_13-09-50.jpg)

![Task & Pomodoro](screenshots/Screenshot_2026-08-20_13-10-12.jpg)

![RPG & Visualizations](screenshots/Screenshot_2026-08-20_13-10-33.jpg)

## Tech Stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic, fastembed (local ONNX embeddings)
- **Frontend:** React 19, TypeScript, Vite, Vitest
- **Knowledge base:** Local embeddings + Obsidian vault integration

## License

See repository for license details.
