import argparse
import base64
import hashlib
import hmac
import html
import json
import re
from datetime import datetime, UTC
from pathlib import Path
from urllib.parse import urlparse

import requests

# API auth config
USERNAME = "collectorinvestorapiuser"
BASE64_TOKEN = "U4uRz/MrYA5O4lQNw/zHIlq7v5ez+Mv8ljw80oq3pVU="

# Endpoint that returns listing data
API_URI_TEMPLATE = "https://bid.collectorinvestorauctions.com/api/listing/search/{offset}/{limit}"
CONTENT_TYPE = "application/json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch CollectorInvestor listings and save OpenAI-ready JSON."
    )
    parser.add_argument("--offset", type=int, default=0, help="Listing offset (default: 0)")
    parser.add_argument("--limit", type=int, default=25, help="Listing page size (default: 25)")
    parser.add_argument(
        "--output",
        default="collectorinvestor_products_sample.json",
        help="Output JSON path (default: collectorinvestor_products_sample.json)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=45,
        help="HTTP timeout in seconds (default: 45)",
    )
    parser.add_argument(
        "--status",
        default="",
        help="Optional listing status filter (e.g. Active, Draft)",
    )
    parser.add_argument(
        "--event-id",
        default="",
        help="Optional CollectorInvestor Event ID (e.g. 4053663)",
    )
    return parser.parse_args()


def generate_headers(username: str, base64_token: str, uri: str, body: str, content_type: str) -> dict:
    # API expects Content-MD5 and HMAC signature using request path.
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


def listing_to_product(
    listing: dict,
) -> dict:
    listing_id = listing.get("ID")
    title = (listing.get("Title") or "").strip()
    subtitle = (listing.get("Subtitle") or "").strip()
    description = strip_html(listing.get("Description") or "")

    image_url = ""
    if listing.get("ImageURI"):
        image_url = str(listing.get("ImageURI")).strip()
    if not image_url:
        image_url = extract_best_image_url(listing.get("Media") or [])

    product = {
        "id": listing_id,
        "title": title,
        "description": description,
        "image_url": image_url,
    }
    if subtitle:
        product["subtitle"] = subtitle

    return product


def parse_response_to_listings(payload):
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]

    if isinstance(payload, dict):
        for key in ["List", "list", "Items", "items", "Listings", "listings", "Data", "data"]:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

    return []


def main() -> None:
    args = parse_args()

    uri = API_URI_TEMPLATE.format(offset=args.offset, limit=args.limit)
    
    # Add EventID query parameter if provided
    if args.event_id and args.event_id.strip():
        uri = f"{uri}?EventID={args.event_id.strip()}"
    
    request_body = {"Items": {}}
    body_str = json.dumps(request_body, separators=(",", ":"))

    headers = generate_headers(USERNAME, BASE64_TOKEN, uri, body_str, CONTENT_TYPE)

    print("\n--- Sending Request ---\n")
    print("Endpoint:", uri)
    print("Date:", headers["Date"])

    response = requests.get(uri, headers=headers, data=body_str, timeout=args.timeout)

    print("\n--- Response ---\n")
    print("Status:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        raise SystemExit(1)

    payload = response.json()
    listings = parse_response_to_listings(payload)

    if not listings:
        print("No listings found in response.")
        output_path = Path(args.output)
        output_path.write_text("[]", encoding="utf-8")
        print(f"Saved empty array to: {output_path}")
        return

    products = [listing_to_product(item) for item in listings]

    # Keep only entries with at least an ID and title.
    products = [p for p in products if p.get("id") and p.get("title")]

    # Optional status filter.
    if args.status:
        wanted = args.status.strip().lower()
        listings = [item for item in listings if str(item.get("Status", "")).lower() == wanted]
        products = [listing_to_product(item) for item in listings]

    output_path = Path(args.output)
    output_path.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved {len(products)} normalized products to: {output_path}")


if __name__ == "__main__":
    main()
