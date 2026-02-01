"""
Sainsbury's vendor adapter. POC: fetch product page and parse price (and Nectar if present).
"""
from .base import VendorAdapter, ProductMatch, Product

# TODO: implement search() and get_product() using httpx + BeautifulSoup
# Example product: https://www.sainsburys.co.uk/gol-ui/product/laila-basmati-rice-10kg
# Respectful: daily run only; minimal requests.


class SainsburysAdapter(VendorAdapter):
    @property
    def name(self) -> str:
        return "sainsburys"

    async def search(self, query: str) -> list[ProductMatch]:
        # TODO: Sainsbury's search URL or product listing; parse results
        raise NotImplementedError("Sainsbury's search not yet implemented")

    async def get_product(self, url_or_id: str) -> Product | None:
        # TODO: GET url_or_id, parse price and Nectar price
        raise NotImplementedError("Sainsbury's get_product not yet implemented")
