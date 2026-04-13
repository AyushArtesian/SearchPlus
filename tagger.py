#!/usr/bin/env python3
"""
Batch tag sports cards using Azure OpenAI.
Send each product (title, description, image) to OpenAI and get 10-20 user-friendly search tags.
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
import os


load_dotenv()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tag sports cards using Azure OpenAI. Loads settings from .env automatically."
    )
    parser.add_argument(
        "--input",
        default="collectorinvestor_products_sample.json",
        help="Input JSON file with products",
    )
    parser.add_argument(
        "--output",
        default="collectorinvestor_products_tagged.json",
        help="Output JSON file with tags added",
    )
    parser.add_argument(
        "--endpoint",
        default=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        help="Azure OpenAI endpoint (or set AZURE_OPENAI_ENDPOINT env var)",
    )
    parser.add_argument(
        "--deployment",
        default=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        help="Azure OpenAI deployment name (or set AZURE_OPENAI_DEPLOYMENT env var)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("AZURE_OPENAI_API_KEY", ""),
        help="Azure OpenAI API key (or set AZURE_OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay between requests in seconds (default: 0.5)",
    )
    return parser.parse_args()


def load_products(path: str) -> list[dict[str, Any]]:
    """Load products from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        raise ValueError("JSON must be an array of products")
    
    return data


