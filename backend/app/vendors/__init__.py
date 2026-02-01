# Vendor adapters: Sainsbury's first; Tesco, Aldi later.
# See docs/DESIGN.md for VendorAdapter interface.

from .base import VendorAdapter, ProductMatch, Product

__all__ = ["VendorAdapter", "ProductMatch", "Product"]
