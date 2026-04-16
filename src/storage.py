"""Storage layer for product persistence with PostgreSQL."""

import psycopg
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import json
from typing import Optional
from src.config import DATABASE_URL

# Connection pool
_connection_pool = None

def get_connection_pool():
    """Get or create connection pool."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=20)
    return _connection_pool


def init_db() -> None:
    """Initialize database tables if they don't exist."""
    pool = get_connection_pool()
    
    with pool.connection() as conn:
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
                id SERIAL PRIMARY KEY,
                product_id INTEGER NOT NULL,
                event_id TEXT NOT NULL,
                tagged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tags_count INTEGER,
                posting_status TEXT,
                attempts INTEGER DEFAULT 1,
                last_error TEXT,
                UNIQUE(product_id, event_id)
            )
        """)
        
        conn.commit()


def load_products() -> list[dict]:
    """Load all products from database."""
    init_db()
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor(row_factory=dict_row)
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
        rows = cursor.fetchall()
        
        products = []
        for product in rows:
            # Parse JSON fields
            product["tags"] = json.loads(product["tags"]) if product["tags"] else []
            product["image_urls"] = json.loads(product["image_urls"]) if product["image_urls"] else []
            products.append(product)
        
        return products


def get_product_by_id(product_id: int | str) -> Optional[dict]:
    """Get a single product by ID."""
    init_db()
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor(row_factory=dict_row)
        cursor.execute("SELECT * FROM products WHERE id = %s", (int(product_id),))
        product = cursor.fetchone()
        
        if not product:
            return None
        
        product["tags"] = json.loads(product["tags"]) if product["tags"] else []
        product["image_urls"] = json.loads(product["image_urls"]) if product["image_urls"] else []
        return product


def add_or_update_product(product: dict) -> None:
    """Add or update a product in database."""
    init_db()
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor()
        
        product_id = product.get("id")
        tags_json = json.dumps(product.get("tags", []))
        image_urls_json = json.dumps(product.get("image_urls", []))
        
        cursor.execute("""
            INSERT INTO products 
            (id, title, description, image_url, image_urls, tags, name, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                title=EXCLUDED.title,
                description=EXCLUDED.description,
                image_url=EXCLUDED.image_url,
                image_urls=EXCLUDED.image_urls,
                tags=EXCLUDED.tags,
                name=EXCLUDED.name,
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


def get_product_count() -> int:
    """Get total number of products."""
    init_db()
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
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
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM tagging_history 
            WHERE product_id = %s AND event_id = %s
        """, (int(product_id), event_id))
        
        result = cursor.fetchone()
        return result is not None


def record_tagging(product_id: int, event_id: str, tags_count: int, status: str = "pending", error: str = None) -> None:
    """Record tagging event in history."""
    init_db()
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tagging_history 
            (product_id, event_id, tags_count, posting_status, last_error)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(product_id, event_id) DO UPDATE SET
                tags_count=EXCLUDED.tags_count,
                posting_status=EXCLUDED.posting_status,
                last_error=EXCLUDED.last_error,
                tagged_at=CURRENT_TIMESTAMP
        """, (int(product_id), event_id, tags_count, status, error))
        
        conn.commit()


def get_tagging_history(product_id: int = None, event_id: str = None) -> list[dict]:
    """Get tagging history records."""
    init_db()
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor(row_factory=dict_row)
        
        if product_id and event_id:
            cursor.execute("""
                SELECT * FROM tagging_history 
                WHERE product_id = %s AND event_id = %s
            """, (product_id, event_id))
        elif product_id:
            cursor.execute("SELECT * FROM tagging_history WHERE product_id = %s", (product_id,))
        elif event_id:
            cursor.execute("SELECT * FROM tagging_history WHERE event_id = %s", (event_id,))
        else:
            cursor.execute("SELECT * FROM tagging_history ORDER BY tagged_at DESC")
        
        records = cursor.fetchall()
        return records if records else []


def delete_tagging_history(product_id: int, event_id: str) -> bool:
    """Delete a tagging history record to allow re-tagging."""
    init_db()
    pool = get_connection_pool()
    
    with pool.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM tagging_history 
            WHERE product_id = %s AND event_id = %s
        """, (int(product_id), event_id))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted