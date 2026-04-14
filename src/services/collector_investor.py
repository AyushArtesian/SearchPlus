"""CollectorInvestor API service for fetching and normalizing listings."""

import base64
import hashlib
import hmac
import html
import json
import re
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
) -> list[dict]:
    """Fetch and normalize products from CollectorInvestor API."""
    uri = COLLECTOR_INVESTOR_API_URI_TEMPLATE.format(offset=offset, limit=limit)
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