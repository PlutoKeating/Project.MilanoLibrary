# Frontend Architecture Specifications

This document details the UI design principles, page layout routing, component composition, and state orchestration of the MilanoLibrary Next.js Frontend.

---

## 1. Visual & UI Guidelines (Retro-Futurism Minimalism)

MilanoLibrary's frontend strictly follows a **retro-futuristic, monospace, command-line aesthetic**:
- **Typography**: Strict monospace layout (`font-mono`) powered by **JetBrains Mono** loaded globally.
- **Borders & Shapes**: Strictly straight and sharp. No rounded corners (`rounded-none`), no gradients, and no translucent glassmorphism.
- **Color Palette**:
  - Background: Obsidian Space-Black (`#0a0a0f`)
  - Accent A (Neon Cyan): `#00f0ff` (focus borders, success badges, main titles)
  - Accent B (Neon Fuchsia): `#ff00a0` (hover styles, errors, deleting indicators)
  - Structuring Lines: Dark slate (`#1e293b` / `#0f172a`)
- **Transitions**: Flat and instant to retain the snappy, immediate feeling of a hardware hacker terminal.

---

## 2. Catch-all Routing & Page Structure

The application operates as a single-page app utilizing the Next.js **Pages Router** catch-all structure (`pages/[[...slug]].tsx`). 

### UI Component Tree Structure
```
[[...slug]].tsx (Main Shell Page Controller)
├── Header.tsx                 # Branding Title (MILANO LIBRARY)
├── FileExplorer.tsx           # Navigates & dynamically selects Root Book Vault directory
├── UserKeyInput.tsx           # Dropdown panel managing OpenAI endpoints & API Keys
├── [3 Main Workspaces] (Tab Navigation)
│   ├── [1. LIBRARY Tab]
│   │   ├── [Shelf Grid View] (Lists MilanoBooks, with "NEW VAULT" trigger card)
│   │   └── [Book Detail Terminal View] (Visible when reading a MilanoBook)
│   │       ├── PipelineProcessor.tsx# Controls re-processing & uploads
│   │       ├── TimelineProgress.tsx # Listens to real-time step percentage & log messages
│   │       ├── Video/Audio Player   # Embedded local HTML5 player
│   │       ├── [Outline Sidebar]    # Tree index showing custom-numbered headings
│   │       └── SummaryResult.tsx    # Renders complete.md using ReactMarkdown + Math + LaTeX
│   │           └── Sentence.tsx     # Parsed interactive [MM:SS] clickable links
│   │
│   ├── [2. AGGREGATOR Tab]
│   │   ├── Book Selection Checkboxes (Source MilanoBooks)
│   │   ├── Integration Instruction Directive Textarea
│   │   └── Compile Collective Note Trigger Button
│   │
│   └── [3. STUDY NOTES Tab]
│       ├── Notes Directory Sidebar (Reads .notes/ folder files)
│       └── Custom Markdown Notes Reader & Copy Action
└── Footer.tsx                 # Monospaced trademark footer
```

---

## 3. Core Reactive Custom Hooks

Rather than using heavy global state libraries (like Redux or Zustand), reactive states are elegantly partitioned into decoupled custom hooks:

### `useSummarize.ts`
Manages pipeline trigger HTTP requests.
- Accepts forms config values, serializes React Hook Form payloads into backend Pydantic models, and posts requests.
- Leverages `AbortController` to cancel connections on-demand.
- Connects state machines to backend-driven workflows.

### `useModelManager.ts`
Interacts with the local Whisper weights manager.
- Queries `/api/models/local` periodically to poll model installation states (`tiny`, `base`, `small`, `medium`, `large-v3`).
- Sends `POST /api/models/local/{model_name}/download` to start background downloading, polling percentages dynamically.

### `useClearCache.ts`
Triggers `DELETE /api/cache` requests on-demand to wipe the backend Redis server.

### `useLocalStorage.ts`
Provides reactive bindings to the browser's `localStorage` keeping UI configurations persistent across page reloads.

---

## 4. Key Client-side Pipelines & Interactions

### 4.1 Root Vault Dynamic Selection
Using `FileExplorer`, users browse the host computer's directories dynamically. When a path is selected:
1. The frontend posts the selection to `/api/books/settings/root`.
2. The backend validates and updates the active vault path.
3. The frontend clears old details, fetches books, and re-renders the books shelf instantly.

### 4.2 Science-Grade Markdown Rendering
To properly showcase highly detailed leaf node technical guides:
- `ReactMarkdown` is loaded alongside `remark-gfm` (standard markdown tables), `remark-math` (LaTeX mathematical structures), and `rehype-katex` (HTML LaTeX compiler).
- Pre-defined, lightweight CSS rules (`markdown.css`) style technical sections, blockquotes, inline backticks, and lists.

### 4.3 Interactive click-to-play [MM:SS] Timestamps
Timestamps inside summary markdown files are formatted as brackets (e.g., `[02:30]`).
- The parser wraps bracketed timestamps inside a custom `<Sentence />` node.
- Clicking a timestamp extracts the time in seconds.
- It triggers a seek action `currentTime` on the local HTML5 `<video>` player, or links to precise timestamp endpoints on online media pages.
- Standard headings automatically generate anchor-scroll IDs on the fly, allowing clicking the monospaced tree-outline sidebar to jump smoothly to any chapter inside the Markdown document.
