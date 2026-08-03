# SyllabusAI

A study platform that uses AI to generate quizzes and summaries from your uploaded course materials. Upload your PDFs, slides, or docs, organize them by institution, course, and semester, and let AI do the heavy lifting for exam prep.

## Features

- **AI Quiz Generation** - Generate quizzes from uploaded materials with configurable difficulty levels
- **AI Summaries** - Get concise summaries of your study materials (cached for fast access)
- **Material Upload** - Supports PDF, PPT, and DOC files
- **Organization** - Structure content by institution, course, semester, subject, and unit
- **Quiz History & Analytics** - Track your performance over time
- **Auth** - Google OAuth and email/password authentication
- **Admin Dashboard** - Manage institutions, courses, and content
- **Browse Mode** - Explore available courses and materials without signing up

## Tech Stack

**Frontend** (`/client`)
- React 19, TypeScript, Vite
- Tailwind CSS v4, Framer Motion
- React Router v7, Axios
- Firebase SDK (auth)

**Backend** (`/server`)
- Node.js, Express, TypeScript
- PostgreSQL with Sequelize ORM
- JWT auth + Firebase Admin
- Groq SDK for AI generation
- pdf-parse, Multer for file handling

## Getting Started

### Prerequisites

- Node.js >= 18
- PostgreSQL
- Firebase project (for auth)
- Groq API key

### Server

```bash
cd server
npm install
```

Set up your `.env` with database credentials, JWT secret, Firebase config, and Groq API key.

```bash
npm run dev
```

### Client

```bash
cd client
npm install
```

Add your Firebase config to the client `.env`.

```bash
npm run dev
```

The client runs on `http://localhost:5173` and the server on `http://localhost:5000` by default.

## Project Structure

```
SyllabusAi/
├── client/          # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── ...
│   └── package.json
├── server/          # Express backend
│   ├── src/
│   │   ├── controllers/
│   │   ├── models/       # User, Institution, Course, Subject, Unit, Material, Quiz, QuizAttempt, Summary
│   │   ├── routes/
│   │   ├── middlewares/
│   │   └── ...
│   └── package.json
└── README.md
```
