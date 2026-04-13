#!/usr/bin/env python3
"""
Batch tag sports cards using Azure OpenAI.
Send each product (title, description, image) to OpenAI and get 10-20 user-friendly search tags.
"""

import argparse
import json
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


def generate_tags(client: OpenAI, deployment: str, product: dict[str, Any]) -> list[str]:
    """
    Generate 10-20 user-friendly search tags for a product.
    
    Args:
        client: OpenAI client
        deployment: Azure deployment name
        product: Product dict with title, description, image_url
    
    Returns:
        List of tags
    """
    title = product.get("title", "").strip()
    description = product.get("description", "").strip()
    image_url = product.get("image_url", "").strip()
    
    # Build the prompt
    prompt = f"""You are an expert in sports cards and ecommerce search behavior.

Analyze this sports card and generate the TOP 10-20 search tags that actual buyers use to find this card on ecommerce platforms.

PRODUCT INFO:
Title: {title}
Description: {description}

IMPORTANT RULES:
1. Return ONLY a JSON array of tags. No explanations, no markdown.
2. Tags must be actual search queries buyers use (e.g., "shohei ohtani rc", "psa 10", "x-fractor")
3. Include: player names, card set, year, grade, special features, variations, sport
4. Keep tags lowercase and user-friendly (1-4 words each)
5. No speculative or vague tags
6. No auction site boilerplate

Example output for a Shohei Ohtani card:
["shohei ohtani", "ohtani rookie", "2018 topps chrome", "x-fractor", "psa 10", "gem mint", "rc card", "baseball"]

Generate tags now:"""

    # Build message content, including the image URL as an image payload if available
    content = []
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

    content.append({"type": "text", "text": prompt})

    try:
        response = client.chat.completions.create(
            model=deployment,
            messages=[
                {
                    "role": "user",
                    "content": content,
                },
            ],
            temperature=0.3,
            max_completion_tokens=300,
        )
        
        raw_response = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            tags = json.loads(raw_response)
            if isinstance(tags, list):
                tags = [str(t).strip().lower() for t in tags if t]
                return tags[:20]  # Cap at 20 tags
        except json.JSONDecodeError:
            pass
        
        return []
    
    except Exception as e:
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
            tags = generate_tags(client, deployment, product)
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
