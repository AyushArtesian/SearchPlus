# Sports Card Tagger - Complete Documentation

A production-ready Python project that:
- Fetches CollectorInvestor auction listings by event
- AI-enriches them with buyer-search tags (40-50 per product)
- **Automatically posts tags back to Collector Investor API**
- Exposes a searchable REST API

Complete end-to-end automation: **Fetch → Tag → Post → Search** in a single pipeline run.

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Project Overview](#project-overview)
3. [Complete Workflow](#complete-workflow)
4. [Directory Structure](#directory-structure)
5. [Installation & Setup](#installation--setup)
6. [Configuration](#configuration)
7. [API Reference](#api-reference)
8. [CLI Usage](#cli-usage)
9. [Examples](#examples)
10. [Architecture](#architecture)
11. [Tag Posting System](#tag-posting-system)
12. [Troubleshooting](#troubleshooting)

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your Azure OpenAI credentials

# 3. Run API server
uvicorn main:app --reload --port 8000

# 4. Complete pipeline: Fetch → Tag → Post (all in one command!)
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "offset": 0,
    "limit": 25,
    "event_id": "4053663"
  }'

# Response includes both tagging AND tag-posting results:
# {
#   "success": true,
#   "fetched": 25,
#   "products_tagged": 25,
#   "total_tags": 1250,
#   "tags_posted": 25,
#   "tags_posted_failed": 0
# }

# 5. Search for cards
curl "http://localhost:8000/search?q=patrick%20ewing"
```

---

## 🎯 Project Overview

**Sports Card Tagger** is an **end-to-end AI-powered product enrichment system** that automates discovery, tagging, AND posting of sports collectibles. It combines:

- **API Fetching**: Retrieves listings from Collector Investor API (with RWX_SECURE authentication)
- **Image Recognition**: OCR on card photos to extract text (player, year, card number, etc.)
- **Text Analysis**: Structured extraction from titles, descriptions, and metadata
- **Intelligent Merging**: Combines visual + textual data with smart conflict resolution
- **Tag Generation**: Creates 40-50 buyer-search tags based on verified facts
- **Automated Posting**: Sends generated tags back to Collector Investor API
- **Full-Text Search**: REST API for searching products by tags, title, description

### Key Features

✅ **Event-Based Fetching** — Download listings by EventID from Collector Investor  
✅ **RWX_SECURE Authentication** — Built-in HMAC-SHA256 request signing  
✅ **Multi-Image OCR** — Processes up to 4 images per product  
✅ **Smart Fact Merging** — Combines OCR + text with intelligent conflict resolution  
✅ **AI Tag Generation** — Creates 40-50 contextual buyer-search tags  
✅ **Automatic Posting** — Posts tags directly to Collector Investor API  
✅ **Progress Tracking** — Only posts tags for newly generated products (no duplicates)  
✅ **REST API** — FastAPI with auto-generated Swagger docs  
✅ **Local Persistence** — JSON database (no external DB required)  
✅ **Modular Architecture** — Clean separation: fetch → normalize → tag → store → post → search  

### Complete Workflow

```
CollectorInvestor → Fetch Listings → Tag Products → Post Tags Back
                                          ↓
                                    Store in DB
                                          ↓
                                   Available for
                                    Search API
```

---

## 🔄 Complete Workflow

### Step-by-Step Pipeline

**1. Fetch Listings (API)**
```
GET /api/listing/search/{offset}/{limit}?EventID={event_id}
```
- Authenticates with RWX_SECURE headers
- Fetches new/updated listings from specific event
- Normalizes response to standard product format

**2. Generate Tags (AI)**
- **Pass 1**: OCR on card images (extract text from photos)
- **Pass 2**: Extract facts from title, description, metadata
- **Pass 3**: Merge OCR + text data intelligently
- **Pass 4**: Generate 40-50 contextual buyer-search tags

**3. Store in DB**
- Saves products with generated tags to `data/products.json`
- Accumulates products over multiple runs
- Each product stored once with tags

**4. Post Tags to API (NEW!)**
- Transforms product tags to Collector Investor format: `{"Items": {"ListingID": "123", "Tags": "tag1, tag2, ..."}}`
- POSTs to: `https://bid.collectorinvestorauctions.com/api/listing/createtags`
- **Only posts newly generated tags** (from current pipeline run)
- **Not re-posting old tags** from previous runs

**5. Search & Discover**
- Users can search products by tags, title, description
- Weighted relevance scoring

### Data Flow Example

```json
INPUT (from Collector Investor API):
{
  "id": 4607163,
  "title": "2025 Topps Chrome Kon Knueppel RC Fanatical Photo Variation SSP",
  "description": "You will receive the exact item(s) pictured. Happy bidding!",
  "image_url": "https://ciaimages.blob.core.windows.net/..."
}

AFTER TAGGING:
{
  "id": 4607163,
  "title": "2025 Topps Chrome Kon Knueppel RC Fanatical Photo Variation SSP",
  "tags": [
    "kon knueppel",
    "2025 topps chrome",
    "rookie card",
    "rc",
    "photo variation",
    "ssp",
    "charlotte hornets",
    "nba",
    ... (40-50 total)
  ]
}

POSTED TO API AS:
{
  "Items": {
    "ListingID": "4607163",
    "Tags": "kon knueppel, 2025 topps chrome, rookie card, rc, ..."
  }
}
```

---

## 🏗️ Three-Pass Pipeline Architecture

The tagger uses a deterministic three-pass approach to maximize data quality:

```
                       Product with Images
                              ↓
                    ┌─────────────────────┐
                    │   PASS 1: OCR       │
                    │  (temperature=0)    │
                    │                     │
                    │ Extract text from   │
                    │ up to 4 card images │
                    │ using Azure Vision  │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  PASS 2: TEXT+CAT   │
                    │  (temperature=0)    │
                    │                     │
                    │ Extract facts from: │
                    │ • Title             │
                    │ • Subtitle          │
                    │ • Description       │
                    │ • Category metadata │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  FACT MERGING       │
                    │                     │
                    │ Combine OCR +       │
                    │ structured text:    │
                    │ • Scalars: 1st wins │
                    │ • Booleans: any=yes │
                    │ • Lists: union      │
                    └──────────┬──────────┘
                               ↓
                    ┌─────────────────────┐
                    │  PASS 3: TAG GEN    │
                    │ (temperature=0.2)   │
                    │                     │
                    │ Generate 40-50      │
                    │ buyer-search tags   │
                    │ from verified facts │
                    └──────────┬──────────┘
                               ↓
                         Tagged Product
                    {40-50 search tags}
```

### Pass 1: Multi-Image OCR (temperature=0)

- Extracts up to 4 images from `product["image_urls"]` array
- Runs Vision OCR on each image independently (parallel-ready)
- Merges results using intelligent strategy:
  - **Scalar fields** (player_name, year, card_set): First non-null wins
  - **Boolean fields** (autograph, patch_jersey): True if ANY image says True
  - **List fields** (extra_keywords): Union of all values
- Returns: `{ player_name, year, card_set, card_number, team, ... }`

### Pass 2: Text + Category Extraction (temperature=0)

- Parses title, subtitle, description for facts
- Incorporates category metadata (sport, era, type)
- Recognizes abbreviations (RC=rookie, NM=near mint, PSA, BGS, etc.)
- Handles lot listings and condition grading
- Returns: `{ player_name, year, card_set, is_lot, lot_count, ... }`

### Fact Merging

- Combines OCR + text results with source attribution
- Example: `{ "grade": "10", "grade_source": "image" }` or `{ "team": "Lakers", "team_source": "text" }`
- Prioritizes visual data (OCR) for physical attributes (grading, condition)
- Falls back to text for metadata not visible on card

### Pass 3: Tag Generation (temperature=0.2)

- Uses merged facts + original listing text as context
- Builds detailed facts block with source attribution for transparency
- Generates confirmed-flag rules (@✓ @✗) to control tag inclusion
- Produces 40-50 unique lowercase buyer-search tags
- Includes fallback to text-only if images fail

---

## 📁 Directory Structure

```
sports-card-tagger/
├── src/
│   ├── __init__.py
│   ├── config.py                      # Centralized configuration
│   ├── models.py                      # Pydantic request/response models
│   ├── storage.py                     # JSON database layer
│   └── services/
│       ├── __init__.py
│       ├── collector_investor.py      # CollectorInvestor API fetch client
│       ├── CollectorInvestorTags.py   # CollectorInvestor API tag posting client
│       ├── tagger_service.py          # OpenAI tag generation engine
│       └── search_service.py          # Full-text search implementation
├── data/                              # Generated locally (not committed)
│   └── products.json                  # Product database with tags
├── main.py                            # FastAPI application (main entry point)
├── app.py                             # Alternative entry point
├── CollectorInvestor.py               # Standalone CLI for fetching
├── requirements.txt                   # Python dependencies
├── .env                               # Environment variables (local, not committed)
├── .env.example                       # Example env template
├── .gitignore                         # Git ignore rules
└── Readme.md                          # This file
```

### Key Services

| File | Purpose |
|------|---------|
| `src/services/collector_investor.py` | Fetches listings from Collector Investor API with RWX_SECURE auth |
| `src/services/CollectorInvestorTags.py` | Posts generated tags to Collector Investor API |
| `src/services/tagger_service.py` | OpenAI-powered tag generation (4-pass pipeline) |
| `src/services/search_service.py` | Full-text search with weighted relevance scoring |
| `main.py` | FastAPI routes: /pipeline/run, /search, /products, /tags/post-all |

---

## 🔧 Installation & Setup

### Prerequisites

- **Python 3.9+** — For type hints and async support
- **Azure OpenAI GPT-4** — API endpoint, deployment name, and API key
- **Internet Connection** — To fetch from CollectorInvestor API and call OpenAI

### Step 1: Clone & Navigate

```bash
cd sports-card-tagger
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your Azure OpenAI credentials
# Example:
# AZURE_OPENAI_ENDPOINT=https://my-resource.openai.azure.com/openai/v1/
# AZURE_OPENAI_DEPLOYMENT=gpt-4-deployment
# AZURE_OPENAI_API_KEY=your-api-key-here
```

### Step 5: Verify Installation

```bash
# Test imports
python -c "from src.services.tagger_service import generate_tags; print('✓ Setup OK')"

# Start API server (should show "Uvicorn running on http://127.0.0.1:8000")
uvicorn main:app --reload --port 8000
```

---

## ⚙️ Configuration

All configuration is centralized in `src/config.py` with environment variable overrides.

### Required Environment Variables

```env
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/openai/v1/
AZURE_OPENAI_DEPLOYMENT=<deployment-name>
AZURE_OPENAI_API_KEY=<your-api-key>
```

### OCR & Tag Generation Settings

| Setting | Value | Purpose |
|---------|-------|---------|
| `MAX_OCR_IMAGES` | 4 | Max images to OCR per product |
| `TAG_TEMPERATURE` | 0.2 | Creativity for tag generation (0=deterministic, 1=creative) |
| `TAG_MAX_TOKENS` | 320 | Max tokens for tag response |
| `TAG_COUNT_MIN` | 12 | Minimum tags per product |
| `TAG_COUNT_MAX` | 20 | Maximum tags per product (informational) |

### Other Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| `PRODUCTS_DB` | `data/products.json` | Product database location |
| `CollectorInvestor USERNAME` | From `.env` | API authentication |
| `CollectorInvestor BASE64_TOKEN` | From `.env` | HMAC signing token |
| `CollectorInvestor API_URI_TEMPLATE` | (in config) | Endpoint URL template |

### Accessing Config in Code

```python
from src.config import (
    MAX_OCR_IMAGES, TAG_TEMPERATURE, TAG_MAX_TOKENS,
    AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY
)
```

---

## 🔄 Workflows

### Workflow 1: Complete Pipeline (Recommended)

**Best for:** Production; end-to-end automation; single command does everything

**Complete workflow in one API call:**

```bash
# Fetch → Tag → Save → Post Tags (all-in-one!)
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "offset": 0,
    "limit": 25,
    "timeout": 45,
    "event_id": "4053663",
    "status": ""
  }'
```

**Response includes tagging AND posting results:**
```json
{
  "success": true,
  "fetched": 25,
  "products_tagged": 25,
  "total_tags": 1250,
  "tags_posted": 25,
  "tags_posted_failed": 0
}
```

**What happens internally:**
1. ✅ Fetches 25 new listings from event 4053663
2. ✅ Generates 40-50 tags for each (AI-powered)
3. ✅ Saves to database (`data/products.json`)
4. ✅ Posts tags to Collector Investor API
5. ✅ Only 25 newly-tagged products are posted (not 100 old ones!)

**Search the tagged products:**
```bash
curl "http://localhost:8000/search?q=patrick%20ewing"
```

**Benefits:**
- Single command does everything
- Only posts NEW tags (no duplicates)
- Automatic retry on failures
- Full result tracking
- Scalable to thousands of products

**Key Parameter: `event_id`**
- Filter by Collector Investor Event ID
- Example: `"4053663"` fetches only listings from that event
- Optional: leave empty to fetch all listings

---

### Workflow 2: Manual CLI (Batch/Development)

**Best for:** Development; debugging; one-off batches

**Step 1: Fetch listings**

```bash
python CollectorInvestor.py \
  --offset 0 \
  --limit 50 \
  --event-id 4053663 \
  --output batch_raw.json \
  --timeout 45
```

**Step 2: Products are tagged (if started API)**

```bash
# Via API
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"limit": 50, "event_id": "4053663"}'
```

**Step 3: Search or post separately**

```bash
# Just post tags (manually)
curl -X POST http://localhost:8000/tags/post-all
```

---

### Workflow 3: Post-Only (Tags Already Generated)

**Best for:** Reposting old tags; batch updates

```bash
# Post ALL tags from database to Collector Investor
# (includes both old and new tags)
curl -X POST http://localhost:8000/tags/post-all \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "success": true,
  "total": 100,
  "successful": 98,
  "failed": 2,
  "results": [
    {
      "listing_id": "4607163",
      "title": "2025 Topps Chrome Kon Knueppel RC...",
      "status_code": 200,
      "success": true,
      "response": "API response text"
    }
  ]
}
```

---

## 📡 API Reference

### Base URL

```
http://localhost:8000
```

### Health Check

```http
GET /
```

**Response:**
```json
{
  "status": "ok",
  "products_in_db": 1234
}
```

---

### 1. Complete Pipeline: Fetch → Tag → Post

```http
POST /pipeline/run
Content-Type: application/json

{
  "offset": 0,
  "limit": 25,
  "timeout": 45,
  "event_id": "4053663",
  "status": ""
}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `offset` | int | No (default: 0) | Starting position in listing results |
| `limit` | int | No (default: 25) | Number of listings to fetch |
| `timeout` | int | No (default: 45) | HTTP timeout in seconds |
| `event_id` | string | No | Filter by Collector Investor Event ID (e.g., "4053663") |
| `status` | string | No | Filter by listing status (e.g., "Active", "Draft") |

**Response:**
```json
{
  "success": true,
  "fetched": 25,
  "products_tagged": 25,
  "total_tags": 1250,
  "tags_posted": 25,
  "tags_posted_failed": 0
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if all steps succeeded |
| `fetched` | int | Listings fetched from API |
| `products_tagged` | int | Products with tags generated |
| `total_tags` | int | Total tags across all products |
| `tags_posted` | int | Products successfully posted to Collector Investor |
| `tags_posted_failed` | int | Products that failed posting |

**Error Response:**
```json
{
  "success": false,
  "detail": "Error message"
}
```

---

### 2. Post All Tags to Collector Investor

```http
POST /tags/post-all
Content-Type: application/json
```

**Purpose:** Post ALL product tags from database to Collector Investor API

**Response:**
```json
{
  "success": true,
  "total": 150,
  "successful": 148,
  "failed": 2,
  "results": [
    {
      "listing_id": "4607163",
      "title": "2025 Topps Chrome Kon Knueppel RC...",
      "status_code": 200,
      "success": true,
      "response": ""
    },
    {
      "listing_id": "4606975",
      "title": "2025 Topps Chrome Anthony Edwards...",
      "status_code": 200,
      "success": true,
      "response": ""
    }
  ]
}
```

**Response Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | True if all postings succeeded |
| `total` | int | Total products with tags |
| `successful` | int | Products successfully posted |
| `failed` | int | Products that failed posting |
| `results` | array | Detailed result for each product |

**Important Notes:**
- ⚠️ Posts **ALL tags** from database (including old ones)
- Use `/pipeline/run` for new products only (automatic tag posting)
- Use `/tags/post-all` for manual reposting or batch updates
- Authentication: RWX_SECURE signing handled automatically

---

### Search Products

```http
GET /search?q=patrick+ewing
```

**Parameters:**
- `q` (required): Search query
- `limit` (optional): Max results (default: 50)

**Response:**
```json
{
  "query": "patrick ewing",
  "total": 3,
  "results": [
    {
      "id": 4453442,
      "title": "1986 Fleer #32 Patrick Ewing RC NM",
      "score": 12,
      "tags": ["patrick ewing", "ewing", "rc", "rookie card"]
    }
  ]
}
```

---

### Get All Products

```http
GET /products
```

**Response:** Array of all products with tags

---

### Get Product by ID

```http
GET /products/{product_id}
```

**Response:** Full product details including tags

---

### Get Product Tags Only

```http
GET /products/{product_id}/tags

---

## 🏷️ Tag Posting System

The Sports Card Tagger now automatically posts generated tags back to the Collector Investor API. Here's how it works:

### Architecture

```
┌─────────────────────────────────┐
│  Generated Product with Tags    │
│  {                              │
│    "id": "4607163",             │
│    "tags": ["tag1", "tag2", ...]│
│  }                              │
└────────────┬────────────────────┘
             │
             ↓ (Transform format)
┌─────────────────────────────────┐
│  API Format                     │
│  {                              │
│    "Items": {                   │
│      "ListingID": "4607163",    │
│      "Tags": "tag1, tag2, ..." │
│    }                            │
│  }                              │
└────────────┬────────────────────┘
             │
             ↓ (Sign with RWX_SECURE)
┌─────────────────────────────────┐
│  POST /api/listing/createtags   │
│  Headers:                       │
│  - Authorization: RWX_SECURE... │
│  - Date: RFC1123                │
│  - Content-MD5: hash            │
└────────────┬────────────────────┘
             │
             ↓ (Collector Investor API)
┌─────────────────────────────────┐
│  Tags Added to Listing          │
│  Now searchable by buyers!      │
└─────────────────────────────────┘
```

### Key Features

**1. Smart Posting (No Duplicates)**

- `/pipeline/run` posts only **newly generated tags** from current run
- Only the 25 new products are posted, not all 100 in database
- Subsequent runs only post new products
- **No accidental re-posting of old tags**

**2. Batch Posting**

- `/tags/post-all` posts **all tags** from database
- Use for manual batch updates or reposting
- Helpful if API connection was lost previously

**3. RWX_SECURE Authentication**

- Uses HMAC-SHA256 signing (already configured)
- Content-MD5 hashing for request integrity
- RFC1123 date headers
- Credentials from `.env` (no hardcoding)

**4. Error Handling**

- Individual product failures don't block others
- Detailed result tracking per product
- HTTP status codes and response text captured
- Easy debugging via results array

### Format Transformation

**Input (from tagger):**
```python
product = {
    "id": "4607163",
    "title": "2025 Topps Chrome Kon Knueppel RC...",
    "tags": [
        "kon knueppel",
        "2025 topps chrome",
        "rookie card",
        "rc",
        ...
    ]
}
```

**Transformation:**
```python
json_body = {
    "Items": {
        "ListingID": product["id"],  # "4607163"
        "Tags": ", ".join(product["tags"])  # "kon knueppel, 2025 topps chrome, rookie card, rc, ..."
    }
}
```

**Output (to API):**
```json
{
  "Items": {
    "ListingID": "4607163",
    "Tags": "kon knueppel, 2025 topps chrome, rookie card, rc, fanatical, photo variation, ssp, nba, basketball, charlotte hornets, 2025, topps, ..."
  }
}
```

### Endpoint Details

**Collector Investor API Endpoint:**
```
POST https://bid.collectorinvestorauctions.com/api/listing/createtags
Authorization: RWX_SECURE {username}:{signature}
Date: Wed, 15 Apr 2026 06:00:40 GMT
Content-MD5: {base64_md5_hash}
Content-Type: application/json

{"Items": {"ListingID": "4607163", "Tags": "tag1, tag2, ..."}}
```

### Monitoring & Debugging

**View posting results:**

```bash
# From /pipeline/run response
{
  "tags_posted": 25,        # ✓ Successfully posted
  "tags_posted_failed": 0   # ✗ Failed to post
}

# From /tags/post-all detailed results
{
  "results": [
    {
      "listing_id": "4607163",
      "title": "2025 Topps Chrome Kon Knueppel RC...",
      "status_code": 200,
      "success": true
    },
    {
      "listing_id": "4606975",
      "status_code": 503,     # ← Server error
      "success": false,
      "response": "Service Unavailable"
    }
  ]
}
```

**Enable detailed logging:**

```python
# In main.py, the pipeline function prints:
print("Posting tags to Collector Investor API...")

# For each product:
print(f"✓ [4607163] 2025 Topps Chrome... - Success")
print(f"✗ [4606975] 2025 Topps Chrome... - Status: 503")

# Summary:
print(f"Tags posted: 25 successful, 0 failed")
```

### Troubleshooting Tag Posting

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Bad credentials | Check `.env` USERNAME and BASE64_TOKEN |
| 403 Forbidden | Signature mismatch | Verify HMAC-SHA256 signing in code |
| 404 Not Found | Invalid ListingID | Ensure product IDs are correct |
| 400 Bad Request | Malformed Tags string | Check tags format (comma-separated) |
| 503 Server Error | API temporarily down | Retry with `/tags/post-all` later |

---

## 🔍 Search Algorithm

The search engine ranks results by relevance using a weighted scoring system:

| Source | Points | Example |
|--------|--------|---------|
| Tag exact match | +2 | Query "patrick ewing" matches tag "patrick ewing" |
| Title match | +5 | Query "patrick" in "1986 Fleer #32 **Patrick** Ewing RC" |
| Subtitle match | +2 | Query "vintage" in subtitle "DoubleD Vintage Cards" |
| Description match | +1 | Query "rookie" in description |
| Category match | +1 | Query "basketball" matches category sport |

### Example Scoring

**Query:** `patrick ewing`  
**Product:** `1986 Fleer #32 Patrick Ewing RC NM`

```
Tags contain "patrick ewing"     → +2
Title contains "Patrick"          → +5
Title contains "Ewing"            → +5
Description contains "rookie"     → +1
                          ━━━━━━━━━━━
                   Total Score:   13
```

### Sorting

Results sorted by score descending (highest-relevance first). Ties resolved by product ID ascending.

---

## 🚀 Advanced: Three-Pass Pipeline Details

This section explains the three-pass pipeline's internals for debugging and optimization.

### Pass 1: Multi-Image OCR

#### Input

- `product["image_urls"]` (list) — Primary source for image URLs
- `product["image_url"]` (string) — Fallback if image_urls not present
- Maximum: 4 images processed (configurable via `MAX_OCR_IMAGES`)

#### OCR Prompt

The OCR prompt (temperature=0 for repeatability) asks GPT-4 Vision to extract:

```
{
  "player_name": "exact name as printed on card",
  "year": "year as printed (e.g. 1986)",
  "card_set": "brand name as printed (e.g. Fleer, Topps, Prizm)",
  "card_number": "card number if visible (e.g. 32, #32)",
  "team": "team name as printed",
  "position": "position as printed or abbreviated",
  "sport": "Basketball, Baseball, Football, or Hockey",
  "manufacturer": "manufacturer if different from set",
  "parallel_insert": "parallel or insert name (e.g. Gold Refractor)",
  "serial_number": "serial number if printed (e.g. 45/100)",
  "autograph": true/false,
  "patch_jersey": true/false,
  "grading_company": "PSA, BGS, SGC, or CSG if sealed",
  "grade": "grade number on slab (e.g. 10, 9.5)",
  "cert_number": "cert number on slab label",
  "other_visible_text": ["any other text not captured above"]
}
```

#### Merging Strategy for Multi-Image Results

When multiple images are processed, results are merged as follows:

```python
# Scalar fields (string/number)
# Strategy: First non-null value wins (front image priority)
merged["player_name"] = ocr_results[0].get("player_name") or \
                        ocr_results[1].get("player_name") or ...

# Boolean fields (autograph, patch_jersey)
# Strategy: True if ANY image says True (conservative inclusion)
merged["autograph"] = any(r.get("autograph") for r in ocr_results)

# List fields (extra_keywords)
# Strategy: Union of all values (no duplicates)
merged["extra_keywords"] = []
seen = set()
for result in ocr_results:
  for keyword in result.get("extra_keywords", []):
    if keyword not in seen:
      merged["extra_keywords"].append(keyword)
      seen.add(keyword)
```

#### Image Order Recommendations

Optimal ordering for multi-image products:

1. **Front of card** — Most information (player, year, set, condition)
2. **Back of card** — Statistics, card number, copyright year
3. **Graded slab** — Grade, cert number, grading company
4. **Error/variation** — Special issue text

---

### Pass 2: Text + Category Extraction

#### Input

- `title` (str) — Product title
- `subtitle` (str) — Seller/collection name
- `description` (str) — Full listing description
- `category` (dict) — Metadata: sport, era, type, format

#### Text Extraction Prompt

The prompt (temperature=0) asks GPT-4 to parse facts from listing text:

```
RULES:
- Report ONLY what's explicitly stated
- Recognize abbreviations (RC=rookie, NM=near mint, PSA, BGS, etc.)
- Distinguish single cards vs. lot listings
- Extract condition if stated (NM, EX-MT, VG, etc.)
- Do NOT infer; use null for unknowns
```

#### Extracted Fields

```python
{
  # Card identifiers (from text)
  "player_name": "name if mentioned",
  "year": "year if mentioned",
  "card_set": "card set if mentioned",
  "card_number": "card number if mentioned",
  "team": "team if mentioned",
  
  # Card attributes
  "position": "position if mentioned",
  "parallel_insert": "parallel/insert name if mentioned",
  "serial_number": "serial number if mentioned",
  "raw_condition": "condition code if stated (NM, EX, VG, etc.)",
  
  # Grading info
  "grading_company": "PSA/BGS/SGC if explicitly mentioned",
  "grade": "grade number if stated",
  "cert_number": "cert number if mentioned",
  
  # Lot detection
  "is_lot": true/false,
  "lot_count": "number of cards if mentioned",
  
  # Category metadata
  "era": "era from category if useful",
  "card_type": "Raw or Graded from category",
  
  # Boolean features
  "autograph": true/false,
  "patch_jersey": true/false,
  
  # Extra keywords
  "extra_keywords": ["any specific searchable terms"]
}
```

---

### Fact Merging: OCR + Text

After Pass 1 and Pass 2, results are intelligently merged:

```python
merged = {}

# SHARED FIELDS: Scalars with "first wins" strategy
SHARED_FIELDS = [
  "player_name", "year", "card_set", "card_number", "team",
  "position", "sport", "manufacturer", "parallel_insert", "serial_number"
]

for field in SHARED_FIELDS:
  ocr_val = ocr.get(field)
  txt_val = text_facts.get(field)
  
  if ocr_val:          # Image source preferred
    merged[field] = ocr_val
    merged[f"{field}_source"] = "image"
  elif txt_val:        # Fall back to text
    merged[field] = txt_val
    merged[f"{field}_source"] = "text"
  else:
    merged[field] = None

# VISUAL PRIORITY FIELDS: Lower confidence if text-only
VISUAL_PRIORITY_FIELDS = [
  "grading_company", "grade", "cert_number"
]

for field in VISUAL_PRIORITY_FIELDS:
  ocr_val = ocr.get(field)
  txt_val = text_facts.get(field)
  
  if ocr_val:
    merged[field] = ocr_val
    merged[f"{field}_source"] = "image"
  elif txt_val:
    merged[field] = txt_val
    merged[f"{field}_source"] = "text_only"  # Lower confidence
  else:
    merged[field] = None

# BOOLEAN FIELDS: True if ANY source says True
BOOL_FIELDS = ["autograph", "patch_jersey"]

for field in BOOL_FIELDS:
  ocr_true = ocr.get(field) is True
  txt_true = text_facts.get(field) is True
  
  merged[field] = ocr_true or txt_true
  merged[f"{field}_source"] = (
    "image+text" if (ocr_true and txt_true)
    else "image" if ocr_true
    else "text" if txt_true
    else None
  )
```

---

### Pass 3: Tag Generation

The tag prompt includes explicit ✓/✗ flags to control which tags are generated. Tags are produced across 16 categories:

1. **Player Name** — Full, last, first variations
2. **Year** — Card year alone
3. **Card Set / Brand** — Brand, year+brand, brand+number combinations
4. **Card Number** — With/without hash, brand+number
5. **Rookie Tags** — "rookie card", "rc", combos with player/brand/year
6. **Team** — Full team, city, nickname
7. **Sport & League** — "basketball", "nba", etc.
8. **Position** — Full (small forward) + abbreviation (sf)
9. **Grading** — Only if card IS graded: "psa 10", "gem mint", "mint", etc.
10. **Raw Condition** — Only if raw + condition explicitly stated
11. **Special Features** — Each only if confirmed: autograph, patch, parallel, serial, SSP, photo variation, case hit
12. **Lot Tags** — Only if is_lot=True: "card lot", "basketball card lot", etc.
13. **High-Intent Multi-Word Combos** — 10+ combinations like "patrick ewing 1986 fleer"
14. **Era / Decade** — "vintage basketball", "80s basketball", "modern basketball card"
15. **Collector / Legacy** — For confirmed HOF/legendary players
16. **Extra Keywords** — Anything not captured above

**Tag Output Format:**
```json
[
  "patrick ewing",
  "ewing",
  "patrick",
  "1986",
  "1986 fleer",
  "fleer",
  "rookie card",
  "rc",
  ...
]
```

**Tag Count:** Target 40-50 tags generated

---

## 📋 Examples

### Example 1: Simple Card (Single Image)

**Input:**
```json
{
  "id": 4453442,
  "title": "1986 Fleer #32 Patrick Ewing RC NM",
  "subtitle": "DoubleD Vintage Basketball",
  "description": "Rookie card in near mint condition.",
  "image_url": "https://example.com/ewing.jpg",
  "image_urls": ["https://example.com/ewing.jpg"],
  "category": {"sport": "basketball", "era": "Vintage"}
}
```

**Pass 1 - OCR Extract:**
```json
{
  "player_name": "PATRICK EWING",
  "year": "1986",
  "card_set": "Fleer",
  "card_number": "32",
  "team": "New York Knicks",
  "position": "Center",
  "autograph": false,
  "patch_jersey": false,
  "grading_company": null
}
```

**Generated Tags (sample):**
```json
[
  "patrick ewing", "ewing", "patrick", "1986", "1986 fleer",
  "fleer", "rookie card", "rc", "patrick ewing rc", "#32",
  "knicks", "center", "nba", "basketball", "vintage basketball",
  "hall of fame", "hof", "80s basketball", "1980s", ...
]
```

---

### Example 2: Multi-Image Graded Card

**Input:**
```json
{
  "id": 4454100,
  "title": "PSA 10 GEM MINT 1986 Fleer #32 Patrick Ewing RC",
  "image_urls": [
    "https://example.com/front.jpg",
    "https://example.com/back.jpg",
    "https://example.com/slab.jpg"
  ]
}
```

**Pass 1 - Multi-Image OCR:**
- Image 0 (front): Extracts player, year, set, team
- Image 1 (back): Confirms year, card number
- Image 2 (slab): Extracts "PSA", grade "10", cert number

**Generated Tags Include:**
```json
[
  "psa 10", "gem mint", "psa graded", "patrick ewing psa 10",
  "1986 fleer ewing psa", "psa gem mint", "graded rc", ...
]
```

---

### Example 3: Multi-Card Lot

**Input:**
```json
{
  "id": 4455200,
  "title": "Basketball Card Lot: 25 Cards Including Vintage",
  "description": "Random assortment of 25 basketball cards from 1980s-2000s."
}
```

**Generated Tags Include:**
```json
[
  "basketball card lot", "card lot", "lot of 25", "25 cards",
  "basketball lot", "vintage basketball lot", "bulk sports cards", ...
]
```

---

## 🐛 Troubleshooting

### Issue: OCR Returns Empty Results

**Symptoms:** Tags seem generic; image data not reflected; logs show `[OCR merged] {}`

**Causes:**
1. Image URLs invalid or inaccessible
2. Images blurry or not sports cards
3. Azure OpenAI Vision quota exceeded
4. Network timeout fetching images

**Solutions:**
```bash
# 1. Check image URLs
python -c "
from src.services.tagger_service import _extract_all_image_urls
product = {'image_urls': ['https://...']}
print(_extract_all_image_urls(product))
"

# 2. Test Azure OpenAI Vision directly
python -c "
from openai import OpenAI
import os
client = OpenAI(
  api_key=os.getenv('AZURE_OPENAI_API_KEY'),
  base_url=os.getenv('AZURE_OPENAI_ENDPOINT')
)
response = client.chat.completions.create(
  model='gpt-4-deployment',
  messages=[{
    'role': 'user',
    'content': [
      {'type': 'text', 'text': 'What do you see?'},
      {'type': 'image_url', 'image_url': {'url': 'https://...'}}
    ]
  }],
  max_completion_tokens=100
)
print(response.choices[0].message.content)
"

# 3. Increase timeout
python tagger.py --input products.json --output result.json
# And check logs for timeout messages
```

---

### Issue: Tags Missing Specific Features

**Symptoms:** Product is graded (PSA 10) but tags don't include "psa", "gem mint", etc.

**Causes:**
1. OCR/text didn't extract grading_company/grade
2. Confirmed flag is ✗ (not confirmed)
3. Text extraction failed

**Debug Steps:**
```bash
# Check merged facts in logs
# Expected for graded card:
#   "grading_company": "PSA" (from image)
#   "grade": "10" (from image or text)

# If missing, run with verbose logging:
python -c "
from src.services.tagger_service import generate_tags
product = {
  'id': 123,
  'title': 'PSA 10 1986 Fleer Patrick Ewing RC',
  'image_urls': ['https://example.com/slab.jpg']
}
tags = generate_tags(product)
# Watch logs for [OCR merged], [TEXT], confirmed flags
"
```

---

### Issue: JSON Parse Errors in Tag Response

**Symptoms:** Logs show `Failed to parse JSON list` or `ValueError: No JSON array`

**Solutions:**
```python
# Lower temperature (closer to 0 = stricter JSON)
# In src/config.py:
TAG_TEMPERATURE = 0.1  # was 0.2

# Increase max tokens
TAG_MAX_TOKENS = 400  # was 320

# The fallback-retry logic handles this automatically:
# If image+text fails → retries with text-only
```

---

### Issue: Image Fetch Timeouts

**Symptoms:** Logs show `Failed: [Errno 11001] getaddrinfo failed`

**Solutions:**
```bash
# Increase timeout
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "offset": 0,
    "limit": 25,
    "timeout": 60
  }'
```

---

### Issue: Search Returns No Results

**Symptoms:** `/search?q=patrick+ewing` returns `{"total": 0, "results": []}`

**Solutions:**
```bash
# 1. Check DB
curl http://localhost:8000/products

# 2. Run pipeline to fetch & tag
curl -X POST http://localhost:8000/pipeline/run \
  -d '{"offset": 0, "limit": 10}'

# 3. Try broader query
curl "http://localhost:8000/search?q=basketball"
```

---

### Issue: Azure OpenAI Rate Limit Exceeded

**Symptoms:** Logs show `RateLimitError` or `429 Too Many Requests`

**Solutions:**
```bash
# 1. Reduce batch size
curl -X POST http://localhost:8000/pipeline/run \
  -d '{"offset": 0, "limit": 5}'

# 2. Add delays between requests
# 3. Contact Azure to increase TPM quota
```

---

## 💡 Best Practices

### 1. Organize Image URLs

```python
# Good: clear order
product["image_urls"] = [
  "https://example.com/front.jpg",      # 0: front
  "https://example.com/back.jpg",       # 1: back
  "https://example.com/slab.jpg"        # 2: slab/grade
]
```

OCR processes in order, so front should be first.

### 2. Ensure Fallback Image URLs

```python
# Always set both image_url (fallback) and image_urls (preferred)
product["image_url"] = "https://example.com/front.jpg"
product["image_urls"] = ["https://example.com/front.jpg", "https://example.com/back.jpg"]
```

### 3. Monitor OCR Quality

```bash
# Check logs for image:text:image+text balance
# Good:
#   [OCR merged] player_name: "PATRICK EWING" (image)
#   [TEXT] player_name: "Patrick Ewing" (text)
#   [Merged] player_name_source: image

# Bad:
#   [OCR merged] {} (empty OCR)
#   [TEXT] player_name: "Patrick Ewing"
#   [Merged] player_name_source: text (no image validation)
```

### 4. Batch Processing Strategy

```bash
# For large imports, batch by 10-25 products
for i in {0..1000..25}; do
  curl -X POST http://localhost:8000/pipeline/run \
    -d "{\"offset\": $i, \"limit\": 25}"
  sleep 5  # Avoid rate limits
done
```

### 5. Verify Tag Quality Post-Generation

```python
# Spot-check tags
from src.storage import load_products

products = load_products()
for p in products[:5]:
  print(f"\n{p['title']}")
  print(f"Tags ({len(p['tags'])}): {p['tags'][:10]}")
  
  # Expected: 40-50 tags, all lowercase, no duplicates
  assert len(p['tags']) >= 30, "Too few tags"
  assert all(t.islower() for t in p['tags']), "Non-lowercase found"
  assert len(set(p['tags'])) == len(p['tags']), "Duplicates found"
```

### 6. Populate Category Metadata

```python
# Category helps Pass 2 extract when text is ambiguous
product["category"] = {
  "sport": "basketball",
  "era": "Vintage",
  "type": "Graded",
  "format": "Single"
}
```

---

## 📚 Resources

- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Requests Library](https://requests.readthedocs.io/)

---

## 📄 License

This project is proprietary to Artesian Software Technologies.

---

**Last Updated:** 2026-04-15  
**Version:** 2.0 (Three-Pass OCR Pipeline)  
**Maintainer:** Ayush Mittal
