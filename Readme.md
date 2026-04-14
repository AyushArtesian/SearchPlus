# Sports Card Tagger

A simple Python project that fetches CollectorInvestor auction listings, enriches them with buyer-search-friendly tags using Azure OpenAI, and exposes a searchable product API.

## Key Files

- `CollectorInvestor.py` — fetches listing data from the CollectorInvestor API and normalizes it into JSON objects containing `id`, `title`, `description`, `image_url`, and optional `subtitle`.
- `tagger.py` — sends each product to OpenAI and generates 12-20 user-friendly search tags.
- `main.py` — FastAPI service and pipeline orchestration, now wired to use `CollectorInvestor.py` for fetch and `tagger.py` for tag generation.
- `search.py` — query engine that searches products by tags, title, subtitle, description, and category.
- `storage.py` — reads/writes `products.json` to persist tagged products.
- `.gitignore` — prevents product JSONs and environment files from being committed.

## What This Project Does

1. Fetches live listing data from `CollectorInvestor` auction API.
2. Normalizes the response to a product schema.
3. Sends product data to OpenAI to generate buyer-search tags.
4. Persists tagged products in `products.json`.
5. Serves search and lookup endpoints through FastAPI.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root with Azure OpenAI settings:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource-name>.openai.azure.com/openai/v1/
AZURE_OPENAI_DEPLOYMENT=<your-deployment-name>
AZURE_OPENAI_API_KEY=<your-api-key>
```

Make sure this file is listed in `.gitignore`.

## Fetch Listings

Run CollectorInvestor fetch and save normalized products locally:

```bash
python CollectorInvestor.py --offset 0 --limit 25 --output collectorinvestor_products_sample.json
```

That command fetches listings and writes products with fields:

- `id`
- `title`
- `description`
- `image_url`
- `subtitle` (when present)

## Generate Tags

Tag the fetched products using OpenAI:

```bash
python tagger.py --input collectorinvestor_products_sample.json --output collectorinvestor_products_tagged.json
```

This produces a JSON file with `tags` for each product.

## Run the API

Start the FastAPI server:

```bash
uvicorn main:app --reload --port 8000
```

Then open the API docs:

```text
http://127.0.0.1:8000/docs
```

## Pipeline Endpoint

Use the `/pipeline/run` endpoint to fetch listings and generate tags in one pipeline call.

Example request body:

```json
{
  "offset": 0,
  "limit": 25,
  "timeout": 45,
  "status": ""
}
```

The pipeline:

- fetches data via `CollectorInvestor.py`
- normalizes product fields
- runs tag generation via `tagger.py`
- stores results in `products.json`

## Search

Query the API like this:

```http
GET /search?q=psa+10
```

The search engine ranks results by:

- tags
- title / name
- subtitle
- description
- category

## Git Ignore and Data Files

The repository is configured to ignore generated and sensitive files:

- `.env`
- `products.json`
- `collectorinvestor_products_sample.json`
- `collectorinvestor_products_tagged.json`

These files should remain local and should not be committed to GitHub.

If they were previously tracked, remove them from Git history with:

```bash
git rm --cached collectorinvestor_products_sample.json collectorinvestor_products_tagged.json
```

Then commit the change:

```bash
git commit -m "Remove generated JSON data files from repo"
```

## Notes

- The current system uses the CollectorInvestor endpoint as the source of truth.
- No HTML scraping is required in the main fetch/tag workflow.
- `main.py` now orchestrates fetch + tag + save.

## Recommended Workflow

1. Fetch fresh listings:
   ```bash
   python CollectorInvestor.py --offset 0 --limit 50 --output collectorinvestor_products_sample.json
   ```
2. Generate tags:
   ```bash
   python tagger.py --input collectorinvestor_products_sample.json --output collectorinvestor_products_tagged.json
   ```
3. Run API:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
4. Use `POST /pipeline/run` to automate fetch + tag in the API.
