"""
Watchlist API: add product, list watchlist, remove, get price history.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.db.database import get_connection, init_db
from app.db import crud
from app.vendors.sainsburys import SainsburysAdapter

router = APIRouter()


class AddProductRequest(BaseModel):
    url: Optional[str] = None
    search_query: Optional[str] = None
    alert_email: Optional[str] = None
    alert_telegram_chat_id: Optional[str] = None
    alert_on_drop_only: bool = True


class SetPriceRequest(BaseModel):
    price: float
    nectar_price: Optional[float] = None


@router.post("/api/watchlist/add")
async def add_to_watchlist(req: AddProductRequest):
    url = (req.url or "").strip() or None
    search_query = (req.search_query or "").strip() or None
    if not url and not search_query:
        raise HTTPException(400, "Provide url or search_query")
    await init_db()
    db = await get_connection()
    try:
        sainsburys = SainsburysAdapter()
        if url:
            product = await sainsburys.get_product(url)
        else:
            matches = await sainsburys.search(search_query or "")
            if not matches:
                raise HTTPException(404, "No products found for that search")
            product = await sainsburys.get_product(matches[0].url)
        if not product:
            raise HTTPException(502, "Could not fetch product details")
        product_id = await crud.upsert_product(
            db,
            crud.SAINSBURYS_VENDOR_ID,
            product.external_id or product.url,
            product.name,
            product.url,
            product.image_url,
        )
        if await crud.is_product_on_watchlist(db, product_id):
            return {"ok": True, "message": "Already on watchlist", "product_id": product_id}
        wid = await crud.add_to_watchlist(
            db, product_id,
            alert_email=req.alert_email,
            alert_telegram_chat_id=req.alert_telegram_chat_id,
            alert_on_drop_only=req.alert_on_drop_only,
        )
        return {"ok": True, "watchlist_id": wid, "product_id": product_id}
    finally:
        await db.close()


@router.get("/api/watchlist")
async def list_watchlist():
    await init_db()
    db = await get_connection()
    try:
        entries = await crud.get_watchlist_entries(db)
        return {"items": entries}
    finally:
        await db.close()


@router.delete("/api/watchlist/{watchlist_id}")
@router.post("/api/watchlist/remove/{watchlist_id}")
async def remove_from_watchlist(watchlist_id: int):
    await init_db()
    db = await get_connection()
    try:
        await crud.remove_from_watchlist(db, watchlist_id)
        return {"ok": True}
    finally:
        await db.close()


@router.post("/api/products/{product_id}/price")
async def set_price(product_id: int, req: SetPriceRequest):
    """Record price manually (e.g. when the site blocks automated access)."""
    await init_db()
    db = await get_connection()
    try:
        product = await crud.get_product_by_id(db, product_id)
        if not product:
            raise HTTPException(404, "Product not found")
        nectar = req.nectar_price if req.nectar_price is not None else req.price
        await crud.insert_price_history(db, product_id, req.price, nectar)
        return {"ok": True, "message": "Price recorded"}
    finally:
        await db.close()


@router.get("/api/price-history/{product_id}")
async def price_history(product_id: int, limit: int = 30):
    await init_db()
    db = await get_connection()
    try:
        rows = await crud.get_price_history(db, product_id, limit=limit)
        return {"product_id": product_id, "history": rows}
    finally:
        await db.close()


@router.get("/api/search")
async def search(q: str = ""):
    if not q.strip():
        return {"results": []}
    sainsburys = SainsburysAdapter()
    matches = await sainsburys.search(q.strip())
    return {"results": [{"name": m.name, "url": m.url, "external_id": m.external_id} for m in matches]}
