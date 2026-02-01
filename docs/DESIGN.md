# PantryPal — Design

This document captures the design choices for the POC and how we extend to more vendors and features later.

---

## 1. Scope (POC)

- **Vendors:** Sainsbury's only.
- **Products:** 1–2 to start; watchlist stored in DB.
- **Search:** Prefer fuzzy match (e.g. "Coke" → "Coca-Cola Classic 1L"); fallback to exact name (e.g. "Laila Basmati Rice 10kg").
- **Check frequency:** Once per day to limit load and scraping risk.
- **Alerts:** Price change (POC focus: drops / rollbacks). Delivered via Telegram and/or email; pluggable.
- **Frontend:** Essential — form to add product, list watchlist, show latest price and “alert” state; user can register for daily alerts (email or Telegram).
- **Deployment:** Azure and/or laptop; containerised, K8s-friendly (Rancher Desktop, AKS).

---

## 2. Vendor abstraction (multi-vendor ready)

We treat each retailer as a **vendor adapter** behind a common interface. POC implements Sainsbury's; Tesco, Aldi, etc. plug in later without changing core logic.

### 2.1 Vendor interface (Python)

```text
VendorAdapter (abstract)
├── search(query: str) -> List[ProductMatch]   # e.g. "Laila Basmati Rice 10kg"
├── get_product(url_or_id: str) -> Product     # fetch current price for one product
└── name: str                                  # "sainsburys", "tesco", "aldi"
```

- **ProductMatch:** name, url, current_price, nectar_price (if any), vendor_id.
- **Product:** same plus optional image, description; used for storing in our DB.

Implementations:

- **SainsburysAdapter:** POC only. Fetches Sainsbury's product page (or search result); parses price and Nectar price. Exact or fuzzy match by product name on our side if needed.
- **TescoAdapter / AldiAdapter:** Later; same interface.

Optional later:

- **WebSearchAdapter:** Single “best” result from Google/Bing for a query (e.g. same product elsewhere) — secondary comparison only; primary target remains Sainsbury's for POC.

### 2.2 Where scraping fits

- Sainsbury's has no public price API. POC will use HTTP + HTML parsing (or lightweight browser automation only if necessary).
- Respectful rate: one daily run per product; minimal requests.
- Legal/ToS: accepted as POC/portfolio risk; we can add robots.txt and user-agent checks.

---

## 3. Data model

### 3.1 Core entities (SQLite for POC)

- **vendor**  
  - id, name, slug (e.g. `sainsburys`), base_url, is_active.

