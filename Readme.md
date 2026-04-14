# Sports Card Tagger - Complete Documentation

A production-ready Python project that fetches CollectorInvestor auction listings, enriches them with buyer-search-friendly tags using Azure OpenAI, and exposes a searchable REST API.

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Directory Structure](#directory-structure)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [Workflows](#workflows)
7. [CLI Usage](#cli-usage)
8. [API Endpoints](#api-endpoints)
9. [Search Algorithm](#search-algorithm)
10. [Data Models](#data-models)
11. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**Sports Card Tagger** is an AI-powered product enrichment system designed for sports card auction and ecommerce platforms. It automates the process of:

1. **Fetching** live listing data from CollectorInvestor auction API
2. **Normalizing** raw listings into a consistent product schema
3. **Enriching** products with buyer-intent search tags using Azure OpenAI GPT-4
4. **Persisting** tagged products in local JSON database
5. **Serving** search and lookup endpoints via RESTful API

### Use Case

Improve search discoverability on sports card auction sites by automatically generating contextual tags such as:
- Player names & positions (e.g., "patrick ewing", "power forward")
- Card details (e.g., "1986 fleer", "rookie card", "rc")
- Grading info (e.g., "psa 10", "gem mint", "nm")
- Card features (e.g., "rookie", "signed", "error")

---

## 🏗️ Architecture

### System Overview

```
CollectorInvestor API
       ↓
   Fetch Service (src/services/collector_investor.py)
       ↓
   Normalize Products
       ↓
   Storage Layer (src/storage.py)
       ↓
   Tag Generation Service (src/services/tagger_service.py)
       ↓
   OpenAI API
       ↓
   Persist Tagged Products
       ↓
   FastAPI Server (main.py)
       ├── Pipeline Endpoint (/pipeline/run)
       ├── Search Endpoint (/search)
       ├── Product Endpoints (/products, /products/{id})
       └── Health Check (/)
```

### Modular Design

The project uses a **clean architecture** with clear separation of concerns:

| Layer | Purpose | Files |
|-------|---------|-------|
| **API Layer** | REST endpoints, request validation | `main.py`, `src/models.py` |
| **Service Layer** | Business logic (fetch, tag, search) | `src/services/` |
| **Data Layer** | Product persistence | `src/storage.py` |
| **Config Layer** | Centralized configuration | `src/config.py` |

---

## 📁 Directory Structure

```
sports-card-tagger/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Configuration & constants
│   ├── models.py                 # Pydantic request/response models
│   ├── storage.py                # JSON database layer
│   └── services/
│       ├── __init__.py
│       ├── collector_investor.py # CollectorInvestor API client
│       ├── tagger_service.py     # OpenAI tag generation
│       └── search_service.py     # Search engine
├── data/                         # Generated locally (not committed)
│   └── products.json             
├── main.py                       # FastAPI application (entry point)
├── tagger.py                     # Legacy CLI for tag generation
├── CollectorInvestor.py          # Legacy CLI for fetching
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (local, not committed)
├── .env.example                  # Example env file
├── .gitignore                    # Git ignore rules
└── Readme.md                     # This file
```

---

## 🔧 Installation & Setup

### Prerequisites

- Python 3.9+
- Azure OpenAI account with GPT-4 deployment
- pip (Python package manager)

### Step 1: Clone Repository

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

Create `.env` in project root:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/openai/v1/
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_KEY=<your-api-key>
```

**Security:** Never commit `.env` to Git (it's in `.gitignore`).

---

## ⚙️ Configuration

All configuration is centralized in `src/config.py` with environment variable overrides.

### Key Settings

| Setting | Source | Default | Purpose |
|---------|--------|---------|---------|
| `AZURE_OPENAI_ENDPOINT` | `.env` | Required | Azure OpenAI API endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | `.env` | Required | GPT-4 deployment name |
| `AZURE_OPENAI_API_KEY` | `.env` | Required | API authentication key |
| `PRODUCTS_DB` | Config | `data/products.json` | Product database path |
| `TAG_COUNT_MIN` | Config | 12 | Minimum tags per product |
| `TAG_COUNT_MAX` | Config | 20 | Maximum tags per product |
| `TAG_TEMPERATURE` | Config | 0.2 | OpenAI temperature (creativity 0-1) |

---

## 🔄 Workflows

### Workflow 1: Manual CLI - Fetch & Tag Separately

**Step 1: Fetch Listings**

```bash
python CollectorInvestor.py --offset 0 --limit 50 --output collectorinvestor_products_sample.json
```

Options:
- `--offset` (int): Starting position (default: 0)
- `--limit` (int): Page size (default: 25)
- `--output` (str): Output JSON path
- `--timeout` (int): HTTP timeout seconds (default: 45)
- `--status` (str): Optional status filter

Output:
```json
[
  {
    "id": 4453442,
    "title": "1986 Fleer #32 Patrick Ewing RC NM",
    "description": "You will receive the exact item(s) shown.",
    "image_url": "https://ciaimages.blob.core.windows.net/...",
    "subtitle": "DoubleD Vintage Basketball Cards Collection"
  }
]
```

**Step 2: Generate Tags**

```bash
python tagger.py --input collectorinvestor_products_sample.json --output collectorinvestor_products_tagged.json
```

Output:
```json
[
  {
    "id": 4453442,
    "title": "1986 Fleer #32 Patrick Ewing RC NM",
    "description": "...",
    "image_url": "...",
    "subtitle": "...",
    "tags": ["patrick ewing", "1986 fleer", "rookie card", "rc", "psa 10", ...]
  }
]
```

---

### Workflow 2: API - Automated Pipeline

**Start Server:**

```bash
uvicorn main:app --reload --port 8000
```

Access Swagger docs: `http://127.0.0.1:8000/docs`

**POST /pipeline/run:**

```json
{
  "offset": 0,
  "limit": 25,
  "timeout": 45,
  "status": ""
}
```

Response:
```json
{
  "success": true,
  "fetched": 25,
  "products_tagged": 25,
  "total_tags": 315
}
```

---

## 📡 API Endpoints

### Health Check

```http
GET /
```

### Pipeline: Fetch & Tag

```http
POST /pipeline/run
{
  "offset": 0,
  "limit": 25,
  "timeout": 45,
  "status": ""
}
```

### Search Products

```http
GET /search?q=patrick+ewing
```

Scoring: Tag (+2), Title (+5), Subtitle (+2), Description (+1), Category (+1)

### Get All Products

```http
GET /products
```

### Get Product by ID

```http
GET /products/{product_id}
```

### Get Product Tags Only

```http
GET /products/{product_id}/tags
```

---

## 🔍 Search Algorithm

Results ranked by relevance:

| Field | Points |
|-------|--------|
| Tag match | +2 |
| Title/name match | +5 |
| Subtitle match | +2 |
| Description match | +1 |
| Category match | +1 |

Example: Query "patrick ewing" on product "1986 Fleer #32 Patrick Ewing RC NM"
- Tags contain "patrick ewing" → +2
- Title contains "Patrick Ewing" → +5
- **Total: 7 points**

---

## 📊 Data Models

### Product

```python
{
  "id": int,
  "title": str,
  "description": str,
  "image_url": str,
  "subtitle": str,
  "tags": list[str]
}
```

### Pipeline Request

```python
{
  "offset": int = 0,
  "limit": int = 25,
  "timeout": int = 45,
  "status": str = ""
}
```

### Pipeline Response

```python
{
  "success": bool,
  "fetched": int,
  "products_tagged": int,
  "total_tags": int
}
```

---

## 💾 Data Files

Generated data NOT committed to Git:

- `data/products.json` - Product database with tags
- `.env` - Azure credentials (local only)
- Intermediate JSON files from CLI

---

## 🐛 Troubleshooting

**"Missing AZURE_OPENAI_DEPLOYMENT"**
- Check `.env` file has all required variables
- Restart application after updating `.env`

**"CollectorInvestor fetch failed (status 401)"**
- Verify API credentials
- Check network connectivity

**"No tags generated"**
- Verify image URL is publicly accessible
- System auto-retries with text-only tagging
- Check logs for errors

---

## 📦 Dependencies

```
fastapi          # Web framework
uvicorn          # ASGI server
openai           # Azure OpenAI client
httpx            # Async HTTP client
python-dotenv    # Environment variables
requests         # HTTP client
pydantic         # Data validation
```

---

## 🎯 Quick Start

```bash
# 1. Setup
pip install -r requirements.txt

# 2. Configure
# Edit .env with your Azure credentials

# 3. Fetch Listings
python CollectorInvestor.py --offset 0 --limit 25

# 4. Generate Tags
python tagger.py --input collectorinvestor_products_sample.json

# 5. Start API
uvicorn main:app --reload --port 8000

# 6. Access Swagger UI
# Open http://127.0.0.1:8000/docs
```

---

**Last updated:** April 2026 | **Architecture:** Modular, Clean Code
