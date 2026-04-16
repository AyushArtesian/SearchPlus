"""CollectorInvestor API service for fetching and normalizing listings."""

import base64
import hashlib
import hmac
import html
import json
import re
import time
from datetime import datetime, UTC
from typing import Any
from urllib.parse import urlparse

import requests

from src.config import (
    COLLECTOR_INVESTOR_USERNAME,
    COLLECTOR_INVESTOR_BASE64_TOKEN,
    COLLECTOR_INVESTOR_API_URI_TEMPLATE,
    COLLECTOR_INVESTOR_CONTENT_TYPE,
)


def generate_headers(
    username: str, base64_token: str, uri: str, body: str, content_type: str
) -> dict:
    """Generate authenticated headers for CollectorInvestor API."""
    md5_bytes = hashlib.md5(body.encode("utf-8")).digest()
    content_md5 = base64.b64encode(md5_bytes).decode("utf-8")

    date = datetime.now(UTC).strftime("%a, %d %b %Y %H:%M:%S GMT")
    request_path = urlparse(uri).path.lower()

    string_to_sign = (
        "GET\n"
        + content_md5
        + "\n"
        + content_type
        + "\n"
        + date
        + "\n"
        + username
        + "\n"
        + request_path
    )

    token_bytes = base64.b64decode(base64_token)
    signature = base64.b64encode(
        hmac.new(token_bytes, string_to_sign.encode("utf-8"), hashlib.sha256).digest()
    ).decode("utf-8")

    return {
        "Date": date,
        "Content-MD5": content_md5,
        "Authorization": f"RWX_SECURE {username}:{signature}",
        "Content-Type": content_type,
    }


def strip_html(raw: str) -> str:
    """Remove HTML tags and entities from text."""
    if not raw:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", raw, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_best_image_url(media_items: list) -> str:
    """Extract the best quality image URL from a single media item's variations."""
    if not isinstance(media_items, list):
        return ""

    variation_priority = ["FullSize", "LargeSize", "ThumbFit", "ThumbCrop"]

    for media in media_items:
        variations = (media or {}).get("Variations", {})
        if not isinstance(variations, dict):
            continue
        for name in variation_priority:
            node = variations.get(name) or {}
            asset = node.get("Asset") or {}
            metadata = asset.get("MetaData") or {}
            physical_uri = metadata.get("PhysicalURI")
            if physical_uri:
                return str(physical_uri).strip()

    return ""


def extract_all_image_urls(listing: dict) -> list[str]:
    """
    Extract ALL unique image URLs from a listing, in quality order.

    Handles both response shapes:
      Shape A (new API): listing["images"] is already a list of URL strings
                         e.g. ["https://...fullsize.jpg", "https://...fullsize.jpg"]
      Shape B (old API): listing["Media"] is a list of media objects with Variations
                         e.g. [{"Variations": {"FullSize": {"Asset": {...}}}}]

    Returns up to MAX_IMAGES deduplicated absolute URLs.
    """
    MAX_IMAGES = 4   # analyse at most 4 images per listing — more = diminishing returns
    seen: set[str] = set()
    urls: list[str] = []

    def _add(url: str) -> None:
        url = (url or "").strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    # ── Shape A: listing["images"] list of URL strings ───────────────────────
    images_field = listing.get("images") or listing.get("Images")
    if isinstance(images_field, list):
        for item in images_field:
            if isinstance(item, str) and item.strip():
                _add(item.strip())

    # ── Shape B: listing["Media"] list of media objects ──────────────────────
    media_field = listing.get("Media") or listing.get("media")
    if isinstance(media_field, list):
        variation_priority = ["FullSize", "LargeSize", "ThumbFit", "ThumbCrop"]
        for media in media_field:
            variations = (media or {}).get("Variations", {})
            if not isinstance(variations, dict):
                continue
            for name in variation_priority:
                node = variations.get(name) or {}
                asset = node.get("Asset") or {}
                metadata = asset.get("MetaData") or {}
                physical_uri = metadata.get("PhysicalURI")
                if physical_uri:
                    _add(str(physical_uri).strip())
                    break  # take only best variation per media item

    # ── Legacy single-image fallback ─────────────────────────────────────────
    single = (listing.get("ImageURI") or listing.get("image_url") or "").strip()
    if single:
        _add(single)

    return urls[:MAX_IMAGES]


