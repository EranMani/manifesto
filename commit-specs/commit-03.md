# Commit 03 — `frontend-scaffold` · Aria

**Phase:** 1A — Infrastructure Foundation
**Assignee:** Aria (Frontend)
**Depends on:** C01 (project-scaffold) — needs the project root to exist
**Parallel with:** C02 (python-skeleton) — zero shared files

---

## What

Initialize the React + Vite + TypeScript + Tailwind frontend. No pages, no components, no API calls.
Goal: `npm run dev` renders a blank white page without errors in the browser console.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `frontend/package.json` | new | Dependencies: react 18, vite, typescript, tailwind, zustand, axios, @tanstack/react-query, react-router-dom |
| `frontend/vite.config.ts` | new | Vite config with proxy: `/api` and `/auth` → `http://localhost:8000` |
| `frontend/tailwind.config.ts` | new | Content paths for `src/**/*.{ts,tsx}` |
| `frontend/tsconfig.json` | new | Strict TypeScript config |
| `frontend/index.html` | new | HTML entry point, `<div id="root">` |
| `frontend/src/main.tsx` | new | ReactDOM.createRoot render |
| `frontend/src/App.tsx` | new | Returns `<div>Manifesto</div>` — routing added in C18 |
| `frontend/src/index.css` | new | Tailwind directives: base, components, utilities |
| `frontend/.env.example` | new | `VITE_API_BASE_URL=http://localhost:8000` |

---

## package.json Key Dependencies

```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.23.0",
    "zustand": "^4.5.0",
    "axios": "^1.7.0",
    "@tanstack/react-query": "^5.40.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

---

## vite.config.ts Proxy

```typescript
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/auth': 'http://localhost:8000',
  }
}
```

---

## Done When

- [ ] `npm install` completes without errors
- [ ] `npm run dev` starts without errors
- [ ] Browser shows blank page with no console errors
- [ ] `npm run build` produces a `dist/` folder

---

## Handoffs Out

→ Aria (C17): `src/` folder structure exists — add `store/`, `api/`, `pages/`, `components/` subdirectories in C17.
→ Aria (C17): Vite proxy configured — `/api` and `/auth` route to backend on port 8000.
