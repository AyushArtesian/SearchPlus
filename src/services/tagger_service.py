"""Tagging service for generating search tags using OpenAI."""

import json
import re
import os
from typing import Any

from openai import OpenAI

from src.config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_KEY,
    TAG_TEMPERATURE,
    TAG_MAX_TOKENS,
)


def _normalize_image_url(image_url: str, store_base_url: str = "") -> str:
    """Normalize and resolve image URLs."""
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
    """Extract best available image URL from product."""
    image_candidate = (
        product.get("image_url")
        or product.get("image")
        or product.get("thumbnail")
        or ""
    )
    return _normalize_image_url(str(image_candidate), store_base_url)


def _clean_text(value: Any) -> str:
    """Clean and normalize text."""
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_tags(tags: list[Any]) -> list[str]:
    """Normalize and deduplicate tags."""
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
    """Parse OpenAI response and extract tags."""
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
    """Generate user-search-friendly tags from product data using OpenAI."""
    deployment_name = (deployment or os.getenv("AZURE_OPENAI_DEPLOYMENT", "") or AZURE_OPENAI_DEPLOYMENT).strip()
    if not deployment_name:
        print("    Error: Missing AZURE_OPENAI_DEPLOYMENT")
        return []

    openai_client = client
    if openai_client is None:
        endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT", "") or AZURE_OPENAI_ENDPOINT).strip()
        api_key = (os.getenv("AZURE_OPENAI_API_KEY", "") or AZURE_OPENAI_API_KEY).strip()
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
            temperature=TAG_TEMPERATURE,
            max_completion_tokens=TAG_MAX_TOKENS,
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
