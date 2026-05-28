# Repository Guidelines

## Project Structure

This is a **frontend-backend separated** architecture:

- `frontend/` (root level): Next.js + React + TypeScript app
  - `pages/`: Route entry points (only core pages)
  - `components/`: UI components (retro-futurism minimal style)
  - `hooks/`: Custom React hooks
  - `lib/`: Shared types and utilities
  - `utils/`: Pure helpers
  - `styles/`: Global CSS (dark theme, no animations)
- `backend/`: FastAPI Python service
  - `app/`: FastAPI application
  - `app/routers/`: API endpoints
  - `app/services/`: Business logic (subtitles, AI, cache)

## Build Commands

```bash
# Frontend
cd frontend
npm ci
npm run build      # Production build
npm run dev        # Dev server at http://localhost:3000

# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker
# Backend and Redis:
cd backend && docker compose up -d
# Frontend:
cd frontend && docker compose up -d

## Port Configuration

- Local dev: edit `backend/.env` (`PORT`) and `frontend/.env` (`PORT`, `NEXT_PUBLIC_API_URL`)
- Docker: edit `backend/.env` (`BACKEND_PORT`) and `frontend/.env` (`FRONTEND_PORT`, `NEXT_PUBLIC_API_URL`)
```

## Coding Style

- TypeScript strict mode
- Prettier: `singleQuote: true`, `semi: false`, `trailingComma: all`, `printWidth: 120`
- Components: `PascalCase.tsx`
- Hooks: `useSomething.ts`
- Helpers: `camelCase.ts`

## Design System

**Retro-futurism minimalism:**

- Background: `#0a0a0f`
- Accent cyan: `#00f0ff`
- Accent fuchsia: `#ff00a0`
- Font: JetBrains Mono (monospace)
- No rounded corners, no gradients, no glassmorphism
- No animations except minimal functional transitions

## Key Constraints

- Frontend has **no API routes** — all backend logic is in `backend/`
- Frontend calls `NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`)
- Only core video summarization flow is kept
- All non-core pages, features, and navigation removed