def normalize_category(listing: dict) -> dict[str, str]:
    """
    Extract and normalize the category block from a listing.

    Handles both response shapes:
      Shape A (new API): listing["category"] is a dict with lowercase keys
                         e.g. {"main": "Sports Cards", "sport": "Basketball", "era": "...", "type": "Raw", "format": "Single"}
      Shape B (old API): category fields may be top-level keys (Sport, Era, Type)
    """
    cat: dict[str, str] = {}

    # Shape A — nested category dict
    category_field = listing.get("category") or listing.get("Category")
    if isinstance(category_field, dict):
        for dest, sources in {
            "sport":  ["sport",  "Sport"],
            "era":    ["era",    "Era"],
            "type":   ["type",   "Type"],       # "Raw" / "Graded"
            "format": ["format", "Format"],     # "Single" / "Lot"
            "main":   ["main",   "Main"],
        }.items():
            for src in sources:
                val = category_field.get(src)
                if val and str(val).strip():
                    cat[dest] = str(val).strip()
                    break

    # Shape B — top-level fallback keys
    for dest, key in [("sport", "Sport"), ("era", "Era"), ("type", "Type"), ("format", "Format")]:
        if dest not in cat:
            val = listing.get(key)
            if val and str(val).strip():
                cat[dest] = str(val).strip()

    return cat


def listing_to_product(listing: dict) -> dict:
    """
    Transform a raw listing into a normalized product object.

    New fields added vs original:
      - image_urls (list[str]):  ALL images, not just the first one
      - image_url  (str):        First/best image, kept for backward compatibility
      - category   (dict):       Structured category data (sport, era, type, format)
    """
    listing_id  = listing.get("id") or listing.get("ID")
    title       = (listing.get("title") or listing.get("Title") or "").strip()
    subtitle    = (listing.get("subtitle") or listing.get("Subtitle") or "").strip()
    description = strip_html(listing.get("description") or listing.get("Description") or "")

    # All images (multi-image support)
    image_urls = extract_all_image_urls(listing)
    primary_image_url = image_urls[0] if image_urls else ""

    # Category metadata
    category = normalize_category(listing)

    product: dict[str, Any] = {
        "id":          listing_id,
        "title":       title,
        "description": description,
        "image_url":   primary_image_url,    # backward-compat single URL
        "image_urls":  image_urls,           # all images for multi-image OCR
        "category":    category,             # sport, era, type, format
    }
    if subtitle:
        product["subtitle"] = subtitle

    return product


