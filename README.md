# PantryPal

**Price watch for groceries — get alerted when prices drop (e.g. rollbacks) at Sainsbury's and, later, other retailers.**

![Alt text](./images/PantryPal.jpeg "Azura - The Guardian of Pipelines")

Showcase project: [kingalok.github.io/agentic-projects](https://kingalok.github.io/agentic-projects/)

---

## Goals

- **POC:** Watch 1–2 products at **Sainsbury's**; daily check; alert on price change (especially rollbacks).
- **Showcase:** Simple web frontend (form to add products, view watchlist and alerts) for team and LinkedIn.
- **Extensible:** Same pattern for Tesco, Aldi, etc. — long-term vision similar to [petrolprices.com](https://www.petrolprices.com/) but for groceries (location optional later).
- **Deploy:** Run on Azure (e.g. AKS) and/or laptop (e.g. Rancher Desktop); vendor-agnostic (Python, containerised, K8s-friendly).

## What PantryPal Does (POC)

1. User adds a product (e.g. **"Laila Basmati Rice 10kg"** or exact name).
2. System finds it on Sainsbury's (fuzzy match if feasible; otherwise exact).
3. Daily job records price (and Nectar price if available).
4. On price change (e.g. drop from £19 → £12), user gets an alert (Telegram and/or email).
5. Frontend shows watchlist and latest prices; optional simple “best deal” view.

## Tech Summary (POC)

| Area        | Choice / direction |
|------------|---------------------|
| Backend    | Python (FastAPI)    |
| Storage    | SQLite (POC); schema ready for Postgres later |
| Scheduler  | Daily run (APScheduler or cron in container) |
| Alerts     | Pluggable: Telegram (you have MCP/bot), email |
| Frontend   | Simple form + watchlist + alerts (e.g. Jinja + HTMX or small React) |
| Vendors    | Abstract interface; Sainsbury's first |
| Deployment | Docker; K8s manifests for Rancher Desktop / AKS |

## Repo Layout

```
PantryPal/
├── README.md
├── docs/
│   └── DESIGN.md          # Detailed design (vendors, data model, alerts)
├── backend/               # Python API + jobs
│   ├── app/
│   │   ├── vendors/       # base + Sainsbury's; Tesco, Aldi later
│   │   ├── alerts/        # Telegram, email
│   │   ├── jobs/          # Daily price check
│   │   ├── api/           # REST for frontend
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/              # Simple UI for form + watchlist (see frontend/README.md)
├── deploy/                # K8s / Docker Compose (Azure + laptop)
└── docker-compose.yml     # Local run
```

## Running Locally (After Implementation)

- Backend + scheduler + SQLite in one container (or two: API + worker).
- Frontend served by backend or separate static build.
- `docker-compose up` or `kubectl apply` for K8s.

## Design Details

See **[docs/DESIGN.md](docs/DESIGN.md)** for:

- Vendor abstraction (add Tesco/Aldi later)
- Data model (products, watchlist, price history)
- Alert channels (Telegram, email)
- Optional: secondary “one result from Google/Bing” for comparison
- Future: location for “cheapest near me” (petrolprices-style)

---

*POC scope: Sainsbury's only, 1–2 products, daily check, simple frontend, extensible for more vendors and features.*
