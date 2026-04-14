"""Storage layer for product persistence."""

import json
from pathlib import Path
from typing import Optional
from src.config import PRODUCTS_DB


def load_products() -> list[dict]:
    """Load products from JSON file. Create empty list if file doesn't exist."""
    if not PRODUCTS_DB.exists():
        save_products([])
        return []
    
    try:
        with open(PRODUCTS_DB, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_products(products: list[dict]) -> None:
    """Save products to JSON file."""
    PRODUCTS_DB.parent.mkdir(exist_ok=True)
    with open(PRODUCTS_DB, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


def get_product_by_id(product_id: int | str) -> Optional[dict]:
    """Get a single product by ID."""
    products = load_products()
    product_id = int(product_id)
    for product in products:
        if product.get("id") == product_id:
            return product
    return None


def add_or_update_product(product: dict) -> None:
    """Add a new product or update existing one by ID."""
    products = load_products()
    product_id = product.get("id")
    
    # Find and update or append
    for i, p in enumerate(products):
        if p.get("id") == product_id:
            products[i] = product
            save_products(products)
            return
    
    products.append(product)
    save_products(products)


def get_product_count() -> int:
    """Get total number of products in database."""
    return len(load_products())
