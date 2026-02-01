"""
PantryPal API and web UI. Serves REST, Jinja pages, and runs daily price-check job.
"""
import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db.database import init_db, get_connection
from app.db import crud
from app.api.watchlist import router as watchlist_router
from app.jobs.price_check import run_daily_price_check

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pantrypal")

app = FastAPI(
    title="PantryPal",
    description="Price watch for groceries — get alerted when prices drop.",
    version="0.1.0",
)

templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Serve images from PantryPal/images (repo root)
_images_dir = Path(__file__).resolve().parent.parent.parent / "images"
if _images_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_images_dir)), name="static")


def schedule_daily_job():
    """Run price check daily (e.g. 06:00 UK)."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_price_check, "cron", hour=6, minute=0, id="daily_price_check")
    scheduler.start()
    logger.info("Scheduled daily price check at 06:00")


@app.on_event("startup")
async def startup():
    await init_db()
    schedule_daily_job()


app.include_router(watchlist_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "pantrypal"}


@app.post("/api/jobs/run-now")
async def run_price_check_now():
    """Trigger the daily price check job now (for testing)."""
    await run_daily_price_check()
    return {"ok": True, "message": "Price check completed"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    await init_db()
    db = await get_connection()
    try:
        items = await crud.get_watchlist_entries(db)
    finally:
        await db.close()
    return templates.TemplateResponse("index.html", {"request": request, "items": items})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
