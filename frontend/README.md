# Frontend

Simple UI for PantryPal POC:

- **Add product** form (product name; vendor = Sainsbury's for POC).
- **Watchlist** — list of watched products with latest price and “alert” state.
- **Alert signup** — user enters email or Telegram ID to receive daily alerts.

Options for implementation:

- **Jinja + HTMX:** Served by FastAPI; minimal JS.
- **React / Vue SPA:** Separate build; backend serves static files and exposes REST.

Choose one for POC; keep it minimal for showcase (LinkedIn, team).
