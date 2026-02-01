"""
CRUD for vendor, product, watchlist, price_history, alert.
"""
from datetime import datetime
from typing import Optional

import aiosqlite

SAINSBURYS_VENDOR_ID = 1


async def get_vendor_by_slug(db: aiosqlite.Connection, slug: str) -> Optional[dict]:
    row = await db.execute(
        "SELECT id, name, slug, base_url, is_active FROM vendor WHERE slug = ?", (slug,)
    )
    r = await row.fetchone()
    return dict(r) if r else None


async def get_product_by_id(db: aiosqlite.Connection, product_id: int) -> Optional[dict]:
    row = await db.execute(
        """SELECT p.id, p.vendor_id, p.external_id, p.name, p.url, p.image_url, v.slug as vendor_slug
           FROM product p JOIN vendor v ON p.vendor_id = v.id WHERE p.id = ?""",
        (product_id,),
    )
    r = await row.fetchone()
    return dict(r) if r else None


async def get_product_by_vendor_and_external(
    db: aiosqlite.Connection, vendor_id: int, external_id: str
) -> Optional[dict]:
    row = await db.execute(
        "SELECT id, vendor_id, external_id, name, url, image_url FROM product WHERE vendor_id = ? AND external_id = ?",
        (vendor_id, external_id),
    )
    r = await row.fetchone()
    return dict(r) if r else None


async def upsert_product(
    db: aiosqlite.Connection,
    vendor_id: int,
    external_id: str,
    name: str,
    url: str,
    image_url: Optional[str] = None,
) -> int:
    """Insert or update product; return product id."""
    await db.execute(
        """INSERT INTO product (vendor_id, external_id, name, url, image_url)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(vendor_id, external_id) DO UPDATE SET name = ?, url = ?, image_url = ?""",
        (vendor_id, external_id, name, url, image_url or "", name, url, image_url or ""),
    )
    await db.commit()
    row = await db.execute(
        "SELECT id FROM product WHERE vendor_id = ? AND external_id = ?",
        (vendor_id, external_id),
    )
    r = await row.fetchone()
    return r["id"]


async def add_to_watchlist(
    db: aiosqlite.Connection,
    product_id: int,
    alert_email: Optional[str] = None,
    alert_telegram_chat_id: Optional[str] = None,
    alert_on_drop_only: bool = True,
) -> int:
    """Add product to watchlist. Returns watchlist id."""
    cur = await db.execute(
        """INSERT INTO watchlist (product_id, alert_email, alert_telegram_chat_id, alert_on_drop_only)
           VALUES (?, ?, ?, ?)""",
        (product_id, alert_email or "", alert_telegram_chat_id or "", 1 if alert_on_drop_only else 0),
    )
    await db.commit()
    return cur.lastrowid


async def get_watchlist_entries(db: aiosqlite.Connection) -> list[dict]:
    """All watchlist rows with product and latest price."""
    rows = await db.execute(
        """SELECT w.id as watchlist_id, w.product_id, w.alert_email, w.alert_telegram_chat_id, w.alert_on_drop_only, w.added_at,
                  p.name as product_name, p.url as product_url, p.external_id, v.slug as vendor_slug,
                  (SELECT price FROM price_history WHERE product_id = p.id ORDER BY recorded_at DESC LIMIT 1) as latest_price,
                  (SELECT nectar_price FROM price_history WHERE product_id = p.id ORDER BY recorded_at DESC LIMIT 1) as latest_nectar_price,
                  (SELECT recorded_at FROM price_history WHERE product_id = p.id ORDER BY recorded_at DESC LIMIT 1) as latest_recorded_at,
                  (SELECT price FROM price_history WHERE product_id = p.id ORDER BY recorded_at DESC LIMIT 1 OFFSET 1) as previous_price
           FROM watchlist w
           JOIN product p ON w.product_id = p.id
           JOIN vendor v ON p.vendor_id = v.id
           ORDER BY w.added_at DESC"""
    )
    return [dict(r) for r in await rows.fetchall()]


async def get_watchlist_for_job(db: aiosqlite.Connection) -> list[dict]:
    """Watchlist with product url and vendor slug for daily job."""
    rows = await db.execute(
        """SELECT w.id as watchlist_id, w.product_id, w.alert_on_drop_only, w.alert_email, w.alert_telegram_chat_id,
                  p.url, p.name, v.slug as vendor_slug
           FROM watchlist w JOIN product p ON w.product_id = p.id JOIN vendor v ON p.vendor_id = v.id"""
    )
    return [dict(r) for r in await rows.fetchall()]


async def insert_price_history(
    db: aiosqlite.Connection, product_id: int, price: Optional[float], nectar_price: Optional[float] = None
) -> int:
    await db.execute(
        "INSERT INTO price_history (product_id, price, nectar_price) VALUES (?, ?, ?)",
        (product_id, price, nectar_price),
    )
    await db.commit()
    row = await db.execute("SELECT last_insert_rowid() AS id")
    r = await row.fetchone()
    return r["id"] if r else 0


async def get_previous_price(db: aiosqlite.Connection, product_id: int) -> Optional[tuple[float, float]]:
    """Return (price, nectar_price) of the previous record, or None."""
    row = await db.execute(
        """SELECT price, nectar_price FROM price_history
           WHERE product_id = ? ORDER BY recorded_at DESC LIMIT 1 OFFSET 1""",
        (product_id,),
    )
    r = await row.fetchone()
    if r and r["price"] is not None:
        return (r["price"], r["nectar_price"] or r["price"])
    return None


async def alert_exists_for(
    db: aiosqlite.Connection, watchlist_id: int, price_history_id: int, channel: str
) -> bool:
    row = await db.execute(
        "SELECT 1 FROM alert WHERE watchlist_id = ? AND price_history_id = ? AND channel = ?",
        (watchlist_id, price_history_id, channel),
    )
    return (await row.fetchone()) is not None


async def insert_alert(
    db: aiosqlite.Connection, watchlist_id: int, price_history_id: int, message: str, channel: str
) -> None:
    await db.execute(
        "INSERT INTO alert (watchlist_id, price_history_id, message, channel) VALUES (?, ?, ?, ?)",
        (watchlist_id, price_history_id, message, channel),
    )
    await db.commit()


async def get_price_history(db: aiosqlite.Connection, product_id: int, limit: int = 30) -> list[dict]:
    rows = await db.execute(
        """SELECT id, price, nectar_price, recorded_at FROM price_history
           WHERE product_id = ? ORDER BY recorded_at DESC LIMIT ?""",
        (product_id, limit),
    )
    return [dict(r) for r in await rows.fetchall()]


async def get_alerts_for_watchlist(db: aiosqlite.Connection, watchlist_id: int, limit: int = 10) -> list[dict]:
    rows = await db.execute(
        """SELECT id, message, sent_at, channel FROM alert WHERE watchlist_id = ? ORDER BY sent_at DESC LIMIT ?""",
        (watchlist_id, limit),
    )
    return [dict(r) for r in await rows.fetchall()]


async def is_product_on_watchlist(db: aiosqlite.Connection, product_id: int) -> bool:
    row = await db.execute("SELECT 1 FROM watchlist WHERE product_id = ?", (product_id,))
    return (await row.fetchone()) is not None


async def remove_from_watchlist(db: aiosqlite.Connection, watchlist_id: int) -> None:
    await db.execute("DELETE FROM watchlist WHERE id = ?", (watchlist_id,))
    await db.commit()
