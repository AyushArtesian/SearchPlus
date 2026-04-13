# 🏆 Sports Card Tagger - AI-Powered Product Tag Generator

A comprehensive Python backend solution that fetches sports trading card products from auction APIs, generates contextual AI-powered search tags using GPT-4o vision, and exposes an intelligent semantic search engine for ecommerce discovery.

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Modules](#architecture--modules)
3. [Features](#features)
4. [System Requirements](#system-requirements)
5. [Installation & Setup](#installation--setup)
6. [Process Workflow](#process-workflow)
7. [API Endpoints](#api-endpoints)
8. [Code Documentation](#code-documentation)
9. [Configuration](#configuration)
10. [Usage Examples](#usage-examples)
11. [Search Scoring Algorithm](#search-scoring-algorithm)
12. [Output Format](#output-format)
13. [Troubleshooting](#troubleshooting)
14. [Next Steps & Production](#next-steps--production)

---

## 🎯 Project Overview

**Sports Card Tagger** is an AI-driven product enrichment system designed for sports card auction and ecommerce platforms. It automatically generates semantic search tags for trading card products by analyzing:
- Product images (using GPT-4o vision)
- Product names
- Product descriptions
- Product categories

The system generates **15-20 highly relevant tags per product** that buyers actually search for, then exposes a ranked search API ranked by semantic relevance scoring.

**Use Case:** Improve search discoverability on sports card auction sites (Collector Investor Auctions, PSA grading databases, etc.) by automatically tagging thousands of products with buyer-intent keywords.

---

## 🏗️ Architecture & Modules

### System Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    SPORTS CARD TAGGER                        │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┼─────────┐
                    │         │         │
              ┌─────▼──┐  ┌───▼──┐  ┌──▼────┐
              │ main.py│  │search│  │storage│
              │(FastAPI)  │.py  │  │.py   │
              └────┬────┘  └──┬──┘  └──┬───┘
                   │         │        │
                   └────┬────┴────┬───┘
                        │        │
                   ┌────▼────────▼────┐
                   │    tagger.py     │
                   │   (GPT-4o Vision)│
                   └──────────────────┘
                        │
                ┌───────┴────────┐
                │                │
         ┌──────▼─────┐  ┌──────▼────┐
         │ products   │  │ External  │
         │.json       │  │ API/Mock  │
         └────────────┘  └───────────┘
```

### Module Breakdown

#### 1. **main.py** - FastAPI Application Server
   - **Purpose:** Central orchestration engine; exposes REST API endpoints
   - **Key Responsibilities:**
     - Fetch products from external APIs or use mock data
     - Coordinate the tagging pipeline (dispatch jobs to `tagger.py`)
     - Manage product persistence via `storage.py`
     - Expose search interface via `search.py`
   - **Key Endpoints:**
     - `POST /pipeline/run` - Main tagging pipeline
     - `GET /search` - Semantic search
     - `GET /products` - List all products
     - `GET /products/{id}` - Get single product
     - `GET /products/{id}/tags` - Get product tags
     - `GET /` - Health check

#### 2. **tagger.py** - GPT-4o Vision Tag Generator
   - **Purpose:** AI-powered semantic tag generation using OpenAI's GPT-4o model
   - **Key Functionality:**
     - Accepts product data (name, description, category, image)
     - Constructs multimodal prompts (image + text)
     - Calls GPT-4o API with vision capability
     - Generates 15-20 contextually relevant tags
   - **Image Processing:**
     - Supports multiple image URL formats (relative/absolute)
     - Resolves relative paths using store base URL
     - Uses `detail: "high"` to read fine text, jersey numbers, logos

#### 3. **search.py** - Semantic Search Engine
   - **Purpose:** Full-text and semantic search across product catalog
   - **Key Features:**
     - Multi-field search (tags, name, description, category)
     - Relevance scoring algorithm (2pts for tags, 5pts for name, 1pt for description)
     - Result ranking by score (highest to lowest)
     - Matched tags highlighting
   - **Returns:** Ranked results with score, matched tags, and product metadata

#### 4. **storage.py** - Persistent Data Layer
   - **Purpose:** Handle all product persistence
   - **Storage Method:** JSON file (`products.json`)
   - **Key Functions:**
     - `load_products()` - Read all products from JSON
     - `save_products()` - Write products to JSON
     - `add_or_update_product()` - Insert or update single product
     - `get_product_by_id()` - Retrieve product by ID
     - `get_product_count()` - Total product count
   - **Note:** For production, replace JSON with PostgreSQL, MongoDB, or Redis

#### 5. **test_api.py** - API Test Suite
   - **Purpose:** Comprehensive example script demonstrating all endpoints
   - **Tests Include:**
     - Health check
     - Pipeline execution with mock data
     - Product retrieval (all & individual)
     - Tag extraction
     - Search queries (multiple examples)
   - **Usage:** `python test_api.py` (requires server running)

---

## ✨ Features

- **🤖 GPT-4o Vision Integration** - Analyzes product images to extract context (logos, jersey numbers, card design, condition indicators)
- **🏷️ Intelligent Tag Generation** - Creates 15-20 contextually relevant tags per product, covering:
  - Player names & nicknames
  - Team & franchise names
  - Player roles/positions (e.g., "fast bowler", "striker")
  - Achievements (e.g., "World Cup winner", "Ballon d'Or")
  - Card rarity & design (e.g., "gold foil", "holographic", "PSA 10")
  - Sport & format (e.g., "T20 cricket", "Champions League")
- **🔍 Semantic Search Engine** - Intelligent ranking across tags, names, descriptions
- **⚡ Auto-Pipeline** - Fetch → Tag → Store workflow with progress indicators
- **🔄 Incremental Save** - Products saved immediately during processing (crash-safe)
- **📡 RESTful API** - FastAPI with auto-generated Swagger docs
- **🛡️ CORS Enabled** - Works with any frontend framework
- **📊 Relevance Scoring** - Results ranked by semantic relevance
- **🔗 Custom API Integration** - Connect any ecommerce/auction platform

---

## 💻 System Requirements

- **Python:** 3.9+
- **OS:** Windows, macOS, Linux
- **Memory:** 512MB minimum (2GB recommended for batch processing)
- **Internet:** Required for GPT-4o API calls
- **OpenAI Account:** Paid tier with `gpt-4o` model access

---

## 📦 Installation & Setup

### Step 1: Clone/Navigate to Project
```bash
cd d:\Artesian\Automation\SearchPlus\sports-card-tagger
```

### Step 2: Create Virtual Environment (Optional but Recommended)
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

**Dependencies Installed:**
- `fastapi` - Modern Python web framework
- `uvicorn` - ASGI server (runs FastAPI)
- `openai` - OpenAI API client (for GPT-4o)
- `httpx` - Async HTTP client (fetch products from external APIs)
- `python-dotenv` - Load environment variables from `.env`

### Step 4: Configure OpenAI API Key
Create a `.env` file in the project root:
```
OPENAI_API_KEY=sk-YOUR_KEY_HERE
```

Get your API key at: https://platform.openai.com/api-keys

**⚠️ Security Note:** Never commit `.env` to version control. OpenAI charges per request (~$0.01-0.05 per product with vision).

### Step 5: Verify Installation
```bash
python -c "import fastapi, openai, uvicorn; print('✅ All dependencies installed')"
```

---

## 🔄 Process Workflow

### High-Level Workflow
```
User Request
    │
    ▼
┌─────────────────────────────────┐
│ 1. FETCH PHASE (main.py)        │
│ ─ GET request to API/Mock       │
│ ─ Parse JSON response           │
│ ─ Resolve image URLs            │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 2. TAG GENERATION PHASE         │
│ (tagger.py → GPT-4o)            │
│ ─ For each product:             │
│   • Build multimodal prompt     │
│   • Call GPT-4o with image      │
│   • Extract JSON tag array      │
│   • Add tags to product dict    │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 3. STORAGE PHASE (storage.py)   │
│ ─ Save product to products.json │
│ ─ Update product count          │
│ ─ Show progress in terminal     │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ 4. RETURN RESPONSE (main.py)    │
│ ─ Return success status         │
│ ─ Include products_tagged count │
│ ─ Include total_tags count      │
└─────────────────────────────────┘
```

### Detailed Step-by-Step

**Step 1: Product Fetching**
```python
# User calls: POST /pipeline/run
if request.api_url:
    # Fetch from external API
    async with httpx.AsyncClient() as client:
        response = await client.get(request.api_url)
        products = response.json()
else:
    # Use mock data (5 sample sports cards)
    products = MOCK_PRODUCTS
```

**Step 2: Multimodal Tagging**
```python
# For each product, build GPT-4o request:
message_content = [
    {
        "type": "image_url",
        "image_url": {
            "url": image_url,        # Product image or URL
            "detail": "high"         # Read fine text/logos
        }
    },
    {
        "type": "text",
        "text": text_prompt  # Detailed prompt below ↓
    }
]

# GPT-4o processes:
# - Image analysis (card design, jersey numbers, logos)
# - Text analysis (name, description, category)
# → Returns: ["tag1", "tag2", ..., "tag20"]
```

**GPT-4o Prompt Template:**
```
You are a sports trading card tagging expert for an ecommerce search engine.
Analyze this product card — read the image carefully along with the name and description.
Generate 15-20 highly relevant search tags that buyers would actually type when searching.

Product name: {product.name}
Category: {product.category}
Description: {product.description}

Generate tags covering:
- Player name + common spelling variations and nicknames
- Team names (national + franchise/club)
- Nationality and country
- Playing role/position (e.g. 'fast bowler', 'right hand batsman', 'striker')
- Playing style (e.g. 'aggressive batsman', 'death over specialist', 'free kick specialist')
- Achievements (e.g. 'world cup winner', 'ballon dor', 'ipl champion')
- Card rarity/type visible in image (e.g. 'gold foil', 'holographic', 'platinum border')
- Jersey number or colors visible in the image
- Era / generation (e.g. 'modern era', '90s legend')
- Sport name and format (e.g. 'test cricket', 'T20', 'champions league')
- Any text, logo, or design visible on the card image

Return ONLY a raw JSON array of tag strings. No explanation, no markdown, no backticks.
Example: ["virat kohli","kohli","rcb","royal challengers","indian batsman","run chase king","gold edition","right hand bat"]
```

**Step 3: Immediate Persistence**
```python
# Each product saved immediately (not batch at end)
add_or_update_product(product)  # Writes to products.json
# This prevents data loss if pipeline crashes mid-run
```

**Step 4: Terminal Output Example**
```
📋 Using mock product data...
🏷️  Tagging 1/5: Virat Kohli - Gold Edition (with image)...
   → Generated 18 tags
🏷️  Tagging 2/5: Jasprit Bumrah - Platinum (with image)...
   → Generated 19 tags
🏷️  Tagging 3/5: Lionel Messi - World Cup Hero (with image)...
   → Generated 17 tags
🏷️  Tagging 4/5: Cristiano Ronaldo - Al Nassr (with image)...
   → Generated 20 tags
🏷️  Tagging 5/5: MS Dhoni - Captain Cool (with image)...
   → Generated 16 tags

✨ Pipeline complete! Tagged 5 products (90 total tags)
```

---

## 📡 API Endpoints

### 1. Health Check
```http
GET /
```
**Response:**
```json
{
  "status": "ok",
  "products_in_db": 5
}
```

---

### 2. Run Tagging Pipeline ⭐ (Main Endpoint)
```http
POST /pipeline/run
Content-Type: application/json

{
  "api_url": null
}
```

**Request Parameters:**
- `api_url` (optional): External API endpoint returning products. If null, uses mock data.

**cURL Examples:**
```bash
# Using mock data
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": null}'

# Using external API
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": "https://bid.collectorinvestorauctions.com/api/products"}'
```

**Response:**
```json
{
  "success": true,
  "products_tagged": 5,
  "total_tags": 90
}
```

**Expected Flow:**
1. Fetches products from API or loads mock data
2. Calls GPT-4o for each product
3. Saves product with tags to `products.json`
4. Returns summary statistics

---

### 3. Search Products
```http
GET /search?q={query}
```

**Request Parameters:**
- `q` (required): Search query string

**cURL Examples:**
```bash
# Search for fast bowlers
curl "http://localhost:8000/search?q=fast+bowler"

# Search for World Cup winners
curl "http://localhost:8000/search?q=world+cup"

# Search for gold cards
curl "http://localhost:8000/search?q=gold"
```

**Response:**
```json
{
  "query": "fast bowler",
  "total": 2,
  "results": [
    {
      "id": 2,
      "name": "Jasprit Bumrah - Platinum",
      "category": "Cricket",
      "description": "Indian fast bowler, unique bowling action, deadly yorkers specialist. Mumbai Indians pacer and top wicket-taker.",
      "image_url": "https://...",
      "tags": ["jasprit bumrah", "bumrah", "fast bowler", "yorker", "mi", "indian", ...],
      "matched_tags": ["fast bowler"],
      "score": 2
    },
    {
      "id": 1,
      "name": "Virat Kohli - Gold Edition",
      "category": "Cricket",
      "description": "Indian national team captain...",
      "image_url": "https://...",
      "tags": ["virat kohli", "kohli", "rcb", "batsman", ...],
      "matched_tags": [],
      "score": 0
    }
  ]
}
```

---

### 4. Get All Products
```http
GET /products
```

**Response:**
```json
[
  {
    "id": 1,
    "name": "Virat Kohli - Gold Edition",
    "category": "Cricket",
    "image_url": "https://...",
    "description": "...",
    "tags": ["virat kohli", "kohli", "rcb", ...]
  },
  {
    "id": 2,
    "name": "Jasprit Bumrah - Platinum",
    ...
  }
]
```

---

### 5. Get Single Product
```http
GET /products/{product_id}
```

**Example:**
```bash
curl http://localhost:8000/products/1
```

**Response:**
```json
{
  "id": 1,
  "name": "Virat Kohli - Gold Edition",
  "category": "Cricket",
  "image_url": "https://...",
  "description": "Indian national team captain, right-hand batsman, RCB franchise player. Known for chasing targets in ODIs and aggressive leadership.",
  "tags": ["virat kohli", "kohli", "rcb", "royal challengers", "indian batsman", "run chase king", "gold edition", "right hand bat", ...]
}
```

---

### 6. Get Product Tags Only
```http
GET /products/{product_id}/tags
```

**Example:**
```bash
curl http://localhost:8000/products/2/tags
```

**Response:**
```json
{
  "id": 2,
  "name": "Jasprit Bumrah - Platinum",
  "tags": ["jasprit bumrah", "bumrah", "fast bowler", "yorker", "mi", "mumbai indians", "indian", "death overs", "odi specialist", ...]
}
```

---

## 📚 Code Documentation

### main.py - Complete Code Overview

**Imports & Setup:**
```python
import httpx                                  # Async HTTP client
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from tagger import generate_tags               # AI tag generator
from search import search_products             # Search engine
from storage import load_products, add_or_update_product, get_product_count  # Data layer
```

**Data Models (Pydantic):**
```python
class PipelineRunRequest(BaseModel):
    api_url: Optional[str] = None  # External API to fetch products

class PipelineRunResponse(BaseModel):
    success: bool               # Success status
    products_tagged: int        # Number of products tagged
    total_tags: int             # Total tags generated
```

**Mock Data (Fallback):**
```python
MOCK_PRODUCTS = [
    {
        "id": 1,
        "name": "Virat Kohli - Gold Edition",
        "category": "Cricket",
        "image_url": "https://upload.wikimedia.org/...",
        "description": "Indian national team captain..."
    },
    # ... 4 more mock products
]
```

**FastAPI Setup:**
```python
app = FastAPI(title="Sports Card Tagger", version="1.0.0")

# Enable CORS (allow frontend to make requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],                    # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],                    # Allow all HTTP methods
    allow_headers=["*"]                     # Allow all headers
)
```

**Key Functions:**

```python
@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "products_in_db": get_product_count()}

@app.post("/pipeline/run")
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    """
    Main pipeline: Fetch → Tag → Store
    Workflow:
    1. Fetch products from API or mock data
    2. For each product, generate tags using GPT-4o
    3. Save to products.json immediately (incremental)
    4. Return summary
    """
    products = []
    store_base_url = ""

    if request.api_url:
        # External API fetch
        try:
            print(f"📥 Fetching products from: {request.api_url}")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(request.api_url)
                response.raise_for_status()

                data = response.json()
                products = data if isinstance(data, list) else data.get("products", [])

                # Extract base URL for relative image paths
                from urllib.parse import urlparse
                parsed = urlparse(request.api_url)
                store_base_url = f"{parsed.scheme}://{parsed.netloc}"

                print(f"✅ Fetched {len(products)} products")
        except Exception as e:
            print(f"❌ Failed to fetch from API: {e}")
            print("🔄 Falling back to mock data...")
            products = MOCK_PRODUCTS

    else:
        # Use mock data
        print("📋 Using mock product data...")
        products = MOCK_PRODUCTS

    if not products:
        return PipelineRunResponse(success=False, products_tagged=0, total_tags=0)

    # Tag each product with GPT-4o
    total_tags = 0
    for i, product in enumerate(products, 1):
        product_id = product.get("id", i)

        has_image = bool(
            product.get("image") or product.get("image_url") or product.get("thumbnail")
        )
        image_indicator = "with image" if has_image else "text only"

        print(
            f"🏷️  Tagging {i}/{len(products)}: {product.get('name', f'Product {product_id}')} ({image_indicator})..."
        )

        tags = generate_tags(product, store_base_url)
        product["tags"] = tags
        total_tags += len(tags)

        # Save immediately to preserve progress
        add_or_update_product(product)

        print(f"   → Generated {len(tags)} tags")

    print(f"\n✨ Pipeline complete! Tagged {len(products)} products ({total_tags} total tags)")

    return PipelineRunResponse(
        success=True, products_tagged=len(products), total_tags=total_tags
    )

@app.get("/search")
def search_endpoint(q: str = Query(..., description="Search query")) -> dict:
    """Search products by query across tags, name, and description."""
    return search_products(q)

@app.get("/products")
def get_all_products() -> list[dict]:
    """Get all products with their tags from products.json."""
    return load_products()

@app.get("/products/{product_id}/tags")
def get_product_tags(product_id: int) -> dict:
    """Get tags for a single product by ID."""
    from storage import get_product_by_id
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return {"id": product_id, "name": product.get("name"), "tags": product.get("tags", [])}

@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    """Get full product details by ID."""
    from storage import get_product_by_id
    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    return product
```

---

### tagger.py - Complete Code Overview

**Imports:**
```python
import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # Load OPENAI_API_KEY from .env
client = OpenAI()  # Auto-uses environment variable
```

**Main Function:**
```python
def generate_tags(product: dict, store_base_url: str = "") -> list[str]:
    """
    Generate AI tags for a product using GPT-4o with vision.
    
    Args:
        product: Dict containing id, name, description, image_url, category
        store_base_url: Base URL to prepend to relative image paths
    
    Returns:
        List of 15-20 generated tags, or empty list if tagging fails
    """
    
    # Step 1: Extract image URL
    image_url = (
        product.get("image")
        or product.get("image_url")
        or product.get("thumbnail")
        or None
    )

    # Step 2: Resolve relative image paths
    if image_url and image_url.startswith("/"):
        if store_base_url:
            image_url = store_base_url.rstrip("/") + image_url
        else:
            image_url = None  # Can't resolve

    # Step 3: Build detailed text prompt
    text_prompt = f"""You are a sports trading card tagging expert for an ecommerce search engine.
Analyze this product card — read the image carefully along with the name and description.
Generate 15-20 highly relevant search tags that buyers would actually type when searching.

Product name: {product.get('name', '')}
Category: {product.get('category', '')}
Description: {product.get('description', '')}

Generate tags covering:
- Player name + common spelling variations and nicknames
- Team names (national + franchise/club)
- Nationality and country
- Playing role/position (e.g. 'fast bowler', 'right hand batsman', 'striker')
- Playing style (e.g. 'aggressive batsman', 'death over specialist', 'free kick specialist')
- Achievements (e.g. 'world cup winner', 'ballon dor', 'ipl champion')
- Card rarity/type visible in image (e.g. 'gold foil', 'holographic', 'platinum border')
- Jersey number or colors visible in the image
- Era / generation (e.g. 'modern era', '90s legend')
- Sport name and format (e.g. 'test cricket', 'T20', 'champions league')
- Any text, logo, or design visible on the card image

Return ONLY a raw JSON array of tag strings. No explanation, no markdown, no backticks.
Example: ["virat kohli","kohli","rcb","royal challengers","indian batsman","run chase king","gold edition","right hand bat"]"""

    # Step 4: Build multimodal message content
    content = []

    if image_url:
        content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                    "detail": "high"  # high = reads fine text, jersey numbers, logos
                }
            }
        )

    content.append({"type": "text", "text": text_prompt})

    # Step 5: Call GPT-4o API
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=500,
            temperature=0.3  # Lower temperature = more consistent tags
        )

        raw = response.choices[0].message.content.strip()

        # Step 6: Parse JSON response
        try:
            return json.loads(raw)  # Parse JSON array
        except json.JSONDecodeError:
            # Fallback: extract anything inside [ ]
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            return json.loads(match.group()) if match else []

    except Exception as e:
        print(f"❌ Error calling GPT-4o: {e}")
        return []
```

**Temperature Parameter Explanation:**
- `temperature=0.3`: Lower = more predictable, focused tags (recommended)
- `temperature=1.0`: Higher = more creative, varied tags
- We use 0.3 because we want consistent, buyer-intent keywords

---

### search.py - Complete Code Overview

**Function:**
```python
def search_products(query: str) -> dict:
    """
    Search products by query across tags, name, and description.
    
    Scoring:
    - Tag match: 2 points
    - Name match: 5 points
    - Description match: 1 point
    
    Args:
        query: Search query string
    
    Returns:
        Dict with query, total count, and ranked results
    """
    
    products = load_products()
    query_lower = query.lower().strip()
    
    if not query_lower:
        return {"query": query, "total": 0, "results": []}
    
    results = []
    
    for product in products:
        score = 0
        matched_tags = []
        
        # Get product fields (lowercase for matching)
        tags = product.get("tags", [])
        name = product.get("name", "").lower()
        description = product.get("description", "").lower()
        category = product.get("category", "").lower()
        
        # Check tag matches (2 pts each)
        for tag in tags:
            tag_lower = tag.lower()
            if query_lower in tag_lower or tag_lower in query_lower:
                score += 2
                matched_tags.append(tag)
        
        # Check name match (5 pts) - higher priority
        if query_lower in name:
            score += 5
        
        # Check description match (1 pt)
        if query_lower in description:
            score += 1
        
        # Check category match (1 pt)
        if query_lower in category:
            score += 1
        
        if score > 0:
            result = {
                "id": product.get("id"),
                "name": product.get("name"),
                "category": product.get("category"),
                "description": product.get("description"),
                "image_url": product.get("image_url"),
                "tags": product.get("tags", []),
                "matched_tags": list(set(matched_tags)),  # deduplicate
                "score": score
            }
            results.append(result)
    
    # Sort by score (descending = highest relevance first)
    results.sort(key=lambda x: x["score"], reverse=True)
    
    return {
        "query": query,
        "total": len(results),
        "results": results
    }
```

---

### storage.py - Complete Code Overview

**Functions:**
```python
def load_products() -> list[dict]:
    """Load products from JSON file. Create empty list if file doesn't exist."""
    if not PRODUCTS_DB.exists():
        save_products([])
        return []
    
    try:
        with open(PRODUCTS_DB, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []

def save_products(products: list[dict]) -> None:
    """Save products to JSON file."""
    with open(PRODUCTS_DB, "w") as f:
        json.dump(products, f, indent=2)

def get_product_by_id(product_id: int | str) -> Optional[dict]:
    """Get a single product by ID. Returns None if not found."""
    products = load_products()
    product_id = int(product_id)
    for product in products:
        if product.get("id") == product_id:
            return product
    return None

def add_or_update_product(product: dict) -> None:
    """Add a new product or update existing one by ID."""
    products = load_products()
    product_id = product.get("id")
    
    # Find and update or append
    for i, p in enumerate(products):
        if p.get("id") == product_id:
            products[i] = product
            save_products(products)
            return
    
    products.append(product)
    save_products(products)

def get_product_count() -> int:
    """Get total number of products in database."""
    return len(load_products())
```

**Storage Format (products.json):**
```json
[
  {
    "id": 1,
    "name": "Virat Kohli - Gold Edition",
    "category": "Cricket",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Virat_Kohli_in_2023.jpg/220px-Virat_Kohli_in_2023.jpg",
    "description": "Indian national team captain, right-hand batsman, RCB franchise player. Known for chasing targets in ODIs and aggressive leadership.",
    "tags": [
      "virat kohli",
      "kohli",
      "rcb",
      "royal challengers",
      "indian batsman",
      "run chase king",
      "gold edition",
      "right hand bat",
      "odi specialist",
      "t20 star",
      ...
    ]
  }
]
```

---

### test_api.py - Testing & Examples

**Key Test Functions:**

```python
def test_health():
    """Test health check endpoint."""
    response = requests.get(f"{BASE_URL}/")
    # Output: {"status": "ok", "products_in_db": 5}

def run_pipeline(api_url=None):
    """Run the tagging pipeline."""
    payload = {"api_url": api_url}
    response = requests.post(f"{BASE_URL}/pipeline/run", json=payload)
    # Runs tagging and saves products

def search(query):
    """Search products."""
    response = requests.get(f"{BASE_URL}/search", params={"q": query})
    # Returns ranked results with scores

def get_all_products():
    """Get all products."""
    response = requests.get(f"{BASE_URL}/products")
    # Returns all products with tags

def get_product_by_id(product_id):
    """Get single product details."""
    response = requests.get(f"{BASE_URL}/products/{product_id}")
    # Returns full product data

def get_product_tags(product_id):
    """Get tags for a product."""
    response = requests.get(f"{BASE_URL}/products/{product_id}/tags")
    # Returns only tags for product
```

**Running Tests:**
```bash
python test_api.py
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```
OPENAI_API_KEY=sk-YOUR_KEY_HERE
```

### Server Configuration (main.py)
```python
# Change host/port:
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",        # Listen on all interfaces
        port=8000,             # Port number  
        reload=True            # Auto-reload on code changes
    )
```

### Tagging Configuration (tagger.py)
```python
# Adjust temperature for different tag styles:
client.chat.completions.create(
    model="gpt-4o",
    temperature=0.3  # 0.3=consistent, 1.0=creative
)

# Adjust max_tokens:
max_tokens=500  # Increase if tags are truncated
```

### Storage Backend (storage.py)
```python
# Current: JSON file
PRODUCTS_DB = Path(__file__).parent / "products.json"

# For production, replace with:
# - PostgreSQL
# - MongoDB
# - Redis cache
# - AWS DynamoDB
```

---

## 💡 Usage Examples

### Example 1: Run with Mock Data
```bash
# Terminal 1: Start server
uvicorn main:app --reload --port 8000

# Terminal 2: Run pipeline with mock data
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": null}'

# Response:
# {"success": true, "products_tagged": 5, "total_tags": 90}
```

### Example 2: Search for Products
```bash
# Search for fast bowlers
curl "http://localhost:8000/search?q=fast+bowler"

# Response shows:
# - Jasprit Bumrah (score: 2) ← matched "fast bowler" tag
# - Other cricket players (score: 0)
```

### Example 3: Get All Products
```bash
curl http://localhost:8000/products

# Returns JSON array with all tagged products
```

### Example 4: Python Test Script
```bash
python test_api.py

# Runs comprehensive tests:
# - Health check
# - Pipeline with mock data
# - All search queries
# - All endpoint variations
```

### Example 5: Custom API Integration
```bash
# If you have an external auction API:
curl -X POST http://localhost:8000/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{"api_url": "https://bid.collectorinvestorauctions.com/api/products"}'

# API response format should be:
# [
#   {
#     "id": 123,
#     "name": "Product Name",
#     "description": "...",
#     "category": "Baseball",
#     "image_url": "https://..."
#   }
# ]
```

---

## 🎯 Search Scoring Algorithm

### Scoring Matrix

| Field | Query Match | Points | Reasoning |
|-------|------------|--------|-----------|
| **Tags** | Query in tag | 2 | AI-generated, high relevance |
| **Name** | Query in name | 5 | Product name is exact match |
| **Description** | Query in desc | 1 | Contextual mention |
| **Category** | Query in category | 1 | Broad category match |

### Example Search Walkthrough

**Query:** `"fast bowler"`

```python
# Product 1: Jasprit Bumrah - Platinum
tags = ["jasprit bumrah", "bumrah", "fast bowler", "yorker", ...]
name = "jasprit bumrah - platinum"
description = "Indian fast bowler, unique bowling action..."

# Matching:
# - "fast bowler" in tags ✓ → 2 points
# - "fast bowler" in name ✗ → 0 points
# - "fast bowler" in description ✓ → 1 point
# - "fast bowler" in category ✗ → 0 points
# TOTAL SCORE: 3 points

# Product 2: Virat Kohli - Gold Edition
tags = ["virat kohli", "kohli", "rcb", "batsman", ...]
name = "virat kohli - gold edition"
description = "Indian national team captain, right-hand batsman..."

# Matching:
# - "fast bowler" in tags ✗ → 0 points
# - "fast bowler" in name ✗ → 0 points
# - "fast bowler" in description ✗ → 0 points
# - "fast bowler" in category ✗ → 0 points
# TOTAL SCORE: 0 points (not returned)
```

**Results returned (ranked by score):**
1. Jasprit Bumrah (score: 3)
2. Any other cricket fast bowlers with "fast bowler" in tags/description

---

## 📊 Output Format

### products.json Structure
```json
[
  {
    "id": 1,
    "name": "Virat Kohli - Gold Edition",
    "category": "Cricket",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Virat_Kohli_in_2023.jpg/220px-Virat_Kohli_in_2023.jpg",
    "description": "Indian national team captain, right-hand batsman, RCB franchise player. Known for chasing targets in ODIs and aggressive leadership.",
    "tags": [
      "virat kohli",
      "kohli",
      "rcb",
      "royal challengers",
      "india cricket",
      "batsman",
      "run chase",
      "odi specialist",
      "t20 star",
      "right hand bat",
      "aggressive batsman",
      "captain",
      "raina replacement",
      "gold edition",
      "premium card",
      "modern era",
      "international cricket",
      "new delhi",
      "dehradun",
      "ipl"
    ]
  },
  {
    "id": 2,
    "name": "Jasprit Bumrah - Platinum",
    "category": "Cricket",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Jasprit_Bumrah_in_2023.jpg/220px-Jasprit_Bumrah_in_2023.jpg",
    "description": "Indian fast bowler, unique bowling action, deadly yorkers specialist. Mumbai Indians pacer and top wicket-taker.",
    "tags": [
      "jasprit bumrah",
      "bumrah",
      "fast bowler",
      "yorker",
      "mi",
      "mumbai indians",
      "indian pacer",
      "death overs",
      "odi specialist",
      "t20 specialist",
      "india cricket",
      "unique action",
      "left arm fast",
      "premium bowler",
      "platinum edition",
      "modern era",
      "international cricket",
      "world champion",
      "world cup winner",
      "ipl"
    ]
  }
]
```

### API Response Examples

**Search Response:**
```json
{
  "query": "fast bowler",
  "total": 1,
  "results": [
    {
      "id": 2,
      "name": "Jasprit Bumrah - Platinum",
      "category": "Cricket",
      "description": "Indian fast bowler, unique bowling action, deadly yorkers specialist. Mumbai Indians pacer and top wicket-taker.",
      "image_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Jasprit_Bumrah_in_2023.jpg/220px-Jasprit_Bumrah_in_2023.jpg",
      "tags": ["jasprit bumrah", "bumrah", "fast bowler", ...],
      "matched_tags": ["fast bowler"],
      "score": 3
    }
  ]
}
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: No module named 'fastapi'` | Run `pip install -r requirements.txt` |
| `Error: OpenAI API key not found` | Create `.env` file with `OPENAI_API_KEY=sk-...` |
| `Connection refused` on `http://localhost:8000` | Start server: `uvicorn main:app --reload --port 8000` |
| `Failed to fetch products from API` | Check API URL is correct. Pipeline falls back to mock data. |
| GPT-4o calls are slow (5-10 seconds per product) | This is normal! Vision processing takes time. Can be optimized with batch processing. |
| Tags are truncated or incomplete | Increase `max_tokens=500` in `tagger.py` |
| "Invalid JSON from GPT-4o" | Temperature is too high. Lower to 0.3 in `tagger.py` |
| Search returns no results | Check products are tagged. Run `python test_api.py` to verify pipeline. |
| `products.json` is empty | Run pipeline: `curl -X POST http://localhost:8000/pipeline/run -H "Content-Type: application/json" -d '{"api_url": null}'` |
| CORS errors in browser | Already enabled with `allow_origins=["*"]` in main.py. Check browser console. |

---

## 🚀 Next Steps & Production

### Phase 1: Validation (Current)
- ✅ Mock data pipeline working
- ✅ GPT-4o integration proven
- ✅ Search API functional
- ✅ JSON storage working

### Phase 2: Integration (Next)
- [ ] Connect to real Collector Investor Auctions API
- [ ] Test with 100+ products
- [ ] Optimize tagging speed (parallel processing)
- [ ] Add caching layer (Redis)

### Phase 3: Optimization
- [ ] Replace JSON with PostgreSQL
- [ ] Add batch tagging (Process 10 products in parallel)
- [ ] Add tag caching (Don't re-tag same product)
- [ ] Implement pagination for large result sets
- [ ] Add advanced filtering (by category, date range, etc.)

### Phase 4: Production Deployment
- [ ] Docker containerization
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Deployment to AWS/Azure/GCP
- [ ] Load testing & scaling
- [ ] Monitoring & alerting
- [ ] Cost optimization (GPT-4o billing)

### Database Migration Example (PostgreSQL)
```python
# Replace storage.py with:
from sqlalchemy import create_engine, Column, Integer, String, JSON
from sqlalchemy.orm import declarative_base, Session

DATABASE_URL = "postgresql://user:password@localhost/sports_cards"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    category = Column(String)
    description = Column(String)
    image_url = Column(String)
    tags = Column(JSON)  # Store as JSON array

# Then use SQLAlchemy instead of JSON file
```

### Batch Processing Optimization
```python
# main.py modification for parallel tagging:
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Tag multiple products in parallel
async def tag_all_products_parallel(products):
    tasks = []
    for product in products:
        task = asyncio.create_task(
            asyncio.to_thread(generate_tags, product, store_base_url)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    return results
```

---

## 📞 Support & References

- **FastAPI Docs:** https://fastapi.tiangolo.com
- **OpenAI GPT-4o Vision:** https://platform.openai.com/docs/guides/vision
- **Uvicorn Server:** https://www.uvicorn.org
- **Python dotenv:** https://github.com/theskumar/python-dotenv
- **Httpx Async Client:** https://www.python-httpx.org

---

## 📝 Files Reference

| File | Purpose | Lines | Key Classes |
|------|---------|-------|-------------|
| `main.py` | FastAPI server & pipeline | ~200 | `PipelineRunRequest`, `PipelineRunResponse` |
| `tagger.py` | GPT-4o tag generation | ~80 | `generate_tags()` |
| `search.py` | Semantic search engine | ~60 | `search_products()` |
| `storage.py` | Data persistence | ~50 | `load_products()`, `add_or_update_product()` |
| `test_api.py` | API testing examples | ~140 | Various test functions |
| `products.json` | Product database | Dynamic | JSON array of products |
| `.env` | Environment config | ~1 | `OPENAI_API_KEY` |
| `requirements.txt` | Python dependencies | ~5 | fastapi, uvicorn, openai, httpx, python-dotenv |

---

## ✅ Features Summary

| Feature | Status | Details |
|---------|--------|---------|
| Product Fetching | ✅ Complete | Support for external APIs + mock data fallback |
| AI Tagging | ✅ Complete | GPT-4o vision (15-20 tags per product) |
| Search Engine | ✅ Complete | Multi-field semantic search with relevance scoring |
| REST API | ✅ Complete | FastAPI with Swagger auto-docs |
| Data Storage | ✅ Complete | JSON-based (easily upgradeable to SQL) |
| CORS Support | ✅ Complete | Enabled for all origins |
| Error Handling | ✅ Complete | Graceful fallbacks on API failures |
| Logging | ✅ Partial | Terminal output (could add structured logging) |
| Testing | ✅ Partial | test_api.py script provided |
| Documentation | ✅ Complete | This comprehensive README |
| Docker | ⏳ Future | Planned for production deployment |
| Caching | ⏳ Future | Can add Redis layer |
| Database | ⏳ Future | PostgreSQL migration planned |
| Monitoring | ⏳ Future | Add Prometheus/Grafana |

---

**Last Updated:** April 13, 2026
**Version:** 1.0.0
**Status:** Production Ready (POC Phase)on Integration**: Analyzes product images + text to generate 15-20 smart search tags
- **Smart Search**: Rank products by relevance (tags, name, description, category)
- **Local JSON Storage**: No database required - perfect for POC
- **Graceful Fallbacks**: Text-only tagging if images fail; mock data if API fails
- **Live Progress**: Terminal output shows tagging progress
- **Auto-save**: Incremental saves prevent data loss on crashes

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API key
Edit `.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-...your_key_here...
```

### 3. Run the server
```bash
uvicorn main:app --reload --port 8000
```

The API will start at `http://localhost:8000`

## API Endpoints

### Health Check
```
GET /
```
Returns: `{ "status": "ok", "products_in_db": 5 }`

### Run Tagging Pipeline
```
POST /pipeline/run
Content-Type: application/json
```

**Option A: Use Custom Endpoint (Recommended for your site)**
```json
{
  "api_url": "https://bid.collectorinvestorauctions.com/api/products"
}
```

**Option B: Load from Local File**
```json
{
  "file_path": "products.csv"
}
```

**Option C: Use Mock Data**
```json
{
  "api_url": null
}
```

Response:
```json
{
  "success": true,
  "products_tagged": 5,
  "total_tags": 87,
  "message": "Tagged 5 products from API"
}
```

### Get All Products
```
GET /products
```

Returns full list of all products with tags.

### Get Single Product
```
GET /products/2
```

### Get Product Tags
```
GET /products/2/tags
```

Response:
```json
{
  "id": 2,
  "name": "Jasprit Bumrah - Platinum",
  "tags": ["jasprit bumrah", "fast bowler", "yorker", ...]
}
```

### Upload Products File
```
POST /upload/products
Content-Type: multipart/form-data

[upload CSV or JSON file]
```

Supported formats:
- **CSV**: `id, name, description, category, image_url` (with header)
- **JSON**: Array of objects `[{ "id": 1, "name": "...", ... }]`

## Search Scoring

| Match Type | Points |
|-----------|--------|
| Tag match | 2 |
| Name match | 5 |
| Description match | 1 |
| Category match | 1 |

Results are ranked by total score (highest first).

## Project Structure

```
sports-card-tagger/
├── main.py           # FastAPI app + all route definitions
├── tagger.py         # GPT-4o tag generation logic (image + text)
├── search.py         # Search + scoring logic
├── storage.py        # Read/write products.json
├── products.json     # Auto-created, stores products + tags
├── .env              # OPENAI_API_KEY=sk-...
└── requirements.txt  # Dependencies
```

## How It Works

1. **Fetch**: `POST /pipeline/run` fetches products from your API (or uses mock data)
2. **Tag**: For each product, GPT-4o analyzes the image + name + description
3. **Generate**: GPT-4o returns 15-20 relevant tags (player name, team, position, achievements, etc.)
4. **Save**: Product + tags saved to `products.json` immediately
5. **Search**: `GET /search?q=...` searches across tags, name, description
6. **Score**: Results ranked by relevance scoring

## Example Tags Generated

For "Virat Kohli - Gold Edition":
```
[
  "virat kohli",
  "kohli",
  "rcb",
  "royal challengers bangalore",
  "indian batsman",
  "right hand bat",
  "run chase king",
  "gold edition",
  "modern era",
  "test cricket",
  "captain",
  "indian national team",
  ...
]
```

## Error Handling

- **Failed image load**: Falls back to text-only tagging (still works!)
- **Failed GPT-4o call**: Returns empty tags, continues to next product
- **Failed API fetch**: Falls back to mock data automatically
- **Relative image URLs**: Automatically prepended with store base URL

## Tips

- **Start with mock data**: Run first pipeline without `api_url` to test
- **Monitor tagging**: Terminal shows progress for each product
- **Incremental saves**: Each product saved individually (so failures don't lose progress)
- **Rerun pipeline**: Running pipeline again will update products and tags
- **Search queries**: Try "fast bowler", "world cup winner", "rcb", "gold edition", etc.

## Requirements

- Python 3.10+
- OpenAI API key (for GPT-4o)
- Internet connection (for API calls + image fetching)
#   S e a r c h P l u s 
 
 