- **product**  
  - id, vendor_id, external_id (e.g. Sainsbury's product id/slug), name, url, image_url (optional).  
  - One row per “watched” product per vendor.

- **watchlist**  
  - id, product_id, added_at, created_by (email or telegram_chat_id for POC), alert_on_drop_only (bool, default true).

- **price_history**  
  - id, product_id, price, nectar_price (nullable), recorded_at.  
  - One row per daily check; used to detect change and “previous price”.

- **alert** (optional for POC)  
  - id, watchlist_id, price_history_id, message, sent_at, channel (telegram | email).  
  - Helps avoid duplicate alerts and gives a simple “alert log” in the UI.

### 3.2 POC simplifications

- Single “tenant”: no multi-tenant auth; we can have multiple watchlist rows (different products or same product for different “subscribers”).
- User identity: email and/or Telegram chat ID stored with watchlist; no full auth system for POC.
- Location: not in POC; schema can have optional `location` or `postcode` on watchlist for future “cheapest near me” (petrolprices-style).

---

## 4. Alerts

### 4.1 When to alert

- **Option A (POC):** Alert on any price change (up or down).
- **Option B (recommended for “rollback”):** Alert when price **drops** vs previous recorded price (or vs last N days).
- Configurable per watchlist: `alert_on_drop_only` (true = only drops).

### 4.2 Channels (pluggable)

- **Telegram:** Use your existing Telegram setup (bot token + chat ID). Backend calls Telegram Bot API or your MCP if it exposes “send message”; for simplicity, direct Bot API is easier in a daily job.
- **Email:** SMTP (e.g. SendGrid, Gmail) or Azure Communication Services; one implementation in `alerts/` module.
- **In-app:** Frontend shows “Price dropped” badge and last alert time; no extra infra.

Interface: `AlertChannel.send(subject, body, recipient)` where recipient is email or telegram_chat_id.

### 4.3 Deduplication

- Only send one alert per “price drop event” (e.g. per product per day when price changed).
- Use `alert` table: if we already have an alert for (watchlist_id, price_history_id, channel), skip.

---

## 5. Daily job (scheduler)

- One job runs daily (e.g. 06:00 UK time):  
  1. Load all active watchlist entries and their products.  
  2. For each product, call the appropriate vendor adapter (`get_product`).  
  3. Insert row into `price_history`.  
  4. Compare with previous row; if “price dropped” (and `alert_on_drop_only`), trigger alerts and insert into `alert`.  
- Run in same process as API (APScheduler) or separate worker container; both work with K8s (one deployment or two).

---

## 6. Frontend (POC)

- **Pages:**  
  - Home: short blurb + “Add product” form (product name; optional vendor preselected to Sainsbury's).  
  - Watchlist: table/cards of watched products, latest price, previous price, “Alert sent” indicator.  
  - Optional: “Alert signup” — user enters email or Telegram ID and selects which products to get alerts for (or “all my watchlist”).
- **Stack:** Keep it simple: Jinja templates + HTMX, or a small React/Vue SPA; backend exposes REST (e.g. `GET /products`, `POST /watchlist`, `GET /price-history?product_id=…`).
- **Showcase:** Presentable enough for LinkedIn and team; mobile-friendly is a plus.

---

## 7. Optional: secondary “web search” result

- After we have Sainsbury's price, optionally call a search API (Google/Bing) for the same product name and show “One more option: [link]” on the product detail or in the alert.  
- POC can skip this; add as a second phase so we stay Sainsbury’s-only for the first release.

---

## 8. Deployment (Azure + laptop, vendor-agnostic)

- **Containers:** Backend (API + scheduler) in one image; optional separate worker image later.
- **Orchestration:**  
  - Docker Compose for local/laptop.  
  - K8s manifests (deploy/, e.g. Deployment + Service + CronJob or in-process scheduler) for Rancher Desktop and AKS.
- **Secrets:** Telegram token, SMTP credentials, optional API keys in env or K8s Secrets; no hardcoding.
- **Storage:** SQLite file in a volume for POC; path configurable so we can switch to Postgres later (same schema).

---

## 9. Future extensions (out of POC)

- More vendors: Tesco, Aldi — new adapter, same interface.
- Location: postcode/location on watchlist; “cheapest near me” view (petrolprices-style).
- More products and users: auth, multi-tenant DB.
- Secondary web search: one Google/Bing result per product for comparison.
- MCP: optional MCP server that uses the same backend (e.g. “check price for X”) for Cursor/agents.

---

## 10. Summary table

| Concern           | POC choice                          | Later |
|------------------|--------------------------------------|-------|
| Vendors          | Sainsbury's only                     | Tesco, Aldi, web search |
| Products         | 1–2, watchlist                      | Many, multi-user       |
| Search           | Fuzzy preferred, exact OK           | Same + search API      |
| Frequency        | Daily                               | Configurable           |
| Alerts           | Telegram + email, drop-only option  | More channels          |
| Frontend         | Form + watchlist + alerts           | Auth, location         |
| Deployment       | Docker, K8s (Azure + laptop)        | Same, scale            |
| Storage          | SQLite                              | Postgres optional      |

This design keeps the POC simple while making it straightforward to add vendors (Tesco, Aldi), location, and a petrolprices-like “best price” experience later.
