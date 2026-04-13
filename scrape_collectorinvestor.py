import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import certifi
import requests
from bs4 import BeautifulSoup


DEFAULT_EVENT_URL = (
    "https://bid.collectorinvestorauctions.com/Event/Details/4053663/"
    "APRIL-SPORTS-NONSPORTS-AUCTION"
)
DEFAULT_OUTPUT = "collectorinvestor_products_sample.json"

LOT_LINK_PATTERN = re.compile(r"^/Event/LotDetails/\d+/", re.IGNORECASE)
WHITESPACE_PATTERN = re.compile(r"\s+")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

STOP_MARKERS = [
    "Winning Bid",
    "Shipping",
    "Lot #",
    "Start Date",
    "Bid/Purchase History",
    "View Bid History",
]

NOISE_MARKERS = {
    "Add to Watch List",
    "Back To Catalog",
    "Additional Links",
    "Home",
    "Browse",
    "Register",
    "Sign In",
}


def normalize_text(value: str) -> str:
    return WHITESPACE_PATTERN.sub(" ", value).strip()


def fetch_html(
    session: requests.Session,
    url: str,
    timeout: int,
    verify: bool | str,
    retries: int = 3,
    backoff: float = 1.5,
) -> str:
    attempt = 1
    while True:
        try:
            response = session.get(url, timeout=timeout, verify=verify)
            response.raise_for_status()

            blocked_by_filter = (
                "Blocked site" in response.text
                or "fw.artesian.io" in response.url
                or "network administration" in response.text.lower()
            )
            if blocked_by_filter:
                raise RuntimeError(
                    "Request appears blocked by a network filter/firewall while fetching: "
                    f"{url}"
                )

            return response.text
        except (
            requests.exceptions.ReadTimeout,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            if attempt >= retries:
                raise
            delay = backoff * attempt
            print(
                f"    Request timed out or failed on attempt {attempt}/{retries}: {exc}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)
            attempt += 1


def get_verify_path(args: argparse.Namespace) -> str:
    # Use CLI arg first, then env var, then certifi default.
    return args.ca_bundle or os.environ.get("COLLECTOR_INVESTOR_CA_BUNDLE") or certifi.where()


def allow_insecure(args: argparse.Namespace) -> bool:
    return args.insecure or os.environ.get("COLLECTOR_INVESTOR_INSECURE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }


def extract_lot_links(event_html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(event_html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()

    for anchor in soup.select("a[href]"):
        href = anchor.get("href", "").strip()
        href = href.split("?", 1)[0]

        if not LOT_LINK_PATTERN.match(href):
            continue

        absolute = urljoin(base_url, href)
        if absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    return links


def extract_title(soup: BeautifulSoup) -> str:
    """Extract product title from lot page, skipping auction headers."""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    lines: list[str] = []
    for raw_line in soup.get_text("\n").splitlines():
        line = normalize_text(raw_line)
        if line:
            lines.append(line)

    # Look for "Lot # " pattern followed by the product title
    for idx, line in enumerate(lines):
        if "lot #" in line.lower():
            # Next non-empty line after "Lot #" is usually the product title
            for next_line in lines[idx + 1 :]:
                next_line = normalize_text(next_line).strip()
                # Skip if it looks like navigation/boilerplate
                if (
                    next_line
                    and len(next_line) > 10
                    and "listing image" not in next_line.lower()
                    and "auction" not in next_line.lower()
                ):
                    return next_line

    # Fallback: look for h1 tag but skip if it contains "auction"
    heading = soup.find("h1")
    if heading:
        title = normalize_text(heading.get_text(" ", strip=True))
        title = re.sub(r"\s*Image\s*$", "", title, flags=re.IGNORECASE).strip()
        if title and "auction" not in title.lower():
            return title

    # Last resort: og:title meta tag
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        return normalize_text(og_title["content"])

    return ""


def extract_image_url(soup: BeautifulSoup, page_url: str) -> str:
    candidates: list[str] = []

    for image in soup.select("img[src]"):
        src = image.get("src", "").strip()
        if not src:
            continue
        absolute = urljoin(page_url, src)
        candidates.append(absolute)

    for candidate in candidates:
        lower = candidate.lower()
        if "blob.core.windows.net" in lower and "_fullsize" in lower:
            return candidate

    for candidate in candidates:
        if "blob.core.windows.net" in candidate.lower():
            return candidate

    og_image = soup.find("meta", attrs={"property": "og:image"})
    if og_image and og_image.get("content"):
        return urljoin(page_url, og_image["content"])

    return ""


def extract_description(soup: BeautifulSoup, title: str) -> str:
    """Extract product description, skipping navigation and boilerplate."""
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    lines: list[str] = []
    for raw_line in soup.get_text("\n").splitlines():
        line = normalize_text(raw_line)
        if line:
            lines.append(line)

    # Find the "Description" marker
    desc_start = -1
    for idx, line in enumerate(lines):
        if line.lower().strip() == "description":
            desc_start = idx + 1
            break

    if desc_start < 0:
        # Fallback: use the first line after finding product title
        title_lower = title.lower()
        for idx, line in enumerate(lines):
            if title_lower and title_lower in line.lower():
                desc_start = idx + 1
                break

    if desc_start < 0:
        # Last resort: use meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return normalize_text(meta_desc["content"])
        return ""

    # Collect lines from desc_start until end markers
    collected: list[str] = []
    for line in lines[desc_start:]:
        lower_line = line.lower()

        # Stop markers
        if any(marker in lower_line for marker in ["you will receive", "happy bidding"]):
            break
        if any(
            lower_line.startswith(marker.lower()) for marker in STOP_MARKERS
        ):
            break

        # Skip noise/navigation
        if line in NOISE_MARKERS:
            continue
        if lower_line.startswith("listing image"):
            continue
        if lower_line.startswith("facebook") or lower_line.startswith("twitter"):
            continue
        if lower_line.startswith("pinterest") or lower_line.startswith("share"):
            continue
        if lower_line.startswith("previous") or lower_line.startswith("next"):
            continue

        if len(line.strip()) > 2:
            collected.append(line)

    # Remove short noisy lines and deduplicate
    filtered = []
    seen_lines: set[str] = set()
    for line in collected:
        normalized_line = normalize_text(line).lower()
        if normalized_line not in seen_lines and len(line.strip()) > 3:
            seen_lines.add(normalized_line)
            filtered.append(line)

    if filtered:
        return "\n\n".join(filtered).strip()

    return ""


def parse_lot_page(lot_url: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    lot_id_match = re.search(r"/LotDetails/(\d+)/", lot_url)
    lot_id = int(lot_id_match.group(1)) if lot_id_match else None

    title = extract_title(soup)
    image_url = extract_image_url(soup, lot_url)
    description = extract_description(soup, title)

    return {
        "id": lot_id,
        "title": title,
        "description": description,
        "image_url": image_url,
        "lot_url": lot_url,
    }


def scrape_event(
    event_url: str,
    limit: int,
    delay: float,
    timeout: int,
    verify: bool | str,
    retries: int,
) -> list[dict[str, Any]]:
    session = requests.Session()
    session.headers.update(HEADERS)

    event_html = fetch_html(
        session,
        event_url,
        timeout=timeout,
        verify=verify,
        retries=retries,
    )
    lot_links = extract_lot_links(event_html, event_url)
    selected_links = lot_links[:limit]

    if not selected_links:
        raise RuntimeError("No lot links found on the event page.")

    products: list[dict[str, Any]] = []
    for index, lot_url in enumerate(selected_links, start=1):
        print(f"[{index}/{len(selected_links)}] Scraping {lot_url}")
        lot_html = fetch_html(
            session,
            lot_url,
            timeout=timeout,
            verify=verify,
            retries=retries,
        )
        products.append(parse_lot_page(lot_url, lot_html))
        time.sleep(delay)

    return products


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape a CollectorInvestor auction event page and save first N lots "
            "to JSON with title, description, image_url, and lot_url."
        )
    )
    parser.add_argument("--event-url", default=DEFAULT_EVENT_URL)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--timeout", type=int, default=40)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument(
        "--ca-bundle",
        dest="ca_bundle",
        help="Path to a custom CA bundle PEM file",
    )
    parser.add_argument(
        "--insecure",
        dest="insecure",
        action="store_true",
        help="Disable SSL verification for local testing",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.limit < 1:
        raise ValueError("--limit must be greater than 0")

    verify_path = get_verify_path(args)
    print(f"Using CA bundle: {verify_path}")

    try:
        products = scrape_event(
            event_url=args.event_url,
            limit=args.limit,
            delay=args.delay,
            timeout=args.timeout,
            verify=verify_path,
            retries=args.retries,
        )
    except requests.exceptions.SSLError as exc:
        if allow_insecure(args):
            print("SSL verification failed. --insecure enabled, retrying with verify=False.")
            products = scrape_event(
                event_url=args.event_url,
                limit=args.limit,
                delay=args.delay,
                timeout=args.timeout,
                verify=False,
            )
        else:
            print("SSL certificate verification failed.")
            print(
                "Provide a valid CA bundle with --ca-bundle or "
                "COLLECTOR_INVESTOR_CA_BUNDLE."
            )
            print(
                "Temporary workaround: run with --insecure or set "
                "COLLECTOR_INVESTOR_INSECURE=1"
            )
            raise SystemExit(1) from exc

    output_path = Path(args.output)
    output_path.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(products)} products to {output_path}")


if __name__ == "__main__":
    main()