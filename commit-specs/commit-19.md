# Commit 19 — `placeholder-pages` · Aria

**Phase:** 1F — Frontend Core
**Assignee:** Aria (Frontend)
**Depends on:** C18 (protected-route)

---

## context

```
tier0:
  - .claude/agents/aria.md (Current State header only — first 50 lines)

tier1:
  - frontend/src/App.tsx    # to update imports from inline stubs to real page files

tier2: []   # all 6 page files are new

forbidden:
  - backend/
  - frontend/src/store/     # do not touch state layer
  - frontend/src/api/       # do not touch API layer
  - frontend/src/components/

estimated_reads: 1
estimated_edits: 7   # 6 page files (new) + App.tsx (update imports)
fits_single_agent: true
```

---

## What

Create all placeholder pages. Each renders the page title and "Coming soon" text.
Routing works end-to-end — navigating to each route shows its placeholder.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `frontend/src/pages/Dashboard.tsx` | new | "Dashboard — Coming soon" |
| `frontend/src/pages/VendorList.tsx` | new | "Vendors — Coming soon" |
| `frontend/src/pages/VendorDetail.tsx` | new | "Vendor Detail — Coming soon" |
| `frontend/src/pages/ChatPolicy.tsx` | new | "Policy Chat — Coming soon" |
| `frontend/src/pages/ChatLogistics.tsx` | new | "Logistics Chat — Coming soon" |
| `frontend/src/pages/Admin.tsx` | new | "Admin — Coming soon" |

---

## Page Template

Each page is minimal:

```tsx
export default function Dashboard() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-gray-500 mt-2">Coming soon</p>
    </div>
  )
}
```

---

## Files to Modify

| File | Change |
|---|---|
| `frontend/src/App.tsx` | Replace inline stub components with real imports from pages/ |

---

## Done When

- [ ] All 6 page files exist and render without errors
- [ ] Navigating to each route shows the correct placeholder content
- [ ] No TypeScript errors (`npm run build` passes)

**Viktor + Mira wave runs on this commit (C20 is next, so C20 triggers the wave — but Mira runs here since this introduces user-facing pages).**

Actually: Viktor runs at C20 (the 20th commit). Mira runs on this commit since it introduces user-facing pages.
