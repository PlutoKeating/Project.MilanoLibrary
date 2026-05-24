# Frontend Quick Start Guide

This guide walks you through setting up and running the Next.js/React frontend for development or production.

---

## 1. Prerequisites

Before installing, ensure your host environment has:
- **Node.js**: Recommended version **20.x** (LTS) or higher (Minimum version is 18.x).
- **NPM**: Package manager (a `package-lock.json` file is supplied for version locking).
- **FastAPI Backend**: A running MilanoLibrary backend at `http://localhost:8000` (locally or via Docker Compose).

---

## 2. Setup & Configuration

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```

3. Open `.env` and set:
   - **`NEXT_PUBLIC_API_URL`**: Point this to your backend FastAPI server. The default is `http://localhost:8000`.
   - **`FRONTEND_PORT`**: Port for the Next.js development server (default is `3000`).

---

## 3. Installation

Install all node packages using strict-install mode to align with the lockfile:
```bash
npm ci
```

---

## 4. Development Execution

Launch the Next.js development server with hot-module-replacement (HMR):
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser. Any edits in the source code will immediately reflect on the screen.

---

## 5. Production Build & Deployment

To build optimized production-ready bundles and start the server:
```bash
# Build static assets & compile TypeScript
npm run build

# Start the production runner
npm run start
```

---

## 6. Functional Guide & Main Panels

### A. Dynamic Root Vault Mount (FileExplorer)
MilanoLibrary operates in a database-less model. The frontend provides a **BROWSE...** button at the top that opens a custom-built file directory explorer. You can navigate the host's physical files and directories. Clicking on a folder selects it as your active book vault. All books and notes inside it are dynamically loaded.

### B. The Library Console & Re-Processing
- Clicking **[ NEW VAULT ]** launches a pipeline processor terminal.
- Paste an online video URL or drag-and-drop local video/audio files into the upload dropzone.
- Configure prompt choices (Language, Emoji, Structured Outputs).
- Click **EXECUTE SUMMARY** to start the compiler. The UI automatically displays the progress of all steps.
- For an existing book, click **[RE-PROCESS / 覆盖重新加工]** to re-run the pipeline with new parameters, or click **[RE-COMPILE / 重新编译大纲]** to rebuild `complete.md` from the cached leaf segment files.

### C. Multi-Book Aggregator
- Switch to the **[AGGREGATOR // 多书整合]** tab.
- Select multiple compiled books via checkboxes.
- Input custom prompts to outline and synthesize connections across chosen domains.
- Click Compile to let the LLM generate a comprehensive study guide stored under the active vault's `.notes/` sub-folder.

### D. Study Notes Reader
- Switch to the **[STUDY NOTES // 智能笔记]** tab.
- Click any generated note in the sidebar to read it.
- Markdown, standard LaTeX formulas, and syntax-highlighted code blocks are fully rendered.
- Click **[COPY MARKDOWN]** to instantly copy the raw markdown content to your clipboard.
