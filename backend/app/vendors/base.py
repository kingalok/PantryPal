"""
Abstract vendor adapter. Each retailer (Sainsbury's, Tesco, Aldi) implements this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ProductMatch:
    """Result of a search (e.g. "Laila Basmati Rice 10kg")."""
    name: str
    url: str
    current_price: Optional[float]
    nectar_price: Optional[float] = None  # Sainsbury's Nectar; None for others
    external_id: Optional[str] = None


@dataclass
class Product:
    """Full product snapshot for storing and price history."""
    name: str
    url: str
    current_price: Optional[float]
    nectar_price: Optional[float] = None
    external_id: Optional[str] = None
    image_url: Optional[str] = None
    description: Optional[str] = None


class VendorAdapter(ABC):
    """Implement per vendor: Sainsbury's, then Tesco, Aldi."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Vendor slug, e.g. 'sainsburys'."""
        ...

    @abstractmethod
    async def search(self, query: str) -> list[ProductMatch]:
        """Search for products; fuzzy or exact by vendor. Returns list of matches."""
        ...

    @abstractmethod
    async def get_product(self, url_or_id: str) -> Optional[Product]:
        """Fetch current price for one product by URL or external_id."""
        ...
