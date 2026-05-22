# Frontend Architecture Specifications

This document outlines the UI design, component composition, state management, and client-side data pipelines of the MilanoLibrary Next.js Frontend.

---

## 1. Visual & UI Guidelines (Retro-Futurism Minimalism)

MilanoLibrary UI follows a rigorous **retro-futuristic monospace aesthetic** implemented with Tailwind CSS:
- **Fonts**: Monospace (`font-mono`), explicitly importing **JetBrains Mono** inside `pages/_document.tsx`.
- **Borders & Corners**: Strictly square and direct. Absolutely **no rounded corners** (using `rounded-none`).
- **Theme Color Palette**:
  - Background: Blackish-blue (`#0a0a0f`)
  - Accent A (Neon Cyan): `#00f0ff` (used for titles, focus states, success borders)
  - Accent B (Neon Fuchsia): `#ff00a0` (used for buttons hover effects, errors, deleting states)
  - Layout border lines: Slate-700 / Slate-800
- **Animations**: Excluded to preserve a rapid, command-line terminal feeling, except for minimal smooth transitions on state hover changes.

---

## 2. Page & Component Structure

The app operates as a fast, single-page application centered inside a file-system catch-all page router.

```
[[...slug]].tsx (Main Page Controller)
├── Header.tsx                 # Retro banner title (MILANOLIBRARY)
├── UserKeyInput.tsx           # collapsible panel for Custom Key / Endpoint override
├── [Form Input Element]       # URL Input text field or local media DropZone selector
├── SubmitButton.tsx           # Status-aware execution trigger button
├── ModelSelector.tsx          # Local/Online Whisper toggle & Background Downloader controls
├── PromptOptions.tsx          # Summary language, emojis, structured outputs form options
├── SummaryResult.tsx          # Renders Markdown output with marked-react
│   └── Sentence.tsx           # Custom parser converting [MM:SS] to click-to-play media links
└── Footer.tsx                 # Terminal disclaimer copyright block
```

---

## 3. Core Reactive Custom Hooks

Rather than implementing global state frameworks (e.g., Redux or Zustand), state is neatly divided into specialized React Hooks:

### `useSummarize.ts`
Manages the HTTP streaming reader pipeline.
- Receives configuration options, converts camelCase fields to snake_case (`VideoConfig`, `UserConfig`), and sends a `POST` request to `/api/summarize` or `/api/video/upload`.
- Uses `AbortController` to cancel ongoing transfers when reset/re-submitted.
- Implements `getReader()` and `TextDecoder` loop to read chunks sequentially, streaming raw Markdown tokens into the React `summary` state variable on-the-fly.

### `useModelManager.ts`
Interacts with the backend local Whisper downloads database.
- Periodically queries `/api/models/local` to poll installation statuses of various model sizes (`tiny`, `base`, `small`, `medium`, `large-v3`).
- Sends background trigger commands (`POST /api/models/local/{model_name}/download`) and displays responsive loading status percentages.

### `useClearCache.ts`
Sends a `DELETE /api/cache` request to the backend Redis instance, showing success and clearing messages.

---

## 4. Key Client-Side Pipelines & Helper Functions

### 4.1 URL Parsing & Verification
When a video URL is pasted into the input:
- `getVideoIdFromUrl.ts` intercepts it.
- `extractUrl.ts` uses regex to extract the Bilibili BV or YouTube ID, extracting and mapping query params like Multi-page page numbers (`&p=2`).
- The router pushes the path prefix `bilibili.com/video/BV...` to the address bar. This creates shareable links pointing directly to summarized results.

### 4.2 Interactive Subtitle Click-to-Play Timestamps
Inside the summarized Markdown text, timestamps are represented by bracketed notation (e.g. `[01:23]`).
- `marked-react` renders the Markdown content dynamically.
- The `Sentence.tsx` component is registered as a custom element inside the markdown renderer.
- It parses the bracketed timestamps, wrapping them into actionable links.
- Clicking on a timestamp triggers parent scrolling or coordinates action directly to that time frame on Bilibili or YouTube players.
