"""
Daily price check job: fetch prices for all watchlist products, record history, send alerts on drop.
"""
import logging
from datetime import datetime

from app.db.database import get_db_path, init_db
from app.db import crud
from app.vendors.sainsburys import SainsburysAdapter
from app.alerts.channels import get_telegram_channel, get_email_channel

logger = logging.getLogger("pantrypal.job")


async def run_daily_price_check() -> None:
    import aiosqlite

    await init_db()
    db = await aiosqlite.connect(get_db_path())
    db.row_factory = aiosqlite.Row
    try:
        entries = await crud.get_watchlist_for_job(db)
        sainsburys = SainsburysAdapter()
        telegram = get_telegram_channel()
        email_ch = get_email_channel()

        for entry in entries:
            vendor_slug = entry["vendor_slug"]
            product_id = entry["product_id"]
            watchlist_id = entry["watchlist_id"]
            url = entry["url"]
            name = entry["name"]
            alert_on_drop_only = bool(entry["alert_on_drop_only"])
            alert_email = (entry["alert_email"] or "").strip()
            alert_telegram = (entry["alert_telegram_chat_id"] or "").strip()

            adapter = sainsburys if vendor_slug == "sainsburys" else None
            if not adapter:
                continue

            try:
                product = await adapter.get_product(url)
            except Exception as e:
                logger.warning("Failed to fetch %s: %s", url, e)
                continue

            if not product or product.current_price is None:
                continue

            ph_id = await crud.insert_price_history(
                db, product_id, product.current_price, product.nectar_price
            )
            prev = await crud.get_previous_price(db, product_id)
            if prev is None:
                continue
            prev_price, _ = prev
            current_price = product.current_price
            dropped = current_price < prev_price
            if not dropped and alert_on_drop_only:
                continue
            if dropped and alert_on_drop_only:
                subject = "PantryPal: Price drop"
                body = f"{name}\nPrevious: £{prev_price:.2f} → Now: £{current_price:.2f}\n{url}"
            else:
                subject = "PantryPal: Price change"
                body = f"{name}\nPrevious: £{prev_price:.2f} → Now: £{current_price:.2f}\n{url}"

            if alert_telegram:
                if not await crud.alert_exists_for(db, watchlist_id, ph_id, "telegram"):
                    if await telegram.send(subject, body, alert_telegram):
                        await crud.insert_alert(db, watchlist_id, ph_id, body, "telegram")
            if alert_email:
                if not await crud.alert_exists_for(db, watchlist_id, ph_id, "email"):
                    if await email_ch.send(subject, body, alert_email):
                        await crud.insert_alert(db, watchlist_id, ph_id, body, "email")
    finally:
        await db.close()
