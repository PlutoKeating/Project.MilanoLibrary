# Frontend Quick Start Guide

This guide walks you through the steps to get the Next.js React frontend up and running for local development or production deployment.

---

## 1. Prerequisites

Before installing the dependencies, make sure your host system has:
- **Node.js**: Recommended version **20.x** (LTS) or higher (Minimum version is 18.x).
- **NPM** or **Yarn**: Recommended to stick with `npm` as a package-lock.json is supplied.
- **FastAPI Backend**: Ensure you have a running backend server at `http://localhost:8000` (locally or via Docker Compose) to handle client requests.

---

## 2. Setup & Configuration

1. Navigate to the frontend directory:
   ```bash
   cd MilanoLibrary-v1/frontend
   ```

2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

3. Open `.env` and set your variables:
   - **`NEXT_PUBLIC_API_URL`**: Point this to your backend FastAPI server. The default is `http://localhost:8000`.
   - **`FRONTEND_PORT`**: Custom port for the Next.js dev server (defaults to `3000`).

---

## 3. Installation

Install node packages using strict-install mode to align with the lockfile:

```bash
npm ci
```

---

## 4. Development Execution

Launch the Next.js development server with hot-module-replacement (HMR):

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser. Any edits you make in the code will be immediately reflected on the screen.

---

## 5. Production Build & Run

To build the optimized static production-ready bundles and start the web server:

```bash
# Build static assets & compile typescript
npm run build

# Start the production Next.js runner
npm run start
```

---

## 6. Architecture & Framework Notes

### Pages Router Catch-All
MilanoLibrary uses Next.js **Pages Router** with a catch-all catch slug structure `pages/[[...slug]].tsx`. This allows the front-end to intercept shared URLs in the address bar (e.g. `http://localhost:3000/bilibili.com/video/BV...` or `http://localhost:3000/youtube.com/watch?v=...`) and automatically trigger summarization immediately on page load.

### Form State Persistence
User choices such as custom OpenAI endpoints, API keys, models, language outputs, and timestamp options are automatically saved to `localStorage` using `react-hook-form-persist`. When a user reloads the tab, all configurations are immediately restored.
