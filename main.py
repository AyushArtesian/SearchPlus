import json

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from CollectorInvestor import (
    API_URI_TEMPLATE,
    BASE64_TOKEN,
    CONTENT_TYPE,
    USERNAME,
    generate_headers,
    listing_to_product,
    parse_response_to_listings,
)
from tagger import generate_tags
from search import search_products
from storage import load_products, add_or_update_product, get_product_count


# Request/Response models
class PipelineRunRequest(BaseModel):
    offset: int = 0
    limit: int = 25
    timeout: int = 45
    status: str = ""


class PipelineRunResponse(BaseModel):
    success: bool
    fetched: int
    products_tagged: int
    total_tags: int


def fetch_collectorinvestor_products(
    offset: int,
    limit: int,
    timeout: int,
    status: str,
) -> list[dict]:
    """Fetch and normalize products from CollectorInvestor endpoint."""
    uri = API_URI_TEMPLATE.format(offset=offset, limit=limit)
    request_body = {"Items": {}}
    body_str = json.dumps(request_body, separators=(",", ":"))

    headers = generate_headers(USERNAME, BASE64_TOKEN, uri, body_str, CONTENT_TYPE)
    response = requests.get(uri, headers=headers, data=body_str, timeout=timeout)

    if response.status_code != 200:
        raise RuntimeError(
            f"CollectorInvestor fetch failed (status {response.status_code}): {response.text[:300]}"
        )

    payload = response.json()
    listings = parse_response_to_listings(payload)

    if status.strip():
        wanted = status.strip().lower()
        listings = [item for item in listings if str(item.get("Status", "")).lower() == wanted]

    products = [listing_to_product(item) for item in listings]
    return [p for p in products if p.get("id") and p.get("title")]


app = FastAPI(title="Sports Card Tagger", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "products_in_db": get_product_count()}


@app.post("/pipeline/run")
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    """
    Fetch products from CollectorInvestor, generate tags with GPT, save to products.json.
    """
    try:
        products = fetch_collectorinvestor_products(
            offset=request.offset,
            limit=request.limit,
            timeout=request.timeout,
            status=request.status,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    if not products:
        return PipelineRunResponse(success=True, fetched=0, products_tagged=0, total_tags=0)

    # Tag each product and persist immediately so progress is not lost.
    total_tags = 0
    for i, product in enumerate(products, 1):
        product_id = product.get("id", i)

        has_image = bool(product.get("image_url"))
        image_indicator = "with image" if has_image else "text only"

        print(
            f"Tagging {i}/{len(products)}: {product.get('title', f'Product {product_id}')} ({image_indicator})..."
        )

        tags = generate_tags(product)
        product["tags"] = tags

        # Keep compatibility with any old code that reads "name".
        if not product.get("name") and product.get("title"):
            product["name"] = product["title"]

        total_tags += len(tags)

        add_or_update_product(product)

        print(f"   Generated {len(tags)} tags")

    print(f"Pipeline complete. Tagged {len(products)} products ({total_tags} total tags)")

    return PipelineRunResponse(
        success=True,
        fetched=len(products),
        products_tagged=len(products),
        total_tags=total_tags,
    )


@app.get("/search")
def search_endpoint(q: str = Query(..., description="Search query")) -> dict:
    """
    Search products by query across tags, title/name, subtitle, and description.

    Scoring:
    - Tag match: 2 points
    - Title/name match: 5 points
    - Subtitle match: 2 points
    - Description match: 1 point

    Query example: /search?q=fast+bowler
    """
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

    return {
        "id": product_id,
        "title": product.get("title") or product.get("name"),
        "tags": product.get("tags", []),
    }


@app.get("/products/{product_id}")
def get_product(product_id: int) -> dict:
    """Get full product details by ID."""
    from storage import get_product_by_id

    product = get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    return product


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
