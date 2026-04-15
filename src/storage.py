"""Storage layer for product persistence with SQLite."""

import sqlite3
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from src.config import PRODUCTS_DB


def init_db() -> None:
    """Initialize database tables if they don't exist."""
    conn = sqlite3.connect(PRODUCTS_DB)
    cursor = conn.cursor()
    
    # Products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            image_urls TEXT,
            tags TEXT,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tagging history table (to prevent duplicate tagging)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tagging_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            event_id TEXT,
            tagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tags_count INTEGER,
            posting_status TEXT,
            attempts INTEGER DEFAULT 1,
            last_error TEXT,
            UNIQUE(product_id, event_id)
        )
    """)
    
    conn.commit()
    conn.close()


def load_products() -> list[dict]:
    """Load all products from database."""
    init_db()
    conn = sqlite3.connect(PRODUCTS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products ORDER BY id DESC")
    rows = cursor.fetchall()
    
    products = []
    for row in rows:
        product = dict(row)
        # Parse JSON fields
        product["tags"] = json.loads(product["tags"]) if product["tags"] else []
        product["image_urls"] = json.loads(product["image_urls"]) if product["image_urls"] else []
        products.append(product)
    
    conn.close()
    return products


def get_product_by_id(product_id: int | str) -> Optional[dict]:
    """Get a single product by ID."""
    init_db()
    conn = sqlite3.connect(PRODUCTS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM products WHERE id = ?", (int(product_id),))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    product = dict(row)
    product["tags"] = json.loads(product["tags"]) if product["tags"] else []
    product["image_urls"] = json.loads(product["image_urls"]) if product["image_urls"] else []
    return product


def add_or_update_product(product: dict) -> None:
    """Add or update a product in database."""
    init_db()
    conn = sqlite3.connect(PRODUCTS_DB)
    cursor = conn.cursor()
    
    product_id = product.get("id")
    tags_json = json.dumps(product.get("tags", []))
    image_urls_json = json.dumps(product.get("image_urls", []))
    
    cursor.execute("""
        INSERT INTO products 
        (id, title, description, image_url, image_urls, tags, name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(id) DO UPDATE SET
            title=excluded.title,
            description=excluded.description,
            image_url=excluded.image_url,
            image_urls=excluded.image_urls,
            tags=excluded.tags,
            name=excluded.name,
            updated_at=CURRENT_TIMESTAMP
    """, (
        product_id,
        product.get("title"),
        product.get("description"),
        product.get("image_url"),
        image_urls_json,
        tags_json,
        product.get("name")
    ))
    
    conn.commit()
    conn.close()


def get_product_count() -> int:
    """Get total number of products."""
    init_db()
    conn = sqlite3.connect(PRODUCTS_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def should_skip_tagging(product_id: int, event_id: str) -> bool:
    """
    Check if product was already tagged in this event.
    
    Args:
        product_id: Product ID to check
        event_id: Event ID (must be provided)
    
    Returns:
        True if already tagged in this event, False otherwise
    """
    init_db()
    
    conn = sqlite3.connect(PRODUCTS_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 1 FROM tagging_history 
        WHERE product_id = ? AND event_id = ?
    """, (int(product_id), event_id))
    
    result = cursor.fetchone()
    conn.close()
    return result is not None


def record_tagging(product_id: int, event_id: str, tags_count: int, status: str = "pending", error: str = None) -> None:
    """Record tagging event in history."""
    init_db()
    conn = sqlite3.connect(PRODUCTS_DB)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO tagging_history 
        (product_id, event_id, tags_count, posting_status, last_error)
        VALUES (?, ?, ?, ?, ?)
    """, (int(product_id), event_id, tags_count, status, error))
    
    conn.commit()
    conn.close()


def get_tagging_history(product_id: int = None, event_id: str = None) -> list[dict]:
    """Get tagging history records."""
    init_db()
    conn = sqlite3.connect(PRODUCTS_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if product_id and event_id:
        cursor.execute("""
            SELECT * FROM tagging_history 
            WHERE product_id = ? AND event_id = ?
        """, (product_id, event_id))
    elif product_id:
        cursor.execute("SELECT * FROM tagging_history WHERE product_id = ?", (product_id,))
    elif event_id:
        cursor.execute("SELECT * FROM tagging_history WHERE event_id = ?", (event_id,))
    else:
        cursor.execute("SELECT * FROM tagging_history ORDER BY tagged_at DESC")
    
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return records