import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


NOISE_LINES = {
    "toggle navigation",
    "all categories",
    "search",
    "contact us",
    "about us",
    "newest",
    "ending soon",
    "most popular",
    "advanced search",
    "close",
    "this auction uses",
    "proxy bidding",
    "previous lot",
    "next lot",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def clean_description(raw_description: str) -> str:
    lines = [normalize_space(line) for line in (raw_description or "").splitlines()]
    lines = [line for line in lines if line]

    cleaned: list[str] = []
    for line in lines:
        lower = line.lower()
        if lower in NOISE_LINES:
            continue
        if "bidding has ended on this item" in lower:
            break
        if lower.startswith("april sports") and "auction" in lower:
            continue
        if lower == "(#4053663)":
            continue
        cleaned.append(line)

    if not cleaned:
        return ""

    first = cleaned[0]
    if " - " in first:
        prefix, suffix = first.split(" - ", 1)
        if "collector investor auctions" in prefix.lower() and suffix.strip():
            cleaned[0] = suffix.strip()

    return cleaned[0]


def effective_title(product: dict[str, Any]) -> str:
    title = normalize_space(str(product.get("title") or product.get("name") or ""))
    description = str(product.get("description") or "")

    if "auction" in title.lower() and "closed" in title.lower():
        first_line = ""
        for line in description.splitlines():
            line = normalize_space(line)
            if line:
                first_line = line
                break
        if " - " in first_line:
            _, suffix = first_line.split(" - ", 1)
            fallback = normalize_space(suffix)
            if fallback:
                return fallback

    return title


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Tag products one-by-one using Azure OpenAI and save JSON output incrementally. "
            "Values are loaded automatically from .env when present."
        )
    )
    parser.add_argument(
        "--input",
        default="collectorinvestor_products_sample.json",
        help="Input JSON file path (default: collectorinvestor_products_sample.json)",
    )
    parser.add_argument(
        "--output",
        default="collectorinvestor_products_tagged.json",
        help="Output JSON file path (default: collectorinvestor_products_tagged.json)",
    )
    parser.add_argument(
        "--endpoint",
        default=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        help="Azure OpenAI endpoint base URL, e.g. https://<resource>.openai.azure.com/openai/v1/",
    )
    parser.add_argument(
        "--deployment",
        default=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
        help="Azure OpenAI deployment name (model), e.g. gpt-5.4-nano",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("AZURE_OPENAI_API_KEY", ""),
        help="Azure OpenAI API key",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.25,
        help="Delay between requests in seconds to reduce throttling (default: 0.25)",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retries per product if API call fails (default: 3)",
    )
    return parser.parse_args()


def ensure_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if not endpoint:
        return endpoint
    if not endpoint.endswith("/"):
        endpoint += "/"
    return endpoint


def load_products(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Input JSON must be an array of product objects")

    normalized: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict):
            normalized.append(item)
    return normalized


def save_products(path: Path, products: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)


def extract_json_array(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(tag).strip() for tag in parsed if str(tag).strip()]
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[[\s\S]*\]", raw)
    if not match:
        return []

    try:
        parsed = json.loads(match.group(0))
        if isinstance(parsed, list):
            return [str(tag).strip() for tag in parsed if str(tag).strip()]
    except json.JSONDecodeError:
        return []

    return []


def dedupe_tags(tags: list[str]) -> list[str]:
    blocked_substrings = {
        "?",
        "not specified",
        "unknown",
        "collector investor auctions",
        "collector auction",
        "auction closed",
        "auction lot",
        "vintage cards",
        "modern cards",
        "1800s-1979",
        "1980-current",
    }

    seen: set[str] = set()
    clean: list[str] = []

    for tag in tags:
        normalized = re.sub(r"\s+", " ", tag).strip().lower()
        if not normalized:
            continue
        if any(blocked in normalized for blocked in blocked_substrings):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        clean.append(normalized)

    return clean


def build_prompt(product: dict[str, Any]) -> str:
    cleaned_title = effective_title(product)
    cleaned_description = clean_description(str(product.get("description", "")))

    payload = {
        "id": product.get("id"),
        "title": cleaned_title,
        "description": cleaned_description,
        "image_url": product.get("image_url", ""),
        "lot_url": product.get("lot_url", ""),
    }

    return (
        "You are an expert sports card taxonomy and search-tagging assistant. "
        "Analyze the product data and generate smart ecommerce search tags.\n\n"
        "Rules:\n"
        "1) Return ONLY a raw JSON array of strings.\n"
        "2) No markdown, no explanations, no numbering.\n"
        "3) Generate 12 to 20 high-intent search tags.\n"
        "4) Include player, set/brand, year, rookie indicators, grading, serial/parallel, sport, and rarity if present.\n"
        "5) Add useful synonyms buyers might search for.\n"
        "6) Keep tags concise (1 to 4 words each).\n\n"
        "7) Never include uncertain/speculative tags, question marks, or auction-site boilerplate terms.\n\n"
        f"Product JSON:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def generate_tags_for_product(
    client: OpenAI,
    deployment_name: str,
    product: dict[str, Any],
    max_retries: int,
) -> list[str]:
    prompt = build_prompt(product)
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You generate precise ecommerce search tags for sports cards.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_completion_tokens=400,
            )

            content = response.choices[0].message.content or "[]"
            return dedupe_tags(extract_json_array(content))

        except Exception as exc:
            last_error = exc
            backoff = 1.5 * attempt
            print(f"    Attempt {attempt}/{max_retries} failed: {exc}")
            if attempt < max_retries:
                print(f"    Retrying in {backoff:.1f}s...")
                time.sleep(backoff)

    if last_error:
        raise last_error

    return []


def main() -> None:
    args = parse_args()

    endpoint = ensure_endpoint(args.endpoint)
    deployment_name = args.deployment.strip()
    api_key = args.api_key.strip()

    if not endpoint or not deployment_name or not api_key:
        raise SystemExit(
            "Missing required Azure settings. Provide --endpoint, --deployment, --api-key "
            "or set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_KEY."
        )

    input_path = Path(args.input)
    output_path = Path(args.output)

    products = load_products(input_path)
    if not products:
        raise SystemExit("No products found in input file.")

    client = OpenAI(api_key=api_key, base_url=endpoint)

    print(f"Loaded {len(products)} products from: {input_path}")
    print(f"Using endpoint: {endpoint}")
    print(f"Using deployment: {deployment_name}")

    for idx, product in enumerate(products, 1):
        lot_id = product.get("id", f"item-{idx}")
        title = effective_title(product) or (product.get("title") or product.get("name") or "").strip()

        print(f"\n[{idx}/{len(products)}] Tagging lot {lot_id}: {title[:80]}")

        try:
            tags = generate_tags_for_product(
                client=client,
                deployment_name=deployment_name,
                product=product,
                max_retries=args.max_retries,
            )
            product["tags"] = tags
            product.pop("tagging_error", None)
            print(f"    Generated {len(tags)} tags")

        except Exception as exc:
            product["tags"] = []
            product["tagging_error"] = str(exc)
            print(f"    Failed to tag lot {lot_id}: {exc}")

        save_products(output_path, products)

        if args.delay_seconds > 0:
            time.sleep(args.delay_seconds)

    print(f"\nDone. Output saved to: {output_path}")


if __name__ == "__main__":
    main()
