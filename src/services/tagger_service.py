"""
Tagging service — three-pass pipeline:
  Pass 1 — OCR:         Read visible text from ALL card images (temperature=0)
  Pass 2 — Text+Cat:    Parse structured facts from title/subtitle/description + category (temperature=0)
  Pass 3 — Tag gen:     Merge all sources → generate grounded buyer-search tags
"""

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

# Maximum images to OCR per product. Front + back is ideal; >4 rarely adds value.
MAX_OCR_IMAGES = 4


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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
    return f"{base}{image_url}" if image_url.startswith("/") else f"{base}/{image_url}"


def _extract_all_image_urls(product: dict[str, Any], store_base_url: str = "") -> list[str]:
    """
    Return all unique image URLs from the product, up to MAX_OCR_IMAGES.
    Reads product["image_urls"] (list) first, falls back to product["image_url"] (str).
    """
    seen: set[str] = set()
    urls: list[str] = []

    def _add(raw: str) -> None:
        url = _normalize_image_url(raw, store_base_url)
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    # Primary: image_urls list (set by updated collector_investor.py)
    for raw in product.get("image_urls") or []:
        if isinstance(raw, str):
            _add(raw)

    # Fallback: single image_url string
    single = product.get("image_url") or product.get("image") or product.get("thumbnail") or ""
    if isinstance(single, str):
        _add(single)

    return urls[:MAX_OCR_IMAGES]


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_tags(tags: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        clean = re.sub(r"\s+", " ", str(tag or "")).lower().strip(".,;:-\"'/#")
        if not clean or len(clean) < 2:
            continue
        if clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
    return result[:50]


def _parse_json_list(raw: str) -> list[str]:
    raw = (raw or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        if isinstance(parsed, dict):
            for key in ("tags", "result", "output"):
                if isinstance(parsed.get(key), list):
                    return [str(x) for x in parsed[key]]
    except json.JSONDecodeError:
        pass
    m = re.search(r"\[[\s\S]*?\]", raw)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            pass
    return [x.strip() for x in re.split(r"\n|,", raw) if x.strip()]


def _parse_facts_json(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        try:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}


def _expand_condition(abbr: str) -> str:
    mapping = {
        "nm": "near mint", "nm-mt": "near mint mint",
        "ex": "excellent", "ex-mt": "excellent mint",
        "vg": "very good", "vg-ex": "very good excellent",
        "g": "good", "fr": "fair", "pr": "poor",
    }
    return mapping.get(abbr.lower().strip(), abbr.lower().strip())


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

def _merge_ocr_results(ocr_list: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Merge OCR results from multiple images into one fact sheet.
    Strategy:
      - For scalar fields: first non-null value wins (image 0 = front, most reliable)
      - For booleans (autograph, patch_jersey): True if ANY image says True
      - For list fields (other_visible_text): union of all values
    """
    if not ocr_list:
        return {}
    if len(ocr_list) == 1:
        return ocr_list[0]

    SCALAR_FIELDS = [
        "player_name", "year", "card_set", "card_number", "team", "position",
        "sport", "manufacturer", "parallel_insert", "serial_number",
        "grading_company", "grade", "cert_number",
    ]
    BOOL_FIELDS = ["autograph", "patch_jersey"]
    LIST_FIELDS = ["other_visible_text"]

    merged: dict[str, Any] = {}

    for field in SCALAR_FIELDS:
        for ocr in ocr_list:
            val = ocr.get(field)
            if val is not None and val != "":
                merged[field] = val
                break
        else:
            merged[field] = None

    for field in BOOL_FIELDS:
        merged[field] = any(
            ocr.get(field) is True or str(ocr.get(field, "")).lower() == "true"
            for ocr in ocr_list
        )

    for field in LIST_FIELDS:
        combined: list[str] = []
        seen_vals: set[str] = set()
        for ocr in ocr_list:
            vals = ocr.get(field) or []
            if isinstance(vals, list):
                for v in vals:
                    sv = str(v).strip()
                    if sv and sv not in seen_vals:
                        seen_vals.add(sv)
                        combined.append(sv)
        if combined:
            merged[field] = combined

    return merged


def _merge_facts(
    ocr: dict[str, Any],
    text_facts: dict[str, Any],
) -> dict[str, Any]:
    """
    Merge image-OCR facts + text-extracted facts into one unified fact sheet.
    OCR wins for visual/physical facts; text fills gaps.
    Each field is tagged with its source for prompt transparency.
    """
    SHARED_FIELDS = [
        "player_name", "year", "card_set", "card_number", "team",
        "position", "sport", "manufacturer", "parallel_insert", "serial_number",
    ]
    VISUAL_PRIORITY_FIELDS = ["grading_company", "grade", "cert_number"]
    BOOL_FIELDS = ["autograph", "patch_jersey"]

    merged: dict[str, Any] = {}

    for field in SHARED_FIELDS:
        ocr_val = ocr.get(field)
        txt_val = text_facts.get(field)
        if ocr_val is not None and ocr_val != "":
            merged[field] = ocr_val
            merged[f"{field}_source"] = "image"
        elif txt_val is not None and txt_val != "":
            merged[field] = txt_val
            merged[f"{field}_source"] = "text"
        else:
            merged[field] = None

    for field in VISUAL_PRIORITY_FIELDS:
        ocr_val = ocr.get(field)
        txt_val = text_facts.get(field)
        if ocr_val is not None and ocr_val != "":
            merged[field] = ocr_val
            merged[f"{field}_source"] = "image"
        elif txt_val is not None and txt_val != "":
            merged[field] = txt_val
            merged[f"{field}_source"] = "text_only"  # lower confidence
        else:
            merged[field] = None

    for field in BOOL_FIELDS:
        ocr_true  = ocr.get(field)  is True or str(ocr.get(field,  "")).lower() == "true"
        txt_true  = text_facts.get(field) is True or str(text_facts.get(field, "")).lower() == "true"
        merged[field] = ocr_true or txt_true
        merged[f"{field}_source"] = (
            "image+text" if (ocr_true and txt_true)
            else "image" if ocr_true
            else "text"  if txt_true
            else None
        )

    # raw_condition only comes from text
    rc = text_facts.get("raw_condition")
    if rc:
        merged["raw_condition"] = rc

    # Extra keywords — union from both sources
    extra: list[str] = []
    seen_extra: set[str] = set()
    for src in (ocr, text_facts):
        vals = src.get("other_visible_text") or src.get("extra_keywords") or []
        if isinstance(vals, list):
            for v in vals:
                sv = str(v).strip()
                if sv and sv not in seen_extra:
                    seen_extra.add(sv)
                    extra.append(sv)
        elif isinstance(vals, str) and vals.strip():
            sv = vals.strip()
            if sv not in seen_extra:
                seen_extra.add(sv)
                extra.append(sv)
    if extra:
        merged["extra_keywords"] = extra

    return merged


# ---------------------------------------------------------------------------
# PASS 1 — Multi-image OCR
# ---------------------------------------------------------------------------

OCR_PROMPT = """You are an expert sports card OCR analyst. Your ONLY job is to read what is
literally visible in this image and report it as structured JSON. NEVER guess or infer anything
not directly visible.

Examine this sports card image carefully and extract every piece of visible text.

Return ONLY valid JSON in this exact schema — use null for any field you cannot clearly see:

{
  "player_name": "exact name as printed on card",
  "year": "year as printed (e.g. 1986) — null if not printed anywhere on card",
  "card_set": "set/brand name as printed (e.g. Fleer, Topps, Donruss, Bowman, Prizm)",
  "card_number": "card number as printed (e.g. 32, #32) — null if not visible",
  "team": "team name as printed on card",
  "position": "position as printed (abbreviation or full word)",
  "sport": "Basketball, Baseball, Football, or Hockey — only if clearly identifiable",
  "manufacturer": "manufacturer text if different from set name",
  "parallel_insert": "parallel or insert name if printed (e.g. Gold Refractor, Silver Prizm, Holo) — null if base card",
  "serial_number": "serial number if physically printed on card (e.g. 45/100) — null if not numbered",
  "autograph": true or false — is a physical handwritten signature visibly present on the card itself,
  "patch_jersey": true or false — is a fabric swatch physically embedded in the card,
  "grading_company": "PSA, BGS, SGC, or CSG — only if card is sealed in a graded slab. null if raw.",
  "grade": "grade number on slab label (e.g. 10, 9.5) — null if raw/ungraded",
  "cert_number": "cert/barcode number on slab label if clearly readable — null if not",
  "other_visible_text": ["any other text on card or slab not captured above"]
}

RULES:
- Report ONLY what you can literally read. If unsure, use null.
- Do NOT infer year from the set name. Only report year if it is printed on the card.
- Do NOT add grading_company or grade unless the card is in a graded slab.
- autograph and patch_jersey are booleans — true or false, never null.
- Return ONLY the JSON object. No other text."""


def _ocr_single_image(
    openai_client: OpenAI,
    deployment_name: str,
    image_url: str,
    image_index: int,
) -> dict[str, Any]:
    """OCR one image. Returns parsed facts dict."""
    try:
        response = openai_client.chat.completions.create(
            model=deployment_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
                ],
            }],
            temperature=0.0,
            max_completion_tokens=600,
        )
        raw = (response.choices[0].message.content or "").strip()
        result = _parse_facts_json(raw)
        print(f"      [OCR img{image_index}] {json.dumps(result, ensure_ascii=False)}")
        return result
    except Exception as e:
        print(f"      [OCR img{image_index}] Failed: {e}")
        return {}


def _ocr_all_images(
    openai_client: OpenAI,
    deployment_name: str,
    image_urls: list[str],
) -> dict[str, Any]:
    """
    Run OCR on every image URL and merge results.
    Front of card (index 0) is usually most information-rich.
    Back of card (index 1) often has stats, card number, copyright year.
    Slab images (if graded) may have grade, cert number.
    """
    if not image_urls:
        return {}

    ocr_results: list[dict[str, Any]] = []
    for i, url in enumerate(image_urls):
        result = _ocr_single_image(openai_client, deployment_name, url, i)
        if result:
            ocr_results.append(result)

    merged = _merge_ocr_results(ocr_results)
    print(f"      [OCR merged] {json.dumps(merged, ensure_ascii=False)}")
    return merged


# ---------------------------------------------------------------------------
# PASS 2 — Text + Category extraction
# ---------------------------------------------------------------------------

TEXT_EXTRACT_PROMPT_TEMPLATE = """You are a sports card data parser. Extract structured facts
from the listing text and category metadata below. Only report facts that are explicitly
stated — do NOT infer or guess.

=== LISTING TEXT ===
Title:       {title}
Subtitle:    {subtitle}
Description: {description}

=== CATEGORY METADATA ===
Sport:   {cat_sport}
Era:     {cat_era}
Type:    {cat_type}
Format:  {cat_format}

Return ONLY valid JSON using this schema — use null for anything not mentioned:

{{
  "player_name": "player name if mentioned",
  "year": "card year if mentioned (e.g. 1986)",
  "card_set": "card set or brand if mentioned (e.g. Fleer, Topps, Prizm)",
  "card_number": "card number if mentioned (e.g. #32, 32)",
  "team": "team name if mentioned",
  "position": "player position if mentioned",
  "sport": "sport — use category metadata if not in title",
  "manufacturer": "manufacturer if mentioned separately from set",
  "parallel_insert": "parallel or insert name if mentioned (e.g. Gold Refractor, Holo, SSP, Photo Variation) — null if not mentioned",
  "serial_number": "serial number if mentioned (e.g. 45/100) — null if not mentioned",
  "autograph": true or false — is autograph/signed/auto explicitly mentioned,
  "patch_jersey": true or false — is patch/jersey/relic/game-used explicitly mentioned,
  "grading_company": "PSA, BGS, SGC — only if explicitly mentioned. null otherwise.",
  "grade": "numeric grade if explicitly stated (e.g. 10, 9.5) — null if not stated",
  "cert_number": "cert number if mentioned — null if not",
  "raw_condition": "raw condition if stated (e.g. NM, EX-MT, VG) — null if not stated",
  "is_lot": true or false — does the listing describe multiple cards (lot/set/collection),
  "lot_count": "number of cards in lot if mentioned (e.g. 4) — null if single card",
  "era": "era from category if useful (e.g. Vintage, Modern)",
  "card_type": "Raw or Graded — from category type field",
  "extra_keywords": ["any other specific searchable terms not captured above — include SSP, Case Hit, Photo Variation, insert names, player nicknames, etc."]
}}

RULES:
- Abbreviations count: RC = rookie card, NM = near mint, EX = excellent, SSP = short print, SP = short print, HOF = hall of fame.
- autograph, patch_jersey, is_lot are booleans — true or false, never null.
- Category metadata is reliable — use sport/era/type from it if not stated in title.
- Do NOT fabricate. If a field is not in the text or category, use null.
- Return ONLY the JSON object."""


def _extract_text_facts(
    openai_client: OpenAI,
    deployment_name: str,
    title: str,
    subtitle: str,
    description: str,
    category: dict[str, str],
) -> dict[str, Any]:
    """Pass 2: extract structured facts from listing text + category at temperature=0."""
    prompt = TEXT_EXTRACT_PROMPT_TEMPLATE.format(
        title=title or "(none)",
        subtitle=subtitle or "(none)",
        description=description or "(none)",
        cat_sport=category.get("sport") or "(not specified)",
        cat_era=category.get("era") or "(not specified)",
        cat_type=category.get("type") or "(not specified)",
        cat_format=category.get("format") or "(not specified)",
    )
    try:
        response = openai_client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_completion_tokens=600,
        )
        raw = (response.choices[0].message.content or "").strip()
        facts = _parse_facts_json(raw)
        print(f"      [TEXT] {json.dumps(facts, ensure_ascii=False)}")
        return facts
    except Exception as e:
        print(f"      [TEXT] Failed: {e}")
        return {}


# ---------------------------------------------------------------------------
# PASS 3 — Tag generation from merged facts
# ---------------------------------------------------------------------------

def _facts_to_readable_block(merged: dict[str, Any]) -> str:
    lines: list[str] = []

    def _src(field: str) -> str:
        src = merged.get(f"{field}_source")
        if src == "image":        return " [from image]"
        if src == "text":         return " [from listing text]"
        if src == "image+text":   return " [confirmed by image + text]"
        if src == "text_only":    return " [from listing text — lower confidence]"
        return ""

    simple_fields = [
        ("player_name",     "Player name"),
        ("year",            "Year"),
        ("card_set",        "Card set / brand"),
        ("card_number",     "Card number"),
        ("team",            "Team"),
        ("position",        "Position"),
        ("sport",           "Sport"),
        ("manufacturer",    "Manufacturer"),
        ("parallel_insert", "Parallel / insert name"),
        ("serial_number",   "Serial number"),
        ("grading_company", "Grading company"),
        ("grade",           "Grade"),
        ("cert_number",     "Cert number"),
        ("raw_condition",   "Raw condition"),
        ("era",             "Era"),
        ("card_type",       "Card type (Raw/Graded)"),
        ("lot_count",       "Lot count"),
    ]
    for key, label in simple_fields:
        val = merged.get(key)
        if val is not None and val != "":
            lines.append(f"  {label}: {val}{_src(key)}")

    for key, label in [("autograph", "Autograph"), ("patch_jersey", "Patch / jersey swatch"), ("is_lot", "Is a lot/multi-card")]:
        val = merged.get(key)
        if val is True:
            src = merged.get(f"{key}_source")
            src_str = f" [confirmed by {src}]" if src else ""
            lines.append(f"  {label}: YES{src_str}")

    extra = merged.get("extra_keywords")
    if extra:
        lines.append(f"  Extra keywords: {', '.join(str(x) for x in extra)}")

    return "\n".join(lines) if lines else "  (no structured facts extracted)"


def _build_tag_prompt(
    title: str,
    subtitle: str,
    description: str,
    category: dict[str, str],
    merged: dict[str, Any],
) -> str:
    facts_block = _facts_to_readable_block(merged)

    # Pre-compute flags so instructions are explicit — no guessing in the model
    is_graded      = bool(merged.get("grading_company")) or str(merged.get("card_type", "")).lower() == "graded"
    grade_val      = merged.get("grade")
    is_gem_mint    = str(grade_val).strip() == "10" if grade_val else False
    is_mint        = str(grade_val).strip() == "9"  if grade_val else False
    has_auto       = merged.get("autograph") is True
    has_patch      = merged.get("patch_jersey") is True
    has_parallel   = bool(merged.get("parallel_insert"))
    has_serial     = bool(merged.get("serial_number"))
    is_lot         = merged.get("is_lot") is True or str(category.get("format", "")).lower() == "lot"
    lot_count      = merged.get("lot_count")
    raw_condition  = merged.get("raw_condition")
    year_val       = str(merged.get("year") or "").strip()
    year_int       = int(re.sub(r"\D", "", year_val) or "0") if year_val else 0
    is_vintage     = 0 < year_int < 1980
    is_eighties    = 1980 <= year_int <= 1989
    is_nineties    = 1990 <= year_int <= 1999
    is_modern      = year_int >= 2000
    sport          = str(merged.get("sport") or category.get("sport") or "").strip()
    era_label      = str(merged.get("era") or category.get("era") or "").strip()
    parallel_name  = str(merged.get("parallel_insert") or "").strip().lower()
    serial_val     = str(merged.get("serial_number") or "").strip()
    cert_val       = str(merged.get("cert_number") or "").strip()
    company        = str(merged.get("grading_company") or "").strip().lower()

    # Rookie detection across all text sources
    combined_text = " ".join([
        title, subtitle, description,
        str(merged.get("card_set") or ""),
        str(merged.get("parallel_insert") or ""),
        " ".join(merged.get("extra_keywords") or []),
    ]).lower()
    is_rookie = bool(re.search(r"\b(rc|rookie card|rookie)\b", combined_text))

    # SSP / short print detection
    is_ssp = bool(re.search(r"\b(ssp|short print|sp\b)", combined_text))

    # Photo variation detection
    is_photo_var = bool(re.search(r"photo variation", combined_text))

    # Case hit detection
    is_case_hit = bool(re.search(r"case hit", combined_text))

    # Build confirmed-flag lines
    def _flag(condition: bool, yes_msg: str, no_msg: str) -> str:
        return f"✓ {yes_msg}" if condition else f"✗ {no_msg}"

    flags = "\n".join([
        _flag(is_graded,    "Card IS graded — include grading tags",                  "Card is RAW/ungraded — DO NOT add PSA/BGS/SGC/grade tags"),
        _flag(is_rookie,    "Rookie confirmed — include RC tags",                      "Rookie NOT confirmed — DO NOT add rookie/RC tags"),
        _flag(has_auto,     "Autograph confirmed — include auto/signed tags",          "Autograph NOT confirmed — DO NOT add auto/signed tags"),
        _flag(has_patch,    "Patch/jersey confirmed — include patch/relic tags",       "Patch NOT confirmed — DO NOT add patch/jersey/relic tags"),
        _flag(has_parallel, f"Parallel confirmed: '{parallel_name}' — include parallel tags", "Parallel NOT confirmed — DO NOT add refractor/prizm/holo/insert tags"),
        _flag(has_serial,   f"Serial number confirmed: {serial_val} — include numbered tags", "Serial NOT confirmed — DO NOT add numbered/serial tags"),
        _flag(is_lot,       f"This is a LOT/multi-card listing{' (' + str(lot_count) + ' cards)' if lot_count else ''} — include lot tags", "Single card — do not add lot/bundle tags"),
        _flag(is_ssp,       "SSP/Short Print confirmed — include ssp tags",            "SSP NOT confirmed — do not add ssp tags"),
        _flag(is_photo_var, "Photo Variation confirmed — include photo variation tags","Photo Variation NOT confirmed — skip"),
        _flag(is_case_hit,  "Case Hit confirmed — include case hit tags",              "Case Hit NOT confirmed — skip"),
    ])

    # Build dynamic category context paragraph
    category_notes: list[str] = []
    if sport:
        category_notes.append(f"Sport is confirmed as: {sport}")
    if era_label:
        category_notes.append(f"Era category: {era_label}")
    if is_lot:
        category_notes.append("This listing is a LOT (multiple cards).")
    cat_block = "\n".join(f"  • {n}" for n in category_notes) if category_notes else "  (no category metadata)"

    return f"""You are a sports card search-tag specialist. You know exactly what real collectors
type on eBay, PWCC, Goldin, Beckett, and Google when searching for specific cards.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VERIFIED FACTS  (from image OCR + listing text + category)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{facts_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CATEGORY CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{cat_block}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ORIGINAL LISTING TEXT  (for any nuance not captured above)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Title:       {title or "(none)"}
Subtitle:    {subtitle or "(none)"}
Description: {description or "(none)"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIRMED FLAGS  (these override everything — read before generating)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{flags}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate exactly 40-50 unique lowercase search tags a real buyer would type to find this card.
Use ALL sources: image OCR, listing text, and category metadata.
Return ONLY a flat JSON array of strings. No explanation, no preamble, no markdown fences.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TAG CATEGORIES  (cover every applicable one — skip those marked ✗ above)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. PLAYER NAME — all three forms if known:
   • Full name        → "kon knueppel"
   • Last name only   → "knueppel"
   • First name only  → "kon"

2. YEAR — if confirmed:
   • Year alone       → "2025"

3. CARD SET / BRAND:
   • Brand alone          → "topps chrome"
   • Year + brand         → "2025 topps chrome"
   • Year + topps alone   → "2025 topps"  (if applicable)

4. CARD NUMBER — if confirmed:
   • With hash        → "#57"
   • Brand + number   → "topps chrome 57"

5. ROOKIE TAGS — only if confirmed (see flags):
   • "rookie card", "rc", "rookie"
   • Player + rc              → "knueppel rc"
   • Player + rookie card     → "knueppel rookie card"
   • Year + brand + rc        → "2025 topps chrome rc"
   • Year + brand + player    → "2025 topps chrome knueppel"

6. TEAM — if confirmed:
   • Full team        → "oklahoma city thunder"
   • City only        → "oklahoma city"
   • Nickname only    → "thunder"

7. SPORT & LEAGUE:
   • Sport            → "basketball"
   • League           → "nba"

8. POSITION — if confirmed:
   • Full position    → "small forward"
   • Abbreviation     → "sf"

9. GRADING — only if card IS graded (see flags):
   • Company + grade          → "{company} {grade_val or 'X'}"
   {"• 'gem mint'             — because grade = 10" if is_gem_mint else "   (gem mint: skip — grade ≠ 10)"}
   {"• 'mint'                 — because grade = 9"  if is_mint     else "   (mint: skip — grade ≠ 9)"}
   • Company alone            → "{company}"
   • "{company} graded"
   {"• Cert tag               → '" + company + " " + cert_val + "'" if cert_val else "   (no cert number)"}

10. RAW CONDITION — only if card is raw AND condition explicitly stated:
    {"• '" + str(raw_condition).lower() + "', '" + _expand_condition(str(raw_condition)) + "'" if raw_condition and not is_graded else "   (skip)"}

11. SPECIAL FEATURES — each only if flag is ✓:
    {"• 'signed', 'autograph', 'auto', player + ' auto'" if has_auto else "   autograph: skip"}
    {"• 'patch', 'patch card', 'jersey card', 'relic', 'game used', 'memorabilia'" if has_patch else "   patch/jersey: skip"}
    {"• '" + parallel_name + "', shorter variant (e.g. just 'gold' or 'refractor')" if has_parallel else "   parallel: skip"}
    {"• 'numbered', 'serial numbered', '" + serial_val + "'" if has_serial else "   serial: skip"}
    {"• 'ssp', 'short print', player + ' ssp'" if is_ssp else "   ssp: skip"}
    {"• 'photo variation', player + ' photo variation'" if is_photo_var else "   photo variation: skip"}
    {"• 'case hit', player + ' case hit'" if is_case_hit else "   case hit: skip"}

12. LOT TAGS — only if this IS a lot (see flags):
    {"• 'card lot', '" + str(sport).lower() + " card lot', 'graded lot', 'psa lot', 'vintage lot', 'lot of " + str(lot_count or '') + "'" if is_lot else "   (skip — single card)"}

13. HIGH-INTENT MULTI-WORD COMBOS — generate at least 10, these matter most:
    • Year + brand + player              → "2025 topps chrome knueppel"
    {"• Year + brand + player + rc       — only if rc confirmed" if is_rookie else ""}
    • Player + team                      → "knueppel thunder"
    • Player + sport                     → "knueppel basketball"
    • Player + year                      → "knueppel 2025"
    • Brand + player                     → "topps chrome knueppel"
    {"• Player + company + grade         — only if graded" if is_graded else ""}
    {"• Player + rc + grade              — only if both confirmed" if is_graded and is_rookie else ""}
    • Year + sport                       → "2025 basketball card"
    {"• Player + ssp                     → player + ' ssp'" if is_ssp else ""}
    {"• Player + photo variation" if is_photo_var else ""}

14. ERA / DECADE — based on year:
    {"• 'pre-war cards', 'vintage baseball', decade tag" if is_vintage else ""}
    {"• '80s basketball', '1980s cards', 'vintage basketball card'" if is_eighties else ""}
    {"• '90s basketball', '1990s basketball cards'" if is_nineties else ""}
    {"• 'modern basketball card', '2020s basketball'" if is_modern else ""}

15. COLLECTOR / LEGACY — only for confirmed HOF / legendary players:
    • "hall of fame", "hof", player + " hof"
    • "legend", player + " legend"
    • "goat" — ONLY for Jordan, LeBron, Ruth, Brady, Gretzky etc.

16. EXTRA KEYWORDS — mine everything not yet covered:
    • Anything in the extra_keywords list above
    • Any specific detail from description or subtitle
    • Any text from card image the buyer might search
    • Insert/parallel sub-names (e.g. "fanatical", "patented", specific insert set names)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STYLE RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• All lowercase, 1–5 words per tag
• No hashtags, no punctuation except hyphens and spaces
• No duplicates
• No generic filler: "sports card", "collectible", "trading card"
  UNLESS those exact words appear in the listing title/description

Return ONLY the JSON array:
["kon knueppel", "knueppel", "kon", "2025", "topps chrome", ...]"""


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_tags(
    product: dict[str, Any],
    store_base_url: str = "",
    *,
    client: OpenAI | None = None,
    deployment: str | None = None,
) -> list[str]:
    """
    Three-pass tag generation:
      Pass 1 — OCR ALL images (temperature=0, merged)
      Pass 2 — Extract facts from title/subtitle/description + category (temperature=0)
      Pass 3 — Generate 40-50 grounded buyer-search tags from merged facts
    """
    deployment_name = (
        deployment
        or os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        or AZURE_OPENAI_DEPLOYMENT
    ).strip()
    if not deployment_name:
        print("    Error: Missing AZURE_OPENAI_DEPLOYMENT")
        return []

    openai_client = client
    if openai_client is None:
        endpoint = (os.getenv("AZURE_OPENAI_ENDPOINT", "") or AZURE_OPENAI_ENDPOINT).strip()
        api_key   = (os.getenv("AZURE_OPENAI_API_KEY", "")  or AZURE_OPENAI_API_KEY).strip()
        if not endpoint or not api_key:
            print("    Error: Missing Azure OpenAI endpoint or API key")
            return []
        if not endpoint.endswith("/"):
            endpoint += "/"
        openai_client = OpenAI(api_key=api_key, base_url=endpoint)

    product_id  = product.get("id", "")
    title       = _clean_text(product.get("title") or product.get("name"))
    subtitle    = _clean_text(product.get("subtitle"))
    description = _clean_text(product.get("description"))
    category    = product.get("category") or {}
    image_urls  = _extract_all_image_urls(product, store_base_url)

    print(f"    [{product_id}] Images found: {len(image_urls)}")

    # ── PASS 1 — OCR all images ──────────────────────────────────────────────
    ocr: dict[str, Any] = {}
    if image_urls:
        print(f"    [{product_id}] Pass 1: OCR {len(image_urls)} image(s)...")
        ocr = _ocr_all_images(openai_client, deployment_name, image_urls)
    else:
        print(f"    [{product_id}] Pass 1: No images — skipping OCR")

    # ── PASS 2 — Text + category extraction ─────────────────────────────────
    print(f"    [{product_id}] Pass 2: Extracting facts from text + category...")
    text_facts = _extract_text_facts(
        openai_client, deployment_name, title, subtitle, description, category
    )

    # ── Merge all sources ────────────────────────────────────────────────────
    merged = _merge_facts(ocr, text_facts)
    # Carry through fields that only come from text_facts
    for passthrough in ("is_lot", "lot_count", "era", "card_type"):
        if passthrough not in merged and text_facts.get(passthrough) is not None:
            merged[passthrough] = text_facts[passthrough]
    print(f"    [{product_id}] Merged: {json.dumps({k: v for k, v in merged.items() if not k.endswith('_source')}, ensure_ascii=False)}")

    # ── PASS 3 — Tag generation ───────────────────────────────────────────────
    print(f"    [{product_id}] Pass 3: Generating tags...")
    tag_prompt = _build_tag_prompt(title, subtitle, description, category, merged)

    def _request_tags(use_images: bool) -> list[str]:
        content: list[dict[str, Any]] = [{"type": "text", "text": tag_prompt}]
        if use_images:
            for url in image_urls:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": url, "detail": "high"},
                })
        response = openai_client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": content}],
            temperature=TAG_TEMPERATURE,
            max_completion_tokens=TAG_MAX_TOKENS,
        )
        raw = (response.choices[0].message.content or "").strip()
        return _normalize_tags(_parse_json_list(raw))

    try:
        tags = _request_tags(use_images=bool(image_urls))
        print(f"    [{product_id}] ✓ Generated {len(tags)} tags")
        return tags

    except Exception as e:
        if image_urls:
            try:
                print(f"    [{product_id}] Warning: images failed in tag pass, retrying text-only...")
                tags = _request_tags(use_images=False)
                print(f"    [{product_id}] ✓ Generated {len(tags)} tags (text-only fallback)")
                return tags
            except Exception as retry_error:
                print(f"    [{product_id}] Retry error: {retry_error}")
                return []
        print(f"    [{product_id}] Error: {e}")
        return []