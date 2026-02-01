# Frontend

**For the POC, the UI lives in the backend.** There are no source files in this folder.

- The web interface is **server-rendered** by FastAPI using **Jinja2** templates.
- Templates: `backend/app/templates/` — `base.html`, `index.html`.
- That gives you: Add product form, watchlist table, Set price, Run price check now, Remove.

So the “frontend” for PantryPal POC is part of the backend app; no separate frontend build or repo is required.

---

If you later want a separate SPA (e.g. React or Vue), you could build it here and have the backend serve the built static files. For now, the Jinja UI is enough.