def parse_response_to_listings(payload: Any) -> list[dict]:
    """Parse API response to extract listing list."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]

    if isinstance(payload, dict):
        for key in ["List", "list", "Items", "items", "Listings", "listings", "Data", "data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    return []


def fetch_products(
    offset: int = 0,
    limit: int = 25,
    timeout: int = 45,
    status: str = "",
    event_id: str = "",
) -> list[dict]:
    """Fetch and normalize products from CollectorInvestor API."""
    uri = COLLECTOR_INVESTOR_API_URI_TEMPLATE.format(offset=offset, limit=limit)
    
    # Add EventID query parameter if provided
    if event_id and event_id.strip():
        uri = f"{uri}?EventID={event_id.strip()}"
    
    request_body = {"Items": {}}
    body_str = json.dumps(request_body, separators=(",", ":"))

    headers = generate_headers(
        COLLECTOR_INVESTOR_USERNAME,
        COLLECTOR_INVESTOR_BASE64_TOKEN,
        uri,
        body_str,
        COLLECTOR_INVESTOR_CONTENT_TYPE,
    )

    response = requests.get(uri, headers=headers, data=body_str, timeout=timeout)

    if response.status_code != 200:
        raise RuntimeError(
            f"CollectorInvestor fetch failed (status {response.status_code}): {response.text[:300]}"
        )

    payload = response.json()
    listings = parse_response_to_listings(payload)

    if status.strip():
        wanted = status.strip().lower()
        listings = [
            item for item in listings
            if str(item.get("Status") or item.get("status") or "").lower() == wanted
        ]

    products = [listing_to_product(item) for item in listings]
    return [p for p in products if p.get("id") and p.get("title")]

def fetch_all_products_for_event(event_id: str, page_size: int = 50, timeout: int = 45) -> list[dict]:
    """
    Fetch ALL products for an event by auto-paginating.
    
    Args:
        event_id: Event ID to fetch
        page_size: Items per page (default 50)
        timeout: HTTP timeout
    
    Returns:
        List of all products for the event
    """
    all_products = []
    offset = 0
    total_fetched = 0
    page_num = 0
    max_retries = 3
    
    print(f"\n  🔄 Starting pagination for event {event_id}...")
    
    while True:
        page_num += 1
        print(f"  📄 Page {page_num}: Fetching offset={offset}, limit={page_size}...", flush=True)
        
        retry_count = 0
        products = None
        last_error = None
        
        # Retry logic for network issues
        while retry_count < max_retries and products is None:
            try:
                products = fetch_products(
                    offset=offset,
                    limit=page_size,
                    timeout=timeout,
                    event_id=event_id
                )
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    print(f"  ⚠ Retry {retry_count}/{max_retries}: {str(e)[:100]}... waiting 2s")
                    time.sleep(2)
                else:
                    print(f"  ✗ ERROR on page {page_num} after {max_retries} retries: {e}")
                    raise
        
        if products is None:
            print(f"  ✗ Failed to fetch page {page_num}: {last_error}")
            raise RuntimeError(f"Failed to fetch page {page_num}: {last_error}")
        
        if not products:
            print(f"  ✓ End of results (page {page_num} returned 0 items)")
            break  # No more products
        
        print(f"  ✓ Page {page_num}: Got {len(products)} items")
        all_products.extend(products)
        total_fetched += len(products)
        offset += 1  # Increment page number, not offset by limit
        
        print(f"  📊 Total so far: {total_fetched} products...")
        
        # Add delay between requests to avoid rate limiting
        if page_num < 100:  # Don't sleep after last page
            print(f"  ⏳ Waiting 1 second before next request...")
            time.sleep(1.0)  # 1 second delay between requests
    
    print(f"  ✅ Pagination complete: {total_fetched} total products across {page_num} pages\n")
    return all_products


def fetch_verification_tags(skip: int = 0, take: int = 50, timeout: int = 45) -> dict:
    """
    Fetch items with their tags from production database via CollectorInvestor API.
    
    This endpoint is used to VERIFY that generated tags have been successfully posted
    to the production database.
    
    Args:
        skip: Number of items to skip (pagination offset)
        take: Number of items to fetch (page size)
        timeout: HTTP timeout in seconds
    
    Returns:
        Dictionary containing:
        - items: List of items with their tags
        - total: Total number of items available
        - skip: Items skipped
        - take: Items taken
        - status: API response status
    """
    base_uri = "https://bid.collectorinvestorauctions.com/api/listing/getlistingtags"
    uri = f"{base_uri}/{skip}/{take}/0"  # /skip/take/filter format
    
    request_body = {"Items": {}}
    body_str = json.dumps(request_body, separators=(",", ":"))
    
    headers = generate_headers(
        COLLECTOR_INVESTOR_USERNAME,
        COLLECTOR_INVESTOR_BASE64_TOKEN,
        uri,
        body_str,
        COLLECTOR_INVESTOR_CONTENT_TYPE,
    )
    
    print(f"  📋 Fetching verification tags: skip={skip}, take={take}...")
    response = requests.get(uri, headers=headers, data=body_str, timeout=timeout)
    
    if response.status_code != 200:
        raise RuntimeError(
            f"Verification tags fetch failed (status {response.status_code}): {response.text[:300]}"
        )
    
    payload = response.json()
    print(f"  ✓ Received response with status: {payload.get('Status', 'unknown')}")
    
    return {
        "items": payload.get("Items", []),
        "total": payload.get("TotalCount", 0),
        "skip": skip,
        "take": take,
        "status": payload.get("Status", "unknown"),
        "raw_response": payload
    }


def fetch_listing_tags_by_id(listing_id: int, event_id: str, timeout: int = 45) -> dict:
    """
    Fetch tags for a SPECIFIC listing by searching through paginated results.
    
    Since the API doesn't support direct listing ID lookup, we paginate through
    results and find the listing matching the given ID.
    
    NOTE: The API uses ListingId (not system_id). If you have system_id, add 1 to convert.
    
    Args:
        listing_id: The listing ID to search for (NOT system_id - use listing_id which is system_id + 1)
        event_id: The event ID (for context/verification)
        timeout: HTTP timeout in seconds
    
    Returns:
        Dictionary containing:
        - success: Boolean indicating if listing was found
        - tags: List of tags posted for this listing
        - has_tags: Boolean indicating if tags were found
    
    Example:
        # If you have system_id=4440023, convert to listing_id=4440024
        result = fetch_listing_tags_by_id(listing_id=4440024, event_id="4053663")
        print(result['success'])  # True
        print(result['tags_count'])  # 47
    """
    base_uri = "https://bid.collectorinvestorauctions.com/api/listing/getlistingtags"
    page_size = 50
    max_pages = 50  # Search up to 2500 items
    
    for page in range(max_pages):
        skip = page * page_size
        uri = f"{base_uri}/{skip}/{page_size}/0"
        
        request_body = {"Items": {}}
        body_str = json.dumps(request_body, separators=(",", ":"))
        
        headers = generate_headers(
            COLLECTOR_INVESTOR_USERNAME,
            COLLECTOR_INVESTOR_BASE64_TOKEN,
            uri,
            body_str,
            COLLECTOR_INVESTOR_CONTENT_TYPE,
        )
        
        response = requests.get(uri, headers=headers, data=body_str, timeout=timeout)
        
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to fetch listing tags (status {response.status_code}): {response.text[:300]}"
            )
        
        payload = response.json()
        
        # API returns: List, PageIndex, PageSize, TotalItemCount, TotalPageCount
        items = payload.get("List", [])
        
        if not items:
            # End of results reached
            break
        
        # Search for matching listing ID in this page
        for item in items:
            item_id = item.get("ListingId")
            
            # Try to match the listing ID
            if item_id == listing_id:
                tags_str = item.get("Tags", "")
                # Parse comma-separated tags string into array
                tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
                
                return {
                    "success": True,
                    "listing_id": listing_id,
                    "event_id": event_id,
                    "tags": tags,
                    "has_tags": bool(tags),
                    "tags_count": len(tags)
                }
    
    # Not found after searching
    return {
        "success": False,
        "listing_id": listing_id,
        "event_id": event_id,
        "tags": [],
        "has_tags": False,
        "tags_count": 0
    }


def fetch_all_verification_tags(page_size: int = 50, timeout: int = 45) -> dict:
    """
    Fetch ALL items with their tags by auto-paginating through verification endpoint.
    
    Args:
        page_size: Items per page (default 50)
        timeout: HTTP timeout
    
    Returns:
        Dictionary containing aggregated results from all pages
    """
    all_items = []
    skip = 0
    page_num = 0
    max_retries = 3
    
    print(f"\n  🔄 Starting verification tag pagination...")
    
    while True:
        page_num += 1
        print(f"  📄 Page {page_num}: Fetching skip={skip}, take={page_size}...")
        
        retry_count = 0
        result = None
        last_error = None
        
        # Retry logic for network issues
        while retry_count < max_retries and result is None:
            try:
                result = fetch_verification_tags(
                    skip=skip,
                    take=page_size,
                    timeout=timeout
                )
            except Exception as e:
                last_error = e
                retry_count += 1
                if retry_count < max_retries:
                    print(f"  ⚠ Retry {retry_count}/{max_retries}: {str(e)[:100]}... waiting 2s")
                    time.sleep(2)
                else:
                    print(f"  ✗ ERROR on page {page_num} after {max_retries} retries: {e}")
                    raise
        
        if result is None:
            print(f"  ✗ Failed to fetch page {page_num}: {last_error}")
            raise RuntimeError(f"Failed to fetch page {page_num}: {last_error}")
        
        items = result.get("items", [])
        if not items:
            print(f"  ✓ End of results (page {page_num} returned 0 items)")
            total = result.get("total", len(all_items))
            break
        
        print(f"  ✓ Page {page_num}: Got {len(items)} items with tags")
        all_items.extend(items)
        skip += len(items)
        
        print(f"  📊 Total so far: {len(all_items)} items...")
        
        # Add delay between requests
        if len(items) == page_size:  # More pages likely exist
            print(f"  ⏳ Waiting 1 second before next request...")
            time.sleep(1.0)
    
    print(f"  ✅ Verification complete: {len(all_items)} total items across {page_num} pages\n")
    
    return {
        "items": all_items,
        "total": total,
        "pages_fetched": page_num,
        "all_items_count": len(all_items)
    }