"""
PantryPal API entrypoint. Serves REST for frontend and (later) runs daily job.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(
    title="PantryPal",
    description="Price watch for groceries — get alerted when prices drop.",
    version="0.1.0",
)

# Mount frontend static files when built (optional)
# frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
# if frontend_path.exists():
#     app.mount("/", StaticFiles(directory=str(frontend_path), html=True), name="frontend")


@app.get("/health")
def health():
    return {"status": "ok", "service": "pantrypal"}


# TODO: include API routers for watchlist, products, price history
# from app.api import watchlist, products
# app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
# app.include_router(products.router, prefix="/api/products", tags=["products"])