def save_products(path: str, products: list[dict[str, Any]]) -> None:
    """Save products to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


def _normalize_image_url(image_url: str, store_base_url: str = "") -> str:
    image_url = (image_url or "").strip()
    if not image_url:
        return ""

    if image_url.startswith("http://") or image_url.startswith("https://"):
        return image_url

    if image_url.startswith("//"):
        return f"https:{image_url}"

    if not store_base_url:
        return image_url

    base = store_base_url.rstrip("/")
    if image_url.startswith("/"):
        return f"{base}{image_url}"
    return f"{base}/{image_url}"


def _extract_image_url(product: dict[str, Any], store_base_url: str = "") -> str:
    image_candidate = (
        product.get("image_url")
        or product.get("image")
        or product.get("thumbnail")
        or ""
    )
    return _normalize_image_url(str(image_candidate), store_base_url)


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_tags(tags: list[Any]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        clean = _clean_text(tag).lower().strip(".,;:-")
        if not clean:
            continue
        if clean in seen:
            continue
        seen.add(clean)
        normalized.append(clean)
    return normalized[:20]


def _parse_tags_response(raw_response: str) -> list[str]:
    raw_response = (raw_response or "").strip()
    if not raw_response:
        return []

    try:
        parsed = json.loads(raw_response)
        if isinstance(parsed, list):
            return _normalize_tags(parsed)
        if isinstance(parsed, dict) and isinstance(parsed.get("tags"), list):
            return _normalize_tags(parsed["tags"])
    except json.JSONDecodeError:
        pass

    json_array_match = re.search(r"\[[\s\S]*\]", raw_response)
    if json_array_match:
        try:
            parsed = json.loads(json_array_match.group(0))
            if isinstance(parsed, list):
                return _normalize_tags(parsed)
        except json.JSONDecodeError:
            pass

    fallback_split = re.split(r"\n|,", raw_response)
    return _normalize_tags(fallback_split)


def generate_tags(
    product: dict[str, Any],
    store_base_url: str = "",
    *,
    client: OpenAI | None = None,
    deployment: str | None = None,
) -> list[str]:
    """Generate user-search-friendly tags from product text and image."""
    deployment_name = (deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "")).strip()
    if not deployment_name:
        print("    Error: Missing AZURE_OPENAI_DEPLOYMENT")
        return []

    openai_client = client
    if openai_client is None:
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
        if not endpoint or not api_key:
            print("    Error: Missing Azure OpenAI endpoint or API key")
            return []
        if not endpoint.endswith("/"):
            endpoint += "/"
        openai_client = OpenAI(api_key=api_key, base_url=endpoint)

    product_id = product.get("id", "")
    title = _clean_text(product.get("title") or product.get("name"))
    subtitle = _clean_text(product.get("subtitle"))
    description = _clean_text(product.get("description"))
    image_url = _extract_image_url(product, store_base_url)

    payload_for_model: dict[str, Any] = {
        "id": product_id,
        "title": title,
        "description": description,
        "image_url": image_url,
    }
    if subtitle:
        payload_for_model["subtitle"] = subtitle

    prompt = (
        "You are a sports-card ecommerce search expert. "
        "Generate tags that real buyers type when searching for this exact card.\n\n"
        "Input JSON:\n"
        f"{json.dumps(payload_for_model, ensure_ascii=False, indent=2)}\n\n"
        "Rules:\n"
        "1) Return ONLY a JSON array of 12-20 lowercase tags.\n"
        "2) Prioritize high-intent searchable phrases: player name, last name + rc, year + set, "
        "card number, rookie terms, grader/grade (psa/bgs/sgc), parallel/insert/refractor terms, sport.\n"
        "3) No generic filler (e.g. collectible, sports card lot) unless clearly present.\n"
        "4) No duplicates, no hashtags, no punctuation-heavy tags.\n"
        "5) If description is generic boilerplate, rely on title and image details.\n"
        "6) Keep each tag concise (1-4 words)."
    )

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    if image_url:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": "high",
                },
            }
        )

    def _request_tags(request_content: list[dict[str, Any]]) -> list[str]:
        response = openai_client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": request_content}],
            temperature=0.2,
            max_completion_tokens=320,
        )

        raw_response = (response.choices[0].message.content or "").strip()
        return _parse_tags_response(raw_response)

    try:
        return _request_tags(content)

    except Exception as e:
        if image_url:
            try:
                print("    Warning: image could not be used, retrying text-only...")
                return _request_tags([{"type": "text", "text": prompt}])
            except Exception as retry_error:
                print(f"    Error: {retry_error}")
                return []

        print(f"    Error: {e}")
        return []


def main():
    args = parse_args()
    
    # Validate settings
    endpoint = (args.endpoint or "").strip()
    deployment = (args.deployment or "").strip()
    api_key = (args.api_key or "").strip()
    
    if not endpoint or not deployment or not api_key:
        print("ERROR: Missing Azure OpenAI settings.")
        print("Set these environment variables or use command-line args:")
        print("  AZURE_OPENAI_ENDPOINT")
        print("  AZURE_OPENAI_DEPLOYMENT")
        print("  AZURE_OPENAI_API_KEY")
        raise SystemExit(1)
    
    # Ensure endpoint has trailing slash
    if not endpoint.endswith("/"):
        endpoint += "/"
    
    # Load products
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        raise SystemExit(1)
    
    products = load_products(str(input_file))
    print(f"Loaded {len(products)} products from {input_file}\n")
    
    # Create OpenAI client
    client = OpenAI(api_key=api_key, base_url=endpoint)
    
    # Tag each product
    output_file = Path(args.output)
    for idx, product in enumerate(products, 1):
        product_id = product.get("id", f"product-{idx}")
        title = product.get("title", "Unknown")[:60]
        
        print(f"[{idx}/{len(products)}] Tagging {product_id}: {title}...")
        
        try:
            tags = generate_tags(product, client=client, deployment=deployment)
            product["tags"] = tags
            if "tagging_error" in product:
                del product["tagging_error"]
            print(f"    ✓ Generated {len(tags)} tags")
        
        except Exception as e:
            product["tags"] = []
            product["tagging_error"] = str(e)
            print(f"    ✗ Failed: {e}")
        
        # Save after each product (incremental save)
        save_products(str(output_file), products)
        
        # Respect rate limits
        if idx < len(products) and args.delay > 0:
            time.sleep(args.delay)
    
    print(f"\n✓ Done. Saved to {output_file}")


if __name__ == "__main__":
    main()
