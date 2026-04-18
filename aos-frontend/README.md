# AOS Frontend

React + TypeScript + Vite + Tailwind CSS + shadcn-style primitives.

## Getting started

```bash
npm install
npm run dev
```

Dev server runs on http://localhost:5173 and proxies `/api` to the
FastAPI backend on http://localhost:8000.

## Environment

Set `VITE_API_URL` to override the default `/api/v1` base path, e.g.
for a hosted backend.

## Structure

- `src/pages` — top-level route components (Chat, Dashboard, Finance, …)
- `src/components/ui` — primitive UI (Button, Card, Input)
- `src/components/layout` — AppLayout, Sidebar, Topbar
- `src/lib/api.ts` — typed API client for the AOS backend
- `src/store/auth.ts` — Zustand auth store with persistence
- `src/styles/globals.css` — Tailwind + CSS variable theme tokens
