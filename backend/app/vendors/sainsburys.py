"""
Sainsbury's vendor adapter. Fetches product page and parses price (and Nectar if present).
Uses Playwright for JS-rendered pages; daily run only.
"""
import re
from typing import Optional
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from .base import VendorAdapter, ProductMatch, Product

BASE = "https://www.sainsburys.co.uk"
SEARCH_URL = "https://www.sainsburys.co.uk/gol-ui/SearchDisplayView"


def _parse_price(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"£\s*(\d+\.?\d*)", text.replace(",", ""))
    return float(m.group(1)) if m else None


def _slug_from_url(url: str) -> Optional[str]:
    m = re.search(r"/product/([^/?]+)", url)
    return m.group(1) if m else None


def _slug_to_display_name(slug: str) -> str:
    """Convert URL slug to readable name, e.g. laila-basmati-rice-10kg -> Laila Basmati Rice 10kg."""
    return slug.replace("-", " ").strip().title()


def _looks_like_error_page(name: str) -> bool:
    """True if the page title/heading suggests we got blocked or an error page."""
    if not name or len(name.strip()) < 2:
        return True
    lower = name.lower().strip()
    return any(
        x in lower
        for x in ("access denied", "blocked", "sorry", "error", "not found", "unavailable", "forbidden")
    )


class SainsburysAdapter(VendorAdapter):
    @property
    def name(self) -> str:
        return "sainsburys"

    async def get_product(self, url_or_id: str) -> Optional[Product]:
        """Fetch product page and extract name, price, Nectar price."""
        url = url_or_id if url_or_id.startswith("http") else f"{BASE}/gol-ui/product/{url_or_id}"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                    ],
                )
                try:
                    page = await browser.new_page(
                        viewport={"width": 1280, "height": 720},
                        user_agent=(
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                    await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
                    await page.set_extra_http_headers({
                        "Accept-Language": "en-GB,en;q=0.9",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    })
                    await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_load_state("networkidle", timeout=10000)
                    html = await page.content()
                    title_el = await page.query_selector("h1")
                    name = (await title_el.inner_text()).strip() if title_el else ""
                    if not name:
                        name = await page.title() or ""

                    slug = _slug_from_url(url)
                    # If Sainsbury's returned Access Denied / block page, derive name from URL slug
                    if _looks_like_error_page(name) and slug:
                        name = _slug_to_display_name(slug)

                    # Try common price patterns: data attributes, classes, or first £ match
                    price = None
                    nectar_price = None
                    for sel in [
                        '[data-testid="product-details"] [class*="price"]',
                        '[class*="pricing"]',
                        '[class*="Price"]',
                        "p[class*='price']",
                    ]:
                        els = await page.query_selector_all(sel)
                        for el in els:
                            t = await el.inner_text()
                            pv = _parse_price(t)
                            if pv and (price is None or pv < (price or 999)):
                                if "nectar" in t.lower() or "nectar" in (await el.get_attribute("class") or "").lower():
                                    nectar_price = pv
                                else:
                                    price = pv

                    if price is None:
                        all_prices = re.findall(r"£\s*(\d+\.?\d*)", html)
                        if all_prices:
                            prices_floats = [float(x) for x in all_prices]
                            price = min(prices_floats)
                            if len(prices_floats) > 1 and nectar_price is None:
                                nectar_price = min(p for p in prices_floats if p != price) or price
                    if nectar_price is None and price is not None:
                        nectar_price = price

                    product_slug = slug or _slug_from_url(url)
                    external_id = product_slug if product_slug else url
                    display_name = name or (_slug_to_display_name(product_slug) if product_slug and "/" not in product_slug else "Unknown")
                    return Product(
                        name=display_name,
                        url=url,
                        current_price=price,
                        nectar_price=nectar_price,
                        external_id=external_id,
                        image_url=None,
                        description=None,
                    )
                finally:
                    await browser.close()
        except Exception:
            return None

    async def search(self, query: str) -> list[ProductMatch]:
        """Search Sainsbury's; returns list of product matches."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage"],
                )
                try:
                    page = await browser.new_page(
                        viewport={"width": 1280, "height": 720},
                        user_agent=(
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        ),
                    )
                    await page.set_extra_http_headers({"Accept-Language": "en-GB,en;q=0.9"})
                    search_url = f"{BASE}/gol-ui/SearchDisplayView?filters[keyword]={query.replace(' ', '+')}"
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_load_state("networkidle", timeout=10000)

                    results: list[ProductMatch] = []
                    links = await page.query_selector_all('a[href*="/gol-ui/product/"]')
                    seen = set()
                    for link in links[:15]:
                        href = await link.get_attribute("href")
                        if not href or href in seen:
                            continue
                        seen.add(href)
                        full_url = urljoin(BASE, href)
                        slug = _slug_from_url(full_url)
                        if not slug:
                            continue
                        text = (await link.inner_text()).strip()
                        name = text[:200] if text else slug.replace("-", " ")
                        results.append(
                            ProductMatch(
                                name=name,
                                url=full_url,
                                current_price=None,
                                nectar_price=None,
                                external_id=slug,
                            )
                        )
                    return results
                finally:
                    await browser.close()
        except Exception:
            return []